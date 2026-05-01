"""
Modelo SQLAlchemy para borrador temporal de Revisión Manual de Préstamos.
Almacena cambios en estado transitorio antes de validar y confirmar en BD real.
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from app.core.database import Base


class RevisionManualPrestamoTemp(Base):
    __tablename__ = "revision_manual_prestamos_temp"

    id = Column(String(36), primary_key=True, nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id", ondelete="CASCADE"), nullable=False, index=True)

    # Draft de cambios (almacenados como JSON strings)
    cliente_datos_json = Column(Text, nullable=True)
    prestamo_datos_json = Column(Text, nullable=True)
    cuotas_datos_json = Column(Text, nullable=True)
    pagos_datos_json = Column(Text, nullable=True)

    # Estado del borrador
    estado = Column(String(20), nullable=False, default="borrador", index=True)

    # Resultado de validación
    validadores_resultado = Column(Text, nullable=True)
    error_mensaje = Column(Text, nullable=True)

    creado_en = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    actualizado_en = Column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_revision_manual_temp_prestamo_usuario", prestamo_id, usuario_id),
        Index("ix_revision_manual_temp_estado", estado),
        Index("ix_revision_manual_temp_creado", creado_en),
    )
