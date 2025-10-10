# backend/app/models/notificacion.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.session import Base
from app.core.constants import TipoNotificacion, EstadoNotificacion


class Notificacion(Base):
    __tablename__ = "notificaciones"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Tipo y estado
    tipo = Column(SQLEnum(TipoNotificacion), nullable=False)
    estado = Column(SQLEnum(EstadoNotificacion), default=EstadoNotificacion.PENDIENTE)
    
    # Destinatario
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)
    email_destinatario = Column(String, nullable=True)
    telefono_destinatario = Column(String, nullable=True)
    
    # Contenido
    asunto = Column(String, nullable=True)
    mensaje = Column(Text, nullable=False)
    template_id = Column(String, nullable=True)  # recordatorio_3d, mora_1d, etc.
    
    # Referencia
    prestamo_id = Column(Integer, ForeignKey("prestamos.id"), nullable=True)
    pago_id = Column(Integer, ForeignKey("pagos.id"), nullable=True)
    
    # Metadata de envío
    fecha_programada = Column(DateTime, nullable=True)
    fecha_enviada = Column(DateTime, nullable=True)
    intentos_envio = Column(Integer, default=0)
    error_mensaje = Column(Text, nullable=True)
    
    # Quién la envió
    enviado_por = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Auditoría
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    cliente = relationship("Cliente", backref="notificaciones")
    prestamo = relationship("Prestamo", backref="notificaciones")
    pago = relationship("Pago", backref="notificaciones")
    enviado_por_usuario = relationship("User", back_populates="notificaciones_enviadas")
    
    def __repr__(self):
        return f"<Notificacion {self.tipo} - {self.estado}>"
