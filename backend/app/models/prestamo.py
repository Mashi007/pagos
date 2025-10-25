"""
Modelo de Préstamo
Define la estructura básica de un préstamo.
Sincronizado con el endpoint de aprobaciones.
"""

from enum import Enum

from sqlalchemy import (
    TIMESTAMP,
    Column,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.db.session import Base

# Constantes de longitud de campos
CODIGO_LENGTH = 20
NUMERIC_PRECISION = 12
NUMERIC_SCALE = 2
TASA_PRECISION = 5
TASA_SCALE = 2
ESTADO_LENGTH = 20

# --- Enumeraciones ---


class EstadoPrestamo(str, Enum):
    """Estados posibles de un préstamo."""

    PENDIENTE = "PENDIENTE"  # Solicitud inicial
    EN_APROBACION = (
        "EN_APROBACION"  # <== AÑADIDO: Usado por el endpoint de aprobaciones
    )
    APROBADO = "APROBADO"  # <== USADO por el endpoint
    RECHAZADO = "RECHAZADO"  # <== AÑADIDO: Usado por el endpoint al rechazar
    CANCELADO = "CANCELADO"
    ACTIVO = "ACTIVO"
    COMPLETADO = "COMPLETADO"
    REFINANCIADO = "REFINANCIADO"
    EN_MORA = "EN_MORA"


class ModalidadPago(str, Enum):
    """Modalidades de pago disponibles"""

    TRADICIONAL = "TRADICIONAL"
    SEMANAL = "SEMANAL"
    QUINCENAL = "QUINCENAL"
    MENSUAL = "MENSUAL"
    BIMESTRAL = "BIMESTRAL"


class Prestamo(Base):
    __tablename__ = "prestamos"

    id = Column(Integer, primary_key=True, index=True)
    # CORREGIDO: Usamos "clientes.id" para referenciar correctamente al modelo
    # Cliente
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    codigo_prestamo = Column(String(CODIGO_LENGTH), unique=True, index=True)

    # Montos
    monto_total = Column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=False)
    monto_financiado = Column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=False)
    monto_inicial = Column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), default=0.00)
    tasa_interes = Column(Numeric(TASA_PRECISION, TASA_SCALE), default=0.00)

    # Cuotas
    numero_cuotas = Column(Integer, nullable=False)
    monto_cuota = Column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=False)
    cuotas_pagadas = Column(Integer, default=0)
    # Se recomienda que cuotas_pendientes sea calculado, pero se mantiene como
    # columna por diseño.
    cuotas_pendientes = Column(Integer)

    # Fechas
    fecha_aprobacion = Column(
        Date, nullable=True
    )  # Hacemos nullable, ya que solo se llena al ser APROBADO
    fecha_desembolso = Column(Date)
    fecha_primer_vencimiento = Column(Date, nullable=False)
    fecha_ultimo_vencimiento = Column(Date)

    # Estado financiero
    saldo_pendiente = Column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=False)
    saldo_capital = Column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=False)
    saldo_interes = Column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), default=0.00)
    total_pagado = Column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), default=0.00)

    # Estado
    estado = Column(String(ESTADO_LENGTH), default=EstadoPrestamo.PENDIENTE.value)
    categoria = Column(String(ESTADO_LENGTH), default="NORMAL")
    modalidad = Column(String(ESTADO_LENGTH), default=ModalidadPago.TRADICIONAL.value)

    # Información adicional
    destino_credito = Column(Text)
    observaciones = Column(Text)

    # Auditoría
    creado_en = Column(TIMESTAMP, server_default=func.now())
    actualizado_en = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relaciones
    # CORREGIDO: Relación correcta con el modelo Cliente
    # cliente = relationship("Cliente", back_populates="prestamos")  # COMENTADO: Tabla prestamos vacía
    # cuotas = relationship("Cuota", back_populates="prestamo", cascade="all, delete-orphan")  # COMENTADO: Solo plantilla vacía
    # pagos = relationship("Pago", back_populates="prestamo")  # COMENTADO:
    # Solo plantilla vacía
