"""
ShaddAI · servicio CORE
Base de conocimiento + ingesta de CSV + análisis de datos.
FastAPI + SQLAlchemy + MySQL.
"""
import os
import pandas as pd
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from db import engine, Base, get_db
import models
import ai
import ingest
import security

# Carpeta donde se guardan los archivos subidos (para poder re-analizarlos)
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Crea las tablas si no existen
Base.metadata.create_all(bind=engine)


def _migrar_columnas():
    """Agrega columnas nuevas a 'datasets' si la tabla es de una versión previa."""
    for col, tipo in (("tipo", "VARCHAR(20)"), ("texto", "LONGTEXT")):
        try:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE datasets ADD COLUMN {col} {tipo}"))
        except Exception:
            pass  # ya existe


_migrar_columnas()

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


# ---------- Ingesta universal (cualquier archivo) ----------
@app.post("/datasets/upload")
async def subir_archivo(file: UploadFile = File(...), db: Session = Depends(get_db)):
    nombre = file.filename or "archivo"
    tipo = ingest.detectar_tipo(nombre)
    if tipo == "desconocido":
        raise HTTPException(
            400, f"Tipo de archivo no soportado ({nombre}). "
                 "Aceptados: CSV, Excel, JSON, TXT, PDF, código, SQL, logs.")

    contenido = await file.read()
    dataset = models.Dataset(nombre_archivo=nombre, tipo=tipo)

    if tipo == "tabla":
        try:
            df = ingest.leer_tabla(nombre, contenido)
        except Exception as e:
            raise HTTPException(400, f"No se pudo leer la tabla: {e}")
        dataset.filas = len(df)
        dataset.columnas = list(df.columns)
        dataset.muestra = df.head(20).fillna("").astype(str).to_dict(orient="records")
    else:  # texto
        try:
            dataset.texto = ingest.leer_texto(nombre, contenido)
        except Exception as e:
            raise HTTPException(400, f"No se pudo leer el documento: {e}")

    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    # Guardar el archivo original en disco
    ruta = os.path.join(UPLOAD_DIR, f"{dataset.id}_{nombre}")
    with open(ruta, "wb") as f:
        f.write(contenido)

    return {
        "id": dataset.id,
        "nombre_archivo": dataset.nombre_archivo,
        "tipo": dataset.tipo,
        "filas": dataset.filas,
        "columnas": dataset.columnas,
    }


@app.get("/datasets")
def listar_datasets(db: Session = Depends(get_db)):
    return db.query(models.Dataset).order_by(models.Dataset.id.desc()).all()


def _get_dataset(dataset_id: int, db: Session) -> models.Dataset:
    ds = db.get(models.Dataset, dataset_id)
    if not ds:
        raise HTTPException(404, "Archivo no encontrado")
    return ds


def _cargar_df(dataset_id: int, db: Session) -> pd.DataFrame:
    """Carga el archivo tabular guardado como DataFrame."""
    ds = _get_dataset(dataset_id, db)
    if ds.tipo != "tabla":
        raise HTTPException(400, "Este archivo no es una tabla (es un documento).")
    ruta = os.path.join(UPLOAD_DIR, f"{ds.id}_{ds.nombre_archivo}")
    if not os.path.exists(ruta):
        raise HTTPException(404, "No hay archivo guardado para ese dataset")
    with open(ruta, "rb") as f:
        return ingest.leer_tabla(ds.nombre_archivo, f.read())


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

    # Cruces: suma de cada métrica numérica agrupada por cada categoría.
    # Esto es lo realmente útil para decidir (ej. "ventas por región").
    # Se limita a las 2 primeras categóricas x 2 primeras numéricas.
    agregaciones = []
    for cat in categoricas[:2]:
        for num in numericas[:2]:
            grupo = (df.groupby(cat)[num].sum()
                       .sort_values(ascending=False).head(10))
            if grupo.empty:
                continue
            agregaciones.append({
                "categoria": cat,
                "metrica": num,
                "datos": [{"nombre": str(k), "valor": float(v)} for k, v in grupo.items()],
            })

    return {
        "filas": len(df),
        "columnas": list(df.columns),
        "columnas_numericas": numericas,
        "columnas_categoricas": categoricas,
        "resumen_numerico": resumen_numerico,
        "resumen_categorico": resumen_categorico,
        "agregaciones": agregaciones,
    }


