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
    """Metadata de un CSV subido + una muestra de sus filas."""
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    nombre_archivo = Column(String(255), nullable=False)
    filas = Column(Integer, nullable=True)
    columnas = Column(JSON, nullable=True)       # lista de nombres de columnas
    muestra = Column(JSON, nullable=True)        # primeras filas como preview
    creado_en = Column(DateTime, default=datetime.utcnow)
