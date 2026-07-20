"""
Rebotes de notificaciones detectados en Gmail (buzón itmaster).
Tabla: auditoria_rebotes_gmail. Excel y listado del submódulo Auditoría.
"""
from sqlalchemy import BigInteger, Column, DateTime, String, Text, text

from app.core.database import Base


class AuditoriaReboteGmail(Base):
    __tablename__ = "auditoria_rebotes_gmail"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    gmail_message_id = Column(String(64), nullable=False, unique=True, index=True)
    gmail_thread_id = Column(String(64), nullable=True)
    cedula = Column(String(20), nullable=True, index=True)
    correo = Column(String(255), nullable=False, index=True)
    observaciones = Column(String(50), nullable=False, index=True)
    asunto_gmail = Column(String(500), nullable=True)
    remitente_detectado = Column(String(255), nullable=True)
    etiqueta_gmail = Column(String(100), nullable=True)
    fecha_mensaje = Column(DateTime(timezone=False), nullable=True)
    fecha_registro = Column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        index=True,
    )
    procesado_por = Column(String(150), nullable=True)
    fragmento_cuerpo = Column(Text, nullable=True)
