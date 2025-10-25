from datetime import date
"""Modelo de Préstamo
Define la estructura básica de un préstamo.
Sincronizado con el endpoint de aprobaciones.
"""

from enum import Enum
from sqlalchemy import 
from sqlalchemy.sql import func

from app.db.session import Base

CODIGO_LENGTH = 20
NUMERIC_PRECISION = 12
NUMERIC_SCALE = 2
TASA_PRECISION = 5
TASA_SCALE = 2
ESTADO_LENGTH = 20


# --- Enumeraciones ---


class EstadoPrestamo(str, Enum):
    PENDIENTE = "PENDIENTE"  # Solicitud inicial
    EN_APROBACION = 
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

    id = Column(Integer, primary_key=True, index=True)

    # Cliente
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    codigo_prestamo = Column(String(CODIGO_LENGTH), unique=True, index=True)

    monto_total = Column
        Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=False
    monto_financiado = Column
        Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=False
    monto_inicial = Column
        Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), default=0.00
    tasa_interes = Column(Numeric(TASA_PRECISION, TASA_SCALE), default=0.00)

    # Cuotas
    numero_cuotas = Column(Integer, nullable=False)
    monto_cuota = Column
        Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=False
    cuotas_pagadas = Column(Integer, default=0)
    # Se recomienda que cuotas_pendientes sea calculado, pero se mantiene como
    # columna por diseño.
    cuotas_pendientes = Column(Integer)

    # Fechas
    fecha_aprobacion = Column
    fecha_desembolso = Column(Date)
    fecha_primer_vencimiento = Column(Date, nullable=False)
    fecha_ultimo_vencimiento = Column(Date)

    # Estado financiero
    saldo_pendiente = Column
        Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=False
    saldo_capital = Column
        Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=False
    saldo_interes = Column
        Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), default=0.00
    total_pagado = Column
        Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), default=0.00

    # Estado
    estado = Column
        String(ESTADO_LENGTH), default=EstadoPrestamo.PENDIENTE.value
    categoria = Column(String(ESTADO_LENGTH), default="NORMAL")
    modalidad = Column
        String(ESTADO_LENGTH), default=ModalidadPago.TRADICIONAL.value

    # Información adicional
    destino_credito = Column(Text)
    observaciones = Column(Text)

    # Auditoría
    creado_en = Column(TIMESTAMP, server_default=func.now())
    actualizado_en = Column
        TIMESTAMP, server_default=func.now(), onupdate=func.now()

    # Relaciones
    # CORREGIDO: Relación correcta con el modelo Cliente
    # cuotas = relationship
    # cascade="all, delete-orphan")  # COMENTADO: Solo plantilla vacía
    # Solo plantilla vacía

"""
"""