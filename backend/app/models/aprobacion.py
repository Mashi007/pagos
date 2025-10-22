# backend/app/models/aprobacion.py
""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session, relationship
from sqlalchemy import ForeignKey, Text, Numeric, JSON, Boolean, Enum
from fastapi import APIRouter, Depends, HTTPException, Query, status
Modelo de Aprobación
Sistema de workflow para solicitudes que requieren aprobación
""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Date, Boolean

from sqlalchemy.sql import func

from app.db.session import Base

class Aprobacion(Base):
    """
    Modelo de Aprobación para workflow de solicitudes
    """
    __tablename__ = "aprobaciones"
    __table_args__ = {'extend_existing': True}

    # Identificación
    id = Column(Integer, primary_key=True, index=True)

    # Estado - Valores posibles: PENDIENTE, APROBADA, RECHAZADA, CANCELADA
    estado = Column(
        String(20),
        nullable=False,
        default="PENDIENTE",
        index=True
    )

    # Solicitante y revisor
    solicitante_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    revisor_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Detalles de la solicitud
    tipo_solicitud = Column(
        String(50),
        nullable=False,
        index=True
    )  # PRESTAMO, MODIFICACION_MONTO, ANULACION, etc.

    entidad = Column(String(50), nullable=False)  # Cliente, Prestamo, Pago, etc.
    entidad_id = Column(Integer, nullable=False, index=True)

    # Justificación y comentarios
    justificacion = Column(Text, nullable=False)
    comentarios_revisor = Column(Text, nullable=True)

    # Datos de la solicitud (JSON serializado como string)
    datos_solicitados = Column(Text, nullable=True)

    # Fechas
    fecha_solicitud = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    fecha_revision = Column(DateTime(timezone=True), nullable=True)

    # NUEVOS CAMPOS PARA SISTEMA COMPLETO DE APROBACIONES
    archivo_evidencia = Column(String(255), nullable=True)  # Path del archivo adjunto
    tipo_archivo = Column(String(50), nullable=True)        # PDF, IMG, DOC, etc.
    tamaño_archivo = Column(Integer, nullable=True)         # Tamaño en bytes
    prioridad = Column(String(20), default="NORMAL")        # BAJA, NORMAL, ALTA, URGENTE
    fecha_limite = Column(Date, nullable=True)              # Fecha límite para respuesta
    notificado_admin = Column(Boolean, default=False)       # Si ya se notificó al admin
    notificado_solicitante = Column(Boolean, default=False) # Si ya se notificó resultado
    bloqueado_temporalmente = Column(Boolean, default=True) # Si está bloqueado el registro

    # Campos de seguimiento
    visto_por_admin = Column(Boolean, default=False)
    fecha_visto = Column(DateTime(timezone=True), nullable=True)
    tiempo_respuesta_horas = Column(Integer, nullable=True)  # Tiempo que tomó responder

    # Auditoría
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), onupdate=func.now())

    # Relaciones
    solicitante = relationship(
        "User",
        foreign_keys=[solicitante_id],
        back_populates="aprobaciones_solicitadas"
    )
    revisor = relationship(
        "User",
        foreign_keys=[revisor_id],
        back_populates="aprobaciones_revisadas"
    )

    def __repr__(self):
        return f"<Aprobacion {self.tipo_solicitud} - {self.estado}>"

    @property
    def esta_pendiente(self) -> bool:
        """Verifica si la aprobación está pendiente"""
        from app.core.constants import EstadoAprobacion
        return self.estado == EstadoAprobacion.PENDIENTE.value

    @property
    def esta_aprobada(self) -> bool:
        """Verifica si la aprobación fue aprobada"""
        return self.estado == EstadoAprobacion.APROBADA.value

    @property
    def esta_rechazada(self) -> bool:
        """Verifica si la aprobación fue rechazada"""
        return self.estado == EstadoAprobacion.RECHAZADA.value

    def aprobar(self, revisor_id: int, comentarios: str = None):
        """Marca la aprobación como aprobada"""
        self.estado = EstadoAprobacion.APROBADA.value
        self.revisor_id = revisor_id
        self.comentarios_revisor = comentarios
        self.fecha_revision = datetime.utcnow()

    def rechazar(self, revisor_id: int, comentarios: str):
        """Marca la aprobación como rechazada"""
        self.estado = EstadoAprobacion.RECHAZADA.value
        self.revisor_id = revisor_id
        self.comentarios_revisor = comentarios
        self.fecha_revision = datetime.utcnow()
        self.bloqueado_temporalmente = False  # Desbloquear
        self._calcular_tiempo_respuesta()

    def cancelar(self):
        """Cancela la solicitud de aprobación"""
        self.estado = EstadoAprobacion.CANCELADA.value

    def marcar_como_visto(self, admin_id: int):
        """Marcar solicitud como vista por admin"""
        self.visto_por_admin = True
        self.fecha_visto = datetime.utcnow()

    def adjuntar_archivo(self, archivo_path: str, tipo: str, tamaño: int):
        """Adjuntar archivo de evidencia"""
        self.archivo_evidencia = archivo_path
        self.tipo_archivo = tipo
        self.tamaño_archivo = tamaño

    def establecer_prioridad(self, prioridad: str):
        """Establecer prioridad de la solicitud"""
        prioridades_validas = ["BAJA", "NORMAL", "ALTA", "URGENTE"]
        if prioridad in prioridades_validas:
            self.prioridad = prioridad

    def marcar_notificado_admin(self):
        """Marcar que se notificó al admin"""
        self.notificado_admin = True

    def marcar_notificado_solicitante(self):
        """Marcar que se notificó al solicitante"""
        self.notificado_solicitante = True

    def _calcular_tiempo_respuesta(self):
        """Calcular tiempo de respuesta en horas"""
        if self.fecha_revision and self.fecha_solicitud:
            delta = self.fecha_revision - self.fecha_solicitud
            self.tiempo_respuesta_horas = int(delta.total_seconds() / 3600)

    @property
    def esta_vencida(self) -> bool:
        """Verificar si la solicitud está vencida"""
        if not self.fecha_limite:
            return False
        
        return date.today() > self.fecha_limite

    @property
    def dias_pendiente(self) -> int:
        """Días que lleva pendiente la solicitud"""
        if self.estado != "PENDIENTE":
            return 0
        delta = datetime.utcnow() - self.fecha_solicitud
        return delta.days

    @property
    def requiere_atencion_urgente(self) -> bool:
        """Si requiere atención urgente"""
        return (
            self.prioridad == "URGENTE" or
            self.esta_vencida or
            self.dias_pendiente > 2
        )
