"""
Bitacora de revision humana sobre alertas de auditoria de cartera (Paso 4).
Tabla: auditoria_cartera_revision. Append-only; el ultimo evento por (prestamo_id, codigo_control) gobierna si se oculta en UI (tipo MARCAR_OK).
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class AuditoriaCarteraRevision(Base):
    __tablename__ = "auditoria_cartera_revision"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id"), nullable=False, index=True)
    codigo_control = Column(String(80), nullable=False)
    tipo = Column(String(30), nullable=False, server_default="MARCAR_OK")
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    nota = Column(Text, nullable=True)
    creado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
