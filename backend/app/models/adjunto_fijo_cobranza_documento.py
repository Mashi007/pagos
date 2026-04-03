"""PDF fijos por caso de notificacion (Documentos PDF anexos): contenido en BD para sobrevivir a discos efimeros (Render)."""

from sqlalchemy import Column, DateTime, LargeBinary, String, func

from app.core.database import Base


class AdjuntoFijoCobranzaDocumento(Base):
    __tablename__ = "adjunto_fijo_cobranza_documento"

    id = Column(String(36), primary_key=True)
    tipo_caso = Column(String(32), nullable=False, index=True)
    nombre_archivo = Column(String(512), nullable=False)
    pdf_data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
