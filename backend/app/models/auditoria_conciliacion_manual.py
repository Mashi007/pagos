# -*- coding: utf-8 -*-
"`"
Modelo SQLAlchemy para auditoría de conciliación manual.
Registra cada asignación manual o automática de pagos a cuotas.
"`"
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class AuditoriaConciliacionManual(Base):
    __tablename__ = 'auditoria_conciliacion_manual'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pago_id = Column(Integer, ForeignKey('pagos.id', ondelete='CASCADE'), nullable=False, index=True)
    cuota_id = Column(Integer, ForeignKey('cuotas.id', ondelete='CASCADE'), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id', ondelete='SET NULL'), nullable=True)
    monto_asignado = Column(Numeric(14, 2), nullable=False)
    tipo_asignacion = Column(String(20), nullable=False, server_default='MANUAL')  # MANUAL o AUTOMATICA
    motivo = Column(Text, nullable=True)
    resultado = Column(String(20), nullable=False, server_default='EXITOSA')  # EXITOSA, FALLIDA
    fecha_asignacion = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    creado_en = Column(DateTime(timezone=True), nullable=True, server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
