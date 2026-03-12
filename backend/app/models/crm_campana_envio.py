"""
Registro de cada envío por campaña CRM (éxito/fallo por destinatario).
Tabla: crm_campana_envio.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey

from app.core.database import Base


class CampanaEnvioCrm(Base):
    __tablename__ = "crm_campana_envio"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    campana_id = Column(Integer, ForeignKey("crm_campana.id", ondelete="CASCADE"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True, index=True)
    email = Column(String(255), nullable=False)
    estado = Column(String(20), nullable=False, index=True, default="pendiente")
    fecha_envio = Column(DateTime(timezone=False), nullable=True)
    error_mensaje = Column(Text, nullable=True)