@app.get("/datasets/{dataset_id}/analytics")
def analizar_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """Estadísticas para graficar (solo tablas)."""
    return _calcular_analytics(_cargar_df(dataset_id, db))


@app.get("/datasets/{dataset_id}/content")
def contenido_documento(dataset_id: int, db: Session = Depends(get_db)):
    """Devuelve el texto de un documento (para preview)."""
    ds = _get_dataset(dataset_id, db)
    if ds.tipo != "texto":
        raise HTTPException(400, "Este archivo no es un documento de texto.")
    texto = ds.texto or ""
    return {"nombre_archivo": ds.nombre_archivo, "longitud": len(texto),
            "preview": texto[:3000]}


@app.get("/datasets/{dataset_id}/insights")
def insights_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """ShaddAI razona sobre CUALQUIER archivo (tabla o documento)."""
    ds = _get_dataset(dataset_id, db)
    if ds.tipo == "tabla":
        analytics = _calcular_analytics(_cargar_df(dataset_id, db))
        return {"insights": ai.generar_insights(analytics)}
    return {"insights": ai.generar_insights_texto(ds.texto or "")}


class PreguntaIn(BaseModel):
    pregunta: str


@app.post("/datasets/{dataset_id}/ask")
def preguntar_dataset(dataset_id: int, payload: PreguntaIn, db: Session = Depends(get_db)):
    """Pregunta en lenguaje natural sobre cualquier archivo."""
    ds = _get_dataset(dataset_id, db)
    if ds.tipo == "tabla":
        analytics = _calcular_analytics(_cargar_df(dataset_id, db))
        return {"respuesta": ai.responder_pregunta(payload.pregunta, analytics)}
    return {"respuesta": ai.responder_pregunta_texto(payload.pregunta, ds.texto or "")}


# ---------- Base de conocimiento (histórico de análisis) ----------
class GuardarAnalisisIn(BaseModel):
    dataset_id: int | None = None
    titulo: str | None = None
    contenido: str


@app.post("/conocimiento")
def guardar_analisis(payload: GuardarAnalisisIn, db: Session = Depends(get_db)):
    """Guarda un análisis/insight en la base de conocimiento."""
    nombre, tipo = None, None
    if payload.dataset_id:
        ds = db.get(models.Dataset, payload.dataset_id)
        if ds:
            nombre, tipo = ds.nombre_archivo, ds.tipo
    registro = models.Analisis(
        dataset_id=payload.dataset_id,
        nombre_archivo=nombre,
        tipo_archivo=tipo,
        titulo=payload.titulo,
        contenido=payload.contenido,
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


@app.get("/conocimiento")
def listar_conocimiento(db: Session = Depends(get_db)):
    """Lista todo el conocimiento acumulado (más reciente primero)."""
    return db.query(models.Analisis).order_by(models.Analisis.id.desc()).all()


@app.delete("/conocimiento/{analisis_id}")
def borrar_analisis(analisis_id: int, db: Session = Depends(get_db)):
    """Elimina un análisis guardado."""
    registro = db.get(models.Analisis, analisis_id)
    if not registro:
        raise HTTPException(404, "Análisis no encontrado")
    db.delete(registro)
    db.commit()
    return {"ok": True}


# ---------- Inspector de seguridad (defensivo) ----------
class ScanIn(BaseModel):
    url: str


@app.post("/security/scan")
def escanear_seguridad(payload: ScanIn):
    """Analiza los encabezados de seguridad de un sitio + razonamiento de ShaddAI.

    Uso legítimo: sitios propios o con autorización. No hace explotación.
    """
    reporte = security.inspeccionar(payload.url)
    if reporte.get("error"):
        return {"reporte": reporte, "analisis": None}
    analisis = ai.analizar_seguridad(reporte)
    return {"reporte": reporte, "analisis": analisis}
