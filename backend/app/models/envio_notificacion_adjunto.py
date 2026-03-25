"""Adjuntos persistidos de un envío de notificación (snapshot al momento del envío)."""

from sqlalchemy import Column, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class EnvioNotificacionAdjunto(Base):
    __tablename__ = "envios_notificacion_adjuntos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    envio_notificacion_id = Column(
        Integer,
        ForeignKey("envios_notificacion.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nombre_archivo = Column(String(255), nullable=False)
    contenido = Column(LargeBinary, nullable=False)
    orden = Column(Integer, nullable=False, default=0)

    envio = relationship("EnvioNotificacion", back_populates="adjuntos")
