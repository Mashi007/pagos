"""
Modelo SQLAlchemy para Cliente.
Columnas alineadas con public.clientes. Si falta alguna columna en la BD, aplicar el SQL correspondiente
en backend/scripts/ (p. ej. migracion_clientes_email_secundario.sql para email_secundario).
La tabla clientes NO tiene total_financiamiento ni dias_mora (eso está en prestamos / se calcula desde cuotas).
"""
from sqlalchemy import Column, Integer, String, Date, DateTime, Text, text
from sqlalchemy.orm import validates

from app.core.database import Base
from app.utils.cedula_almacenamiento import normalizar_cedula_almacenamiento


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cedula = Column(String(20), nullable=False, index=True)  # UNIQUE parcial en BD: excluye Z999999999 (ver migracion_cedula_z999999999_repetible.sql)
    nombres = Column(String(100), nullable=False)
    telefono = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False)
    email_secundario = Column(String(150), nullable=True)
    direccion = Column(Text, nullable=False)
    fecha_nacimiento = Column(Date, nullable=False)
    ocupacion = Column(String(100), nullable=False)
    estado = Column(String(20), nullable=False, index=True)
    fecha_registro = Column(DateTime(timezone=False), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    fecha_actualizacion = Column(DateTime(timezone=False), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    usuario_registro = Column(String(50), nullable=False)
    notas = Column(Text, nullable=False)

    @validates("cedula")
    def _cedula_guardado_mayusculas(self, key, value):
        if value is None:
            return None
        n = normalizar_cedula_almacenamiento(value)
        return n if n is not None else ""

