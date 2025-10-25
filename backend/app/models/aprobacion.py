from datetime import date, timedelta as delta
# backend/app/models/aprobacion.py
"""Modelo de Aprobación"""
Sistema de workflow para solicitudes que requieren aprobación
""""""

# from sqlalchemy import  # TODO: Agregar imports específicos
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.constants import EstadoAprobacion
from app.db.session import Base


class Aprobacion(Base):
    """"""
    Modelo de Aprobación para workflow de solicitudes
    """"""
    __tablename__ = "aprobaciones"
    __table_args__ = {"extend_existing": True}

    # Identificación
    id = Column(Integer, primary_key=True, index=True)

    estado = Column
        String(20), nullable=False, default="PENDIENTE", index=True

    # Solicitante y revisor
    solicitante_id = Column
    revisor_id = Column

    # Detalles de la solicitud
    tipo_solicitud = Column
        String(50), nullable=False, index=True
    )  # PRESTAMO, MODIFICACION_MONTO, ANULACION, etc.
    entidad = Column
        String(50), nullable=False
    )  # Cliente, Prestamo, Pago, etc.
    entidad_id = Column(Integer, nullable=False, index=True)

    justificacion = Column(Text, nullable=False)


    # Fechas
    fecha_solicitud = Column

    # NUEVOS CAMPOS PARA SISTEMA COMPLETO DE APROBACIONES
    archivo_evidencia = Column
        String(255), nullable=True
    )  # Path del archivo adjunto
    tipo_archivo = Column(String(50), nullable=True)  # PDF, IMG, DOC, etc.
    tamaño_archivo = Column(Integer, nullable=True)  # Tamaño en bytes
    prioridad = Column
        String(20), default="NORMAL"
    )  # BAJA, NORMAL, ALTA, URGENTE
    fecha_limite = Column(Date, nullable=True)  # Fecha límite para respuesta
    notificado_admin = Column
    )  # Si ya se notificó al admin
    notificado_solicitante = Column
    )  # Si ya se notificó resultado
    bloqueado_temporalmente = Column
    )  # Si está bloqueado el registro

    visto_por_admin = Column(Boolean, default=False)
    tiempo_respuesta_horas = Column
    )  # Tiempo que tomó responder

    # Auditoría

    # Relaciones
    solicitante = relationship
    revisor = relationship


    def __repr__(self):
        return f"<Aprobacion {self.tipo_solicitud} - {self.estado}>"

    @property
    def esta_pendiente(self) -> bool:
        """Verifica si la aprobación está pendiente"""
        return self.estado == EstadoAprobacion.PENDIENTE.value

    @property
    def esta_aprobada(self) -> bool:
        """Verifica si la aprobación fue aprobada"""
        return self.estado == EstadoAprobacion.APROBADA.value

    @property
    def esta_rechazada(self) -> bool:
        """Verifica si la aprobación fue rechazada"""
        return self.estado == EstadoAprobacion.RECHAZADA.value


        """Marca la aprobación como aprobada"""
        self.estado = EstadoAprobacion.APROBADA.value
        self.revisor_id = revisor_id


        """Marca la aprobación como rechazada"""
        self.estado = EstadoAprobacion.RECHAZADA.value
        self.revisor_id = revisor_id
        self.bloqueado_temporalmente = False  # Desbloquear
        self._calcular_tiempo_respuesta()


    def cancelar(self):
        """Cancela la solicitud de aprobación"""
        self.estado = EstadoAprobacion.CANCELADA.value


    def marcar_como_visto(self, admin_id: int):
        """Marcar solicitud como vista por admin"""
        self.visto_por_admin = True


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
        return delta.days

    @property
    def requiere_atencion_urgente(self) -> bool:
        """Si requiere atención urgente"""
        return 

"""
""""""