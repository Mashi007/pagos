"""
Registro de envíos de notificaciones por email (éxito/fallo) para estadísticas y rebotados.
Tabla: envios_notificacion. Usado por GET estadisticas-por-tab y GET rebotados-por-tab.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, LargeBinary, JSON, func
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.envio_notificacion_adjunto import EnvioNotificacionAdjunto


class EnvioNotificacion(Base):
    __tablename__ = "envios_notificacion"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    fecha_envio = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    tipo_tab = Column(String(20), nullable=False, index=True)  # dias_5, hoy, dias_1_retraso, prejudicial, ...
    asunto = Column(String(500), nullable=True)  # asunto del email enviado (historial/legal)
    email = Column(String(255), nullable=False)
    nombre = Column(String(255), nullable=True)
    cedula = Column(String(50), nullable=True, index=True)  # consulta historial por cédula
    exito = Column(Boolean, nullable=False)  # True = enviado, False = rebotado/fallo
    error_mensaje = Column(Text, nullable=True)
    prestamo_id = Column(Integer, nullable=True, index=True)  # para COBRANZA
    correlativo = Column(Integer, nullable=True)  # numero correlativo por prestamo
    mensaje_html = Column(Text, nullable=True)
    mensaje_texto = Column(Text, nullable=True)
    comprobante_pdf = Column(LargeBinary, nullable=True)
    # Metadatos SMTP/socket al enviar (prueba de entrega al relay; no constata lectura en buzon).
    metadata_tecnica = Column(JSON, nullable=True)

    adjuntos = relationship(
        EnvioNotificacionAdjunto,
        back_populates="envio",
        cascade="all, delete-orphan",
        order_by=EnvioNotificacionAdjunto.orden,
    )
