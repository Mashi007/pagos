"""
Modelo SQLAlchemy para campañas CRM (envío de correo masivo por lotes).
Tabla: crm_campana. Destinatarios: correos de tabla clientes.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, LargeBinary, func

from app.core.database import Base


class CampanaCrm(Base):
    __tablename__ = "crm_campana"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(200), nullable=False)
    asunto = Column(String(500), nullable=False)
    cuerpo_texto = Column(Text, nullable=False)
    cuerpo_html = Column(Text, nullable=True)
    estado = Column(String(20), nullable=False, index=True, default="borrador")
    total_destinatarios = Column(Integer, nullable=False, default=0)
    enviados = Column(Integer, nullable=False, default=0)
    fallidos = Column(Integer, nullable=False, default=0)
    batch_size = Column(Integer, nullable=False, default=25)
    delay_entre_batches_seg = Column(Integer, nullable=False, default=3)
    cc_emails = Column(Text, nullable=True)
    adjunto_nombre = Column(String(255), nullable=True)
    adjunto_contenido = Column(LargeBinary, nullable=True)
    fecha_creacion = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    fecha_envio_inicio = Column(DateTime(timezone=False), nullable=True)
    fecha_envio_fin = Column(DateTime(timezone=False), nullable=True)
    usuario_creacion = Column(String(255), nullable=True)
