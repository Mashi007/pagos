"""
Modelo para tasas de cambio oficial diaria (BS a USD).
"""
from sqlalchemy import Column, Integer, Numeric, Date, ForeignKey, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class TasaCambioDiaria(Base):
    __tablename__ = "tasas_cambio_diaria"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    fecha = Column(Date, nullable=False, unique=True, index=True)
    tasa_oficial = Column(Numeric(15, 6), nullable=False)  # Ej: 2850.50
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    usuario_email = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now(), onupdate=func.now())
