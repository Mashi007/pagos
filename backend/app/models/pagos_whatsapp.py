"""
Modelo para imágenes recibidas por WhatsApp (tabla pagos_whatsapp).

El binario canónico del comprobante vive en `pago_comprobante_imagen` (`comprobante_imagen_id`).
`imagen` queda solo para filas legacy o respaldo si falla el insert en la tabla única.
`link_imagen`: URL pública (p. ej. Google Drive) además del comprobante en BD.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.sql import text

from app.core.database import Base


class PagosWhatsapp(Base):
    __tablename__ = "pagos_whatsapp"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    fecha = Column(DateTime(timezone=False), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    cedula_cliente = Column(String(20), nullable=True, index=True)
    comprobante_imagen_id = Column(
        String(32),
        ForeignKey("pago_comprobante_imagen.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    imagen = Column(LargeBinary, nullable=True)
    link_imagen = Column(Text, nullable=True)
