"""
Modelo de Auditoría de Pagos
Registra todos los cambios realizados en los pagos
"""

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.session import Base


class PagoAuditoria(Base):
    """
    Modelo para auditoría de pagos
    Registra todos los cambios realizados en los pagos
    """

    __tablename__ = "pagos_auditoria"

    id = Column(Integer, primary_key=True, index=True)
    pago_id = Column(Integer, nullable=False, index=True)

    # Información del cambio
    usuario = Column(String(100), nullable=False)  # Email del usuario
    campo_modificado = Column(String(100), nullable=False)  # Campo que se modificó
    valor_anterior = Column(String(500), nullable=True)  # Valor anterior
    valor_nuevo = Column(String(500), nullable=False)  # Valor nuevo

    # Detalles del cambio
    accion = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE
    observaciones = Column(Text, nullable=True)  # Observaciones adicionales

    # Fecha del cambio
    fecha_cambio = Column(DateTime, nullable=False, index=True)

    def __repr__(self):
        return f"<PagoAuditoria(id={self.id}, pago_id={self.pago_id}, usuario={self.usuario}, accion={self.accion})>"
