"""
Modelo SQLAlchemy para Cliente.

Dos campos de correo electrónico por cliente:
  - email            (NOT NULL) — correo predeterminado; destino de todos los envíos automáticos.
  - email_secundario (nullable) — correo alternativo; se expone en el listado/UI para referencia
                                   del operador pero no se usa como destino de envío automático.

Si falta la columna email_secundario en la BD, aplicar:
  backend/scripts/migracion_clientes_email_secundario.sql

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

