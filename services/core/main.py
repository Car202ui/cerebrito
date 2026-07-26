"""
ShaddAI · servicio CORE
Base de conocimiento + ingesta de CSV + análisis de datos.
FastAPI + SQLAlchemy + MySQL.
"""
import io
import os
import pandas as pd
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import engine, Base, get_db
import models
import ai

# Carpeta donde se guardan los CSV subidos (para poder re-analizarlos)
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Crea las tablas si no existen
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ShaddAI · core", version="0.2.0")

# Permitir que el frontend (React) llame a este servicio
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en producción: restringir al dominio del front
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Esquemas (validación de entrada/salida) ----------
class ProyectoIn(BaseModel):
    nombre: str
    descripcion: str | None = None
    tipo: str | None = None
    datos: dict | None = None


# ---------- Health check ----------
@app.get("/health")
def health():
    return {"status": "ok", "servicio": "core"}


# ---------- Base de conocimiento ----------
@app.post("/proyectos")
def crear_proyecto(payload: ProyectoIn, db: Session = Depends(get_db)):
    proyecto = models.Proyecto(**payload.model_dump())
    db.add(proyecto)
    db.commit()
    db.refresh(proyecto)
    return proyecto


@app.get("/proyectos")
def listar_proyectos(db: Session = Depends(get_db)):
    return db.query(models.Proyecto).order_by(models.Proyecto.id.desc()).all()


@app.get("/proyectos/{proyecto_id}")
def obtener_proyecto(proyecto_id: int, db: Session = Depends(get_db)):
    proyecto = db.get(models.Proyecto, proyecto_id)
    if not proyecto:
        raise HTTPException(404, "Proyecto no encontrado")
    return proyecto


# ---------- Ingesta de CSV ----------
@app.post("/datasets/upload")
async def subir_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "El archivo debe ser un .csv")

    contenido = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contenido))
    except Exception as e:
        raise HTTPException(400, f"No se pudo leer el CSV: {e}")

    dataset = models.Dataset(
        nombre_archivo=file.filename,
        filas=len(df),
        columnas=list(df.columns),
        muestra=df.head(20).fillna("").to_dict(orient="records"),
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    # Guardar el CSV completo en disco para poder analizarlo después
    ruta = os.path.join(UPLOAD_DIR, f"{dataset.id}.csv")
    with open(ruta, "wb") as f:
        f.write(contenido)

    return {
        "id": dataset.id,
        "nombre_archivo": dataset.nombre_archivo,
        "filas": dataset.filas,
        "columnas": dataset.columnas,
        "muestra": dataset.muestra,
    }


@app.get("/datasets")
def listar_datasets(db: Session = Depends(get_db)):
    return db.query(models.Dataset).order_by(models.Dataset.id.desc()).all()


def _cargar_df(dataset_id: int) -> pd.DataFrame:
    """Carga el CSV guardado de un dataset o lanza 404."""
    ruta = os.path.join(UPLOAD_DIR, f"{dataset_id}.csv")
    if not os.path.exists(ruta):
        raise HTTPException(404, "No hay archivo guardado para ese dataset")
    return pd.read_csv(ruta)


def _calcular_analytics(df: pd.DataFrame) -> dict:
    """Estadísticas listas para graficar y para que la IA razone."""
    numericas = df.select_dtypes(include="number").columns.tolist()
    categoricas = df.select_dtypes(exclude="number").columns.tolist()

    # Resumen por columna numérica (para tarjetas y gráficos)
    resumen_numerico = []
    for col in numericas:
        serie = df[col].dropna()
        if serie.empty:
            continue
        resumen_numerico.append({
            "columna": col,
            "suma": float(serie.sum()),
            "promedio": float(serie.mean()),
            "minimo": float(serie.min()),
            "maximo": float(serie.max()),
        })

    # Conteo de categorías (top 10) para gráficos de barras
    resumen_categorico = []
    for col in categoricas:
        conteo = df[col].value_counts().head(10)
        resumen_categorico.append({
            "columna": col,
            "datos": [{"nombre": str(k), "valor": int(v)} for k, v in conteo.items()],
        })

    return {
        "filas": len(df),
        "columnas": list(df.columns),
        "columnas_numericas": numericas,
        "columnas_categoricas": categoricas,
        "resumen_numerico": resumen_numerico,
        "resumen_categorico": resumen_categorico,
    }


@app.get("/datasets/{dataset_id}/analytics")
def analizar_dataset(dataset_id: int):
    """Devuelve estadísticas listas para graficar y tomar decisiones."""
    return _calcular_analytics(_cargar_df(dataset_id))


@app.get("/datasets/{dataset_id}/insights")
def insights_dataset(dataset_id: int):
    """ShaddAI razona sobre el dataset: conclusiones + recomendación."""
    analytics = _calcular_analytics(_cargar_df(dataset_id))
    return {"insights": ai.generar_insights(analytics)}


class PreguntaIn(BaseModel):
    pregunta: str


@app.post("/datasets/{dataset_id}/ask")
def preguntar_dataset(dataset_id: int, payload: PreguntaIn):
    """Pregunta en lenguaje natural sobre los datos."""
    analytics = _calcular_analytics(_cargar_df(dataset_id))
    return {"respuesta": ai.responder_pregunta(payload.pregunta, analytics)}
