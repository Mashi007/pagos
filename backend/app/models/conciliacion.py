# backend/app/models/conciliacion.py
"""
Modelo de Conciliación Bancaria
Registra la conciliación entre pagos del sistema y movimientos bancarios
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Conciliacion(Base):
    """
    Modelo de Conciliación Bancaria
    Relaciona pagos del sistema con movimientos bancarios
    """

    __tablename__ = "conciliacion"

    # Identificación
    id = Column(Integer, primary_key=True, index=True)

    # Relación con pago
    pago_id = Column(
        Integer, ForeignKey("pagos.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Información bancaria
    fecha_carga = Column(DateTime(timezone=True), nullable=False)
    ref_bancaria = Column(String(100), nullable=False, index=True)
    monto_banco = Column(Numeric(12, 2), nullable=False)

    # Estado del match
    estado_match = Column(
        String(20), nullable=False, default="PENDIENTE", index=True
    )  # PENDIENTE, CONCILIADO, RECHAZADO, MANUAL

    # Usuario que realizó la conciliación
    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Información adicional
    observaciones = Column(Text, nullable=True)
    tipo_match = Column(String(20), nullable=True)  # AUTOMATICO, MANUAL
    confianza_match = Column(Numeric(5, 2), nullable=True)  # Porcentaje de confianza

    # Auditoría
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relaciones
    pago = relationship("Pago", back_populates="conciliacion")
    usuario = relationship("User")

    def __repr__(self):
        return f"<Conciliacion Pago:{self.pago_id} - {self.estado_match}>"

    @property
    def esta_conciliado(self) -> bool:
        """Verifica si está conciliado"""
        return self.estado_match == "CONCILIADO"

    @property
    def diferencia_monto(self) -> Decimal:
        """Calcula la diferencia entre monto del sistema y banco"""
        if self.pago:
            return abs(self.monto_banco - self.pago.monto_pagado)
        return Decimal("0.00")

    def marcar_conciliado(self, usuario_id: int, observaciones: str = None):
        """Marca como conciliado"""
        self.estado_match = "CONCILIADO"
        self.usuario_id = usuario_id
        self.observaciones = observaciones
        self.updated_at = datetime.utcnow()

    def marcar_rechazado(self, usuario_id: int, motivo: str):
        """Marca como rechazado"""
        self.estado_match = "RECHAZADO"
        self.usuario_id = usuario_id
        self.observaciones = motivo
        self.updated_at = datetime.utcnow()
