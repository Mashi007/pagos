"""
Solicitudes de reapertura de revisión manual cuando el préstamo está en Visto (revisado).
Los operarios no pueden editar ni reabrir; registran una solicitud que ven los administradores.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func, text

from app.core.database import Base


class RevisionManualSolicitudReapertura(Base):
    __tablename__ = "revision_manual_solicitudes_reapertura"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id", ondelete="CASCADE"), nullable=False, index=True)
    solicitante_usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    solicitante_email = Column(String(255), nullable=True)
    mensaje = Column(Text, nullable=True)
    # pendiente | aprobada | rechazada
    estado = Column(String(20), nullable=False, index=True, server_default=text("'pendiente'"))
    resuelto_por_usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    nota_resolucion = Column(Text, nullable=True)
    creado_en = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    actualizado_en = Column(DateTime(timezone=False), nullable=False, server_default=func.now(), onupdate=func.now())
    resuelto_en = Column(DateTime(timezone=False), nullable=True)
