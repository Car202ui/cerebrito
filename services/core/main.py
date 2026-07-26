"""
cerebrito · servicio CORE
Base de conocimiento + ingesta de CSV.
FastAPI + SQLAlchemy + MySQL.
"""
import io
import pandas as pd
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import engine, Base, get_db
import models

# Crea las tablas si no existen
Base.metadata.create_all(bind=engine)

app = FastAPI(title="cerebrito · core", version="0.1.0")

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
