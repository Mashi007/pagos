"""Imagen de comprobante subida desde el formulario de registro de pago (contenido en BD; sin disco persistente en Render)."""

from sqlalchemy import Column, DateTime, LargeBinary, String, func

from app.core.database import Base


class PagoComprobanteImagen(Base):
    __tablename__ = "pago_comprobante_imagen"

    id = Column(String(32), primary_key=True)
    content_type = Column(String(80), nullable=False)
    imagen_data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
