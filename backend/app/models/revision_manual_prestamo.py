"""
Modelo SQLAlchemy para Revisión Manual de Préstamos (post-migración).
Tabla de monitoreo para verificación manual de cada préstamo.
Historial de cambios y auditoría de la revisión manual.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func, text

from app.core.database import Base


class RevisionManualPrestamo(Base):
    __tablename__ = "revision_manual_prestamos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id"), nullable=False, index=True, unique=True)
    estado_revision = Column(String(20), nullable=False, index=True, server_default="'pendiente'")  # pendiente, revisando, revisado
    usuario_revision_id = Column(Integer, nullable=True)  # Usuario que realizó la revisión
    usuario_revision_email = Column(String(255), nullable=True)
    fecha_revision = Column(DateTime(timezone=False), nullable=True)  # Fecha cuando se marcó como revisado
    observaciones = Column(Text, nullable=True)  # Observaciones del revisor
    cambios_realizados = Column(Text, nullable=True)  # JSON con historial de cambios
    cliente_editado = Column(Boolean, nullable=False, server_default=text("false"))
    prestamo_editado = Column(Boolean, nullable=False, server_default=text("false"))
    pagos_editados = Column(Boolean, nullable=False, server_default=text("false"))
    creado_en = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    actualizado_en = Column(DateTime(timezone=False), nullable=False, server_default=func.now(), onupdate=func.now())
