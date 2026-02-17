"""
Modelo SQLAlchemy para Cliente.
Columnas exactas de la tabla public.clientes en la BD (sin columnas que no existan).
La tabla clientes NO tiene total_financiamiento ni dias_mora (eso está en prestamos / se calcula desde cuotas).
"""
from sqlalchemy import Column, Integer, String, Date, DateTime, Text, text

from app.core.database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cedula = Column(String(20), nullable=False, index=True)  # UNIQUE parcial en BD: excluye Z999999999 (ver migracion_cedula_z999999999_repetible.sql)
    nombres = Column(String(100), nullable=False)
    telefono = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    direccion = Column(Text, nullable=False)
    fecha_nacimiento = Column(Date, nullable=False)
    ocupacion = Column(String(100), nullable=False)
    estado = Column(String(20), nullable=False, index=True)
    fecha_registro = Column(DateTime(timezone=False), nullable=False, server_default=text("'2025-10-31 00:00:00'"))
    fecha_actualizacion = Column(DateTime(timezone=False), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    usuario_registro = Column(String(50), nullable=False)
    notas = Column(Text, nullable=False)
