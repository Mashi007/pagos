"""
Modelo de Préstamo
Define la estructura básica de un préstamo.
Sincronizado con el endpoint de aprobaciones.
"""

from datetime import date
from enum import Enum
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.db.session import Base


class EstadoPrestamo(str, Enum):
    """Estados posibles de un préstamo"""

    PENDIENTE = "PENDIENTE"
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"
    DESEMBOLSADO = "DESEMBOLSADO"
    EN_PAGO = "EN_PAGO"
    PAGADO = "PAGADO"
    VENCIDO = "VENCIDO"
    CANCELADO = "CANCELADO"


class ModalidadPago(str, Enum):
    """Modalidades de pago disponibles"""

    TRADICIONAL = "TRADICIONAL"
    BALLOON = "BALLOON"
    INTERES_FIJO = "INTERES_FIJO"


class Prestamo(Base):
    """
    Modelo para préstamos
    Representa los préstamos otorgados a los clientes
    """

    __tablename__ = "prestamos"

    # Constantes
    CODIGO_LENGTH = 20
    NUMERIC_PRECISION = 12
    NUMERIC_SCALE = 2
    TASA_PRECISION = 5
    TASA_SCALE = 2
    ESTADO_LENGTH = 20

    id = Column(Integer, primary_key=True, index=True)

    # Cliente
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    codigo_prestamo = Column(String(CODIGO_LENGTH), unique=True, index=True)

    # Montos
    monto_solicitado = Column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=False)
    monto_aprobado = Column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=False)
    monto_inicial = Column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), default=0.00)
    tasa_interes_anual = Column(Numeric(TASA_PRECISION, TASA_SCALE), default=0.00)

    # Cuotas
    numero_cuotas = Column(Integer, nullable=False)
    monto_cuota = Column(Numeric(NUMERIC_PRECISION, NUMERIC_SCALE), nullable=False)
    cuotas_pagadas = Column(Integer, default=0)
    cuotas_pendientes = Column(Integer)

    # Fechas
    fecha_solicitud = Column(DateTime, default=func.now(), nullable=False)
    fecha_aprobacion = Column(DateTime, nullable=True)
    fecha_desembolso = Column(Date, nullable=True)
    fecha_primer_vencimiento = Column(Date, nullable=False)
    fecha_ultimo_vencimiento = Column(Date, nullable=True)

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
    destino_credito = Column(Text, nullable=True)
    observaciones = Column(Text, nullable=True)

    # Auditoría
    creado_en = Column(DateTime, server_default=func.now())
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Prestamo(id={self.id}, cliente_id={self.cliente_id}, estado={self.estado})>"

    @property
    def esta_aprobado(self) -> bool:
        """Verifica si el préstamo está aprobado"""
        return self.estado == EstadoPrestamo.APROBADO

    @property
    def esta_pagado(self) -> bool:
        """Verifica si el préstamo está completamente pagado"""
        return self.estado == EstadoPrestamo.PAGADO

    @property
    def esta_vencido(self) -> bool:
        """Verifica si el préstamo está vencido"""
        return self.estado == EstadoPrestamo.VENCIDO

    def calcular_saldo_pendiente(self) -> float:
        """Calcula el saldo pendiente del préstamo"""
        if self.monto_aprobado and self.total_pagado:
            return float(self.monto_aprobado - self.total_pagado)
        return float(self.monto_aprobado) if self.monto_aprobado else 0.0

    def actualizar_estado(self):
        """Actualiza el estado del préstamo basado en el progreso de pago"""
        if self.saldo_pendiente <= 0:
            self.estado = EstadoPrestamo.PAGADO
        elif self.cuotas_pagadas > 0:
            self.estado = EstadoPrestamo.EN_PAGO
        elif self.fecha_aprobacion:
            self.estado = EstadoPrestamo.APROBADO

    def to_dict(self):
        """Convierte el préstamo a diccionario"""
        return {
            "id": self.id,
            "cliente_id": self.cliente_id,
            "codigo_prestamo": self.codigo_prestamo,
            "monto_solicitado": (
                float(self.monto_solicitado) if self.monto_solicitado else None
            ),
            "monto_aprobado": (
                float(self.monto_aprobado) if self.monto_aprobado else None
            ),
            "monto_inicial": float(self.monto_inicial) if self.monto_inicial else None,
            "tasa_interes_anual": (
                float(self.tasa_interes_anual) if self.tasa_interes_anual else None
            ),
            "numero_cuotas": self.numero_cuotas,
            "monto_cuota": float(self.monto_cuota) if self.monto_cuota else None,
            "cuotas_pagadas": self.cuotas_pagadas,
            "cuotas_pendientes": self.cuotas_pendientes,
            "fecha_solicitud": (
                self.fecha_solicitud.isoformat() if self.fecha_solicitud else None
            ),
            "fecha_aprobacion": (
                self.fecha_aprobacion.isoformat() if self.fecha_aprobacion else None
            ),
            "fecha_desembolso": (
                self.fecha_desembolso.isoformat() if self.fecha_desembolso else None
            ),
            "fecha_primer_vencimiento": (
                self.fecha_primer_vencimiento.isoformat()
                if self.fecha_primer_vencimiento
                else None
            ),
            "fecha_ultimo_vencimiento": (
                self.fecha_ultimo_vencimiento.isoformat()
                if self.fecha_ultimo_vencimiento
                else None
            ),
            "saldo_pendiente": (
                float(self.saldo_pendiente) if self.saldo_pendiente else None
            ),
            "saldo_capital": float(self.saldo_capital) if self.saldo_capital else None,
            "saldo_interes": float(self.saldo_interes) if self.saldo_interes else None,
            "total_pagado": float(self.total_pagado) if self.total_pagado else None,
            "estado": self.estado,
            "categoria": self.categoria,
            "modalidad": self.modalidad,
            "destino_credito": self.destino_credito,
            "observaciones": self.observaciones,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "actualizado_en": (
                self.actualizado_en.isoformat() if self.actualizado_en else None
            ),
        }
