"""Modelos de la base de datos (tablas)."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from db import Base


class Proyecto(Base):
    """Base de conocimiento: un proyecto/registro genérico y versátil.

    'datos' es JSON libre para que cerebrito no sea rígido:
    cada proyecto puede guardar la estructura que necesite.
    """
    __tablename__ = "proyectos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)
    tipo = Column(String(100), nullable=True)  # ej: 'seguridad', 'datos', 'analisis'
    datos = Column(JSON, nullable=True)         # contenido flexible (no hardcodeado)
    creado_en = Column(DateTime, default=datetime.utcnow)


class Dataset(Base):
    """Metadata de CUALQUIER archivo subido (tabla o documento)."""
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    nombre_archivo = Column(String(255), nullable=False)
    tipo = Column(String(20), nullable=True)     # 'tabla' | 'texto'
    filas = Column(Integer, nullable=True)       # solo para tablas
    columnas = Column(JSON, nullable=True)       # solo para tablas
    muestra = Column(JSON, nullable=True)        # preview de tablas
    texto = Column(Text, nullable=True)          # contenido de documentos/código
    creado_en = Column(DateTime, default=datetime.utcnow)


class Analisis(Base):
    """Base de conocimiento: análisis/insights que ShaddAI guardó de un archivo.

    Acumula el "conocimiento" del proyecto: cada vez que se guarda un análisis,
    queda un histórico consultable de qué se estudió y qué concluyó ShaddAI.
    """
    __tablename__ = "analisis"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, nullable=True)          # archivo que originó el análisis
    nombre_archivo = Column(String(255), nullable=True)
    tipo_archivo = Column(String(20), nullable=True)     # 'tabla' | 'texto'
    titulo = Column(String(255), nullable=True)          # etiqueta del usuario
    contenido = Column(Text, nullable=False)             # texto del insight/respuesta
    creado_en = Column(DateTime, default=datetime.utcnow)
