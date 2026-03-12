"""
Registro de envÃ­os de notificaciones por email (Ã©xito/fallo) para estadÃ­sticas y rebotados.
Tabla: envios_notificacion. Usado por GET estadisticas-por-tab y GET rebotados-por-tab.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, func

from app.core.database import Base


class EnvioNotificacion(Base):
    __tablename__ = "envios_notificacion"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    fecha_envio = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    tipo_tab = Column(String(20), nullable=False, index=True)  # dias_5, dias_3, dias_1, hoy, mora_90
    email = Column(String(255), nullable=False)
    nombre = Column(String(255), nullable=True)
    cedula = Column(String(50), nullable=True)
    exito = Column(Boolean, nullable=False)  # True = enviado, False = rebotado/fallo
    error_mensaje = Column(Text, nullable=True)
    prestamo_id = Column(Integer, nullable=True, index=True)  # para COBRANZA
    correlativo = Column(Integer, nullable=True)  # numero correlativo por prestamo
