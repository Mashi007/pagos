"""
Modelo de Aprobación
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)

from app.db.session import Base


class EstadoAprobacion(str, Enum):
    """Estados posibles de una aprobación"""

    PENDIENTE = "PENDIENTE"
    APROBADA = "APROBADA"
    RECHAZADA = "RECHAZADA"
    CANCELADA = "CANCELADA"


class TipoSolicitud(str, Enum):
    """Tipos de solicitud que requieren aprobación"""

    PRESTAMO = "PRESTAMO"
    MODIFICACION_MONTO = "MODIFICACION_MONTO"
    ANULACION = "ANULACION"
    REFINANCIAMIENTO = "REFINANCIAMIENTO"
    PRORROGA = "PRORROGA"


class Prioridad(str, Enum):
    """Niveles de prioridad para aprobaciones"""

    BAJA = "BAJA"
    NORMAL = "NORMAL"
    ALTA = "ALTA"
    URGENTE = "URGENTE"


class Aprobacion(Base):
    """
    Modelo para solicitudes de aprobación
    Maneja el flujo de aprobaciones para diferentes tipos de solicitudes
    """

    __tablename__ = "aprobaciones"

    id = Column(Integer, primary_key=True, index=True)

    # Usuarios involucrados
    solicitante_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    revisor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Detalles de la solicitud
    tipo_solicitud = Column(String(50), nullable=False, index=True)  # PRESTAMO, MODIFICACION_MONTO, ANULACION, etc.
    entidad = Column(String(50), nullable=False)  # Cliente, Prestamo, Pago, etc.
    entidad_id = Column(Integer, nullable=False, index=True)

    justificacion = Column(Text, nullable=False)

    # Estado y resultado
    estado = Column(String(20), nullable=False, default="PENDIENTE", index=True)
    resultado = Column(Text, nullable=True)  # Comentarios del revisor
    fecha_aprobacion = Column(DateTime, nullable=True)

    # Fechas
    fecha_solicitud = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Archivos y evidencia
    archivo_evidencia = Column(String(255), nullable=True)  # Path del archivo adjunto
    tipo_archivo = Column(String(50), nullable=True)  # PDF, IMG, DOC, etc.
    tamaño_archivo = Column(Integer, nullable=True)  # Tamaño en bytes

    # Configuración de la solicitud
    prioridad = Column(String(20), default="NORMAL")  # BAJA, NORMAL, ALTA, URGENTE
    fecha_limite = Column(Date, nullable=True)  # Fecha límite para respuesta

    # Notificaciones
    notificado_admin = Column(Boolean, default=False)  # Si ya se notificó al admin
    notificado_solicitante = Column(Boolean, default=False)  # Si ya se notificó resultado
    visto_por_admin = Column(Boolean, default=False)

    # Control de bloqueo
    bloqueado_temporalmente = Column(Boolean, default=False)  # Si está bloqueado el registro

    # Métricas
    tiempo_respuesta_horas = Column(Integer, nullable=True)  # Tiempo que tomó responder

    # Auditoría
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Aprobacion(id={self.id}, tipo={self.tipo_solicitud}, estado={self.estado})>"

    @property
    def esta_vencida(self) -> bool:
        """Verifica si la solicitud está vencida"""
        if self.fecha_limite:
            return date.today() > self.fecha_limite and self.estado == "PENDIENTE"
        return False

    @property
    def dias_pendiente(self) -> int:
        """Calcula los días que lleva pendiente"""
        if self.estado == "PENDIENTE":
            return (datetime.utcnow() - self.fecha_solicitud).days
        return 0

    def calcular_tiempo_respuesta(self):
        """Calcula el tiempo de respuesta en horas"""
        if self.fecha_aprobacion and self.fecha_solicitud:
            delta = self.fecha_aprobacion - self.fecha_solicitud
            self.tiempo_respuesta_horas = int(delta.total_seconds() / 3600)

    def aprobar(self, revisor_id: int, resultado: Optional[str] = None):
        """Marca la solicitud como aprobada"""
        self.estado = "APROBADA"  # type: ignore[assignment]
        self.revisor_id = revisor_id  # type: ignore[assignment]
        self.resultado = resultado  # type: ignore[assignment]
        self.fecha_aprobacion = datetime.utcnow()  # type: ignore[assignment]
        self.calcular_tiempo_respuesta()

    def rechazar(self, revisor_id: int, resultado: str):
        """Marca la solicitud como rechazada"""
        self.estado = "RECHAZADA"  # type: ignore[assignment]
        self.revisor_id = revisor_id  # type: ignore[assignment]
        self.resultado = resultado  # type: ignore[assignment]
        self.fecha_aprobacion = datetime.utcnow()  # type: ignore[assignment]
        self.calcular_tiempo_respuesta()

    def cancelar(self, solicitante_id: int):
        """Cancela la solicitud"""
        self.estado = "CANCELADA"  # type: ignore[assignment]
        self.fecha_aprobacion = datetime.utcnow()  # type: ignore[assignment]

    def to_dict(self):
        """Convierte la aprobación a diccionario"""
        return {
            "id": self.id,
            "solicitante_id": self.solicitante_id,
            "revisor_id": self.revisor_id,
            "tipo_solicitud": self.tipo_solicitud,
            "entidad": self.entidad,
            "entidad_id": self.entidad_id,
            "justificacion": self.justificacion,
            "estado": self.estado,
            "resultado": self.resultado,
            "fecha_solicitud": (self.fecha_solicitud.isoformat() if self.fecha_solicitud else None),
            "fecha_aprobacion": (self.fecha_aprobacion.isoformat() if self.fecha_aprobacion else None),
            "prioridad": self.prioridad,
            "fecha_limite": (self.fecha_limite.isoformat() if self.fecha_limite else None),
            "dias_pendiente": self.dias_pendiente,
            "esta_vencida": self.esta_vencida,
            "tiempo_respuesta_horas": self.tiempo_respuesta_horas,
        }
