# backend/app/models/notificacion.py
"""
Modelo de Notificación
Sistema de notificaciones por email, SMS o WhatsApp
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.db.base import Base


class Notificacion(Base):
    """
    Modelo de Notificación para comunicaciones con usuarios/clientes
    """
    __tablename__ = "notificaciones"
    
    # Identificación
    id = Column(Integer, primary_key=True, index=True)
    
    # Destinatario (puede ser un User o un Cliente por email/teléfono)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    cliente_id = Column(
        Integer,
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Destinatario manual (si no es user ni cliente registrado)
    destinatario_email = Column(String(255), nullable=True)
    destinatario_telefono = Column(String(20), nullable=True)
    destinatario_nombre = Column(String(255), nullable=True)
    
    # Tipo de notificación
    tipo = Column(
        String(50),
        nullable=False,
        index=True
    )  # EMAIL, SMS, WHATSAPP, PUSH
    
    # Categoría
    categoria = Column(
        String(50),
        nullable=False,
        index=True
    )  # RECORDATORIO_PAGO, PRESTAMO_APROBADO, CUOTA_VENCIDA, etc.
    
    # Contenido
    asunto = Column(String(255), nullable=True)
    mensaje = Column(Text, nullable=False)
    
    # Datos adicionales (JSON)
    metadata = Column(JSON, nullable=True)
    
    # Estado de envío
    estado = Column(
        String(20),
        nullable=False,
        default="PENDIENTE",
        index=True
    )  # PENDIENTE, ENVIADA, FALLIDA, LEIDA
    
    # Intentos de envío
    intentos = Column(Integer, default=0)
    max_intentos = Column(Integer, default=3)
    
    # Fechas
    programada_para = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )  # Para notificaciones programadas
    
    enviada_en = Column(DateTime(timezone=True), nullable=True)
    leida_en = Column(DateTime(timezone=True), nullable=True)
    
    # Respuesta del servicio de envío
    respuesta_servicio = Column(Text, nullable=True)
    error_mensaje = Column(Text, nullable=True)
    
    # Prioridad
    prioridad = Column(
        String(10),
        nullable=False,
        default="NORMAL"
    )  # BAJA, NORMAL, ALTA, URGENTE
    
    # Auditoría
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    user = relationship("User", back_populates="notificaciones")
    cliente = relationship("Cliente", back_populates="notificaciones")
    
    def __repr__(self):
        return f"<Notificacion {self.tipo} - {self.categoria} - {self.estado}>"
    
    @property
    def esta_pendiente(self) -> bool:
        """Verifica si la notificación está pendiente"""
        return self.estado == "PENDIENTE"
    
    @property
    def fue_enviada(self) -> bool:
        """Verifica si la notificación fue enviada"""
        return self.estado == "ENVIADA"
    
    @property
    def fallo(self) -> bool:
        """Verifica si la notificación falló"""
        return self.estado == "FALLIDA"
    
    @property
    def puede_reintentar(self) -> bool:
        """Verifica si se puede reintentar el envío"""
        return self.intentos < self.max_intentos and self.fallo
    
    def marcar_enviada(self, respuesta: str = None):
        """Marca la notificación como enviada"""
        self.estado = "ENVIADA"
        self.enviada_en = datetime.utcnow()
        self.respuesta_servicio = respuesta
    
    def marcar_fallida(self, error: str):
        """Marca la notificación como fallida"""
        self.estado = "FALLIDA"
        self.error_mensaje = error
        self.intentos += 1
    
    def marcar_leida(self):
        """Marca la notificación como leída"""
        if self.estado == "ENVIADA":
            self.leida_en = datetime.utcnow()
    
    @classmethod
    def crear_recordatorio_pago(
        cls,
        cliente_id: int,
        tipo: str,
        mensaje: str,
        programada_para: datetime = None
    ):
        """
        Helper para crear notificaciones de recordatorio de pago
        
        Args:
            cliente_id: ID del cliente
            tipo: EMAIL, SMS o WHATSAPP
            mensaje: Mensaje de la notificación
            programada_para: Fecha/hora programada (opcional)
            
        Returns:
            Notificacion: Instancia de notificación
        """
        return cls(
            cliente_id=cliente_id,
            tipo=tipo,
            categoria="RECORDATORIO_PAGO",
            asunto="Recordatorio de Pago",
            mensaje=mensaje,
            programada_para=programada_para,
            prioridad="ALTA"
        )
