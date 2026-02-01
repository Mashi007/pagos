"""
Modelo SQLAlchemy para Cliente.
Campos alineados con el frontend (types/index.ts Cliente, ClienteForm).
"""
from sqlalchemy import Column, Integer, String, Boolean, Numeric, Date, DateTime, Text
from sqlalchemy.sql import func

from app.core.database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cedula = Column(String(20), nullable=False, index=True)
    nombres = Column(String(255), nullable=False)
    telefono = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    direccion = Column(String(500), nullable=True)
    fecha_nacimiento = Column(Date, nullable=True)
    ocupacion = Column(String(100), nullable=True)

    # Financiamiento
    total_financiamiento = Column(Numeric(14, 2), nullable=True)
    cuota_inicial = Column(Numeric(14, 2), nullable=True)
    monto_financiado = Column(Numeric(14, 2), nullable=True)
    fecha_entrega = Column(Date, nullable=True)
    numero_amortizaciones = Column(Integer, nullable=True)
    modalidad_pago = Column(String(50), nullable=True)

    # Estado
    estado = Column(String(20), nullable=False, default="ACTIVO", index=True)
    activo = Column(Boolean, nullable=False, default=True)
    estado_financiero = Column(String(50), nullable=True)
    dias_mora = Column(Integer, nullable=False, default=0)

    # Auditoría
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    usuario_registro = Column(String(100), nullable=True)

    notas = Column(Text, nullable=True)
