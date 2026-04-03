"""
Bitacora: autorizacion administrativa control 5 (pagos misma fecha y monto).
Tabla: auditoria_pago_control5_visto.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class AuditoriaPagoControl5Visto(Base):
    __tablename__ = "auditoria_pago_control5_visto"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pago_id = Column(Integer, ForeignKey("pagos.id", ondelete="CASCADE"), nullable=False, index=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id", ondelete="SET NULL"), nullable=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=False)
    creado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    numero_documento_anterior = Column(String(100), nullable=True)
    numero_documento_nuevo = Column(String(100), nullable=False)
    sufijo_cuatro_digitos = Column(String(4), nullable=False)
    codigo_control = Column(String(80), nullable=False, server_default="pagos_mismo_dia_monto")
