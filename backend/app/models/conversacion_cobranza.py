"""
Modelo para estado de conversación del flujo de cobranza por WhatsApp.
Flujo: esperando_cedula → esperando_confirmacion → esperando_foto → (OCR) esperando_confirmacion_datos → guardado.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import text

from app.core.database import Base


class ConversacionCobranza(Base):
    __tablename__ = "conversacion_cobranza"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    telefono = Column(String(30), nullable=False, unique=True, index=True)
    cedula = Column(String(20), nullable=True)
    nombre_cliente = Column(String(100), nullable=True)
    estado = Column(String(30), nullable=False, default="esperando_cedula")
    intento_cedula = Column(Integer, nullable=False, default=0)
    intento_foto = Column(Integer, nullable=False, default=0)
    intento_confirmacion = Column(Integer, nullable=False, default=0)
    observacion = Column(Text, nullable=True)
    pagos_informe_id_pendiente = Column(Integer, ForeignKey("pagos_informes.id", ondelete="SET NULL"), nullable=True)
    # Confirmación punto a punto: 0=cedula, 1=cantidad, 2=numero_documento
    confirmacion_paso = Column(Integer, nullable=False, default=0)
    # Si está puesto, esperamos que el cliente escriba el valor correcto para este campo
    confirmacion_esperando_valor = Column(String(30), nullable=True)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
