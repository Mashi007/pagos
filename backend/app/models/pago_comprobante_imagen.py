"""Comprobante en BD (imagen o PDF): alta manual de pago o pipeline Gmail (sin guardar el binario del comprobante en Drive)."""

from sqlalchemy import Column, DateTime, LargeBinary, String, func

from app.core.database import Base


class PagoComprobanteImagen(Base):
    __tablename__ = "pago_comprobante_imagen"

    id = Column(String(32), primary_key=True)
    content_type = Column(String(80), nullable=False)
    imagen_data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
