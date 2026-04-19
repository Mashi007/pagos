"""Auditoría de altas de clientes desde snapshot Drive (pestaña CONCILIACIÓN)."""
from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.core.database import Base


class AuditoriaClienteAltaDesdeDrive(Base):
    __tablename__ = "auditoria_cliente_alta_desde_drive"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(40), nullable=False, index=True)
    sheet_row_number = Column(Integer, nullable=False)
    cedula = Column(String(32), nullable=False)
    nombres = Column(Text, nullable=True)
    telefono = Column(String(120), nullable=True)
    email = Column(String(200), nullable=True)
    comentario = Column(Text, nullable=True)
    usuario_email = Column(String(200), nullable=False)
    estado = Column(String(32), nullable=False)
    detalle_error = Column(Text, nullable=True)
    creado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
