"""
Evidencias PDF de notificaciones archivadas desde Gmail (itmaster).
Tabla: evidencias_notificacion.
"""
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, LargeBinary, String, text
from sqlalchemy.orm import deferred

from app.core.database import Base


class EvidenciaNotificacion(Base):
    __tablename__ = "evidencias_notificacion"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    gmail_message_id = Column(String(64), nullable=False, unique=True)
    gmail_thread_id = Column(String(64), nullable=True)
    etiqueta_gmail = Column(String(40), nullable=False, index=False)
    email_cliente = Column(String(255), nullable=False)
    email_cliente_norm = Column(String(255), nullable=False, index=False)
    cedula = Column(String(50), nullable=True, index=False)
    asunto = Column(String(500), nullable=True)
    fecha_mensaje = Column(DateTime(timezone=False), nullable=True)
    pdf_contenido = deferred(Column(LargeBinary, nullable=False))
    pdf_tamano_bytes = Column(Integer, nullable=False, default=0)
    tiene_anexo = Column(Boolean, nullable=False, default=False)
    fuente_anexo = Column(String(20), nullable=True)  # gmail | sistema | ninguno
    procesado_por = Column(String(150), nullable=True)
    fecha_registro = Column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        index=False,
    )
