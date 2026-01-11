"""
Schemas para Notificaciones
FASE 2: Sincronizado con modelo ORM
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ============================================================================
# Schemas Base
# ============================================================================
class NotificacionBase(BaseModel):
    """Schema base para notificaciones"""

    # Destinatario
    cliente_id: Optional[int] = Field(None, description="ID del cliente destinatario")
    user_id: Optional[int] = Field(None, description="ID del usuario destinatario")
    destinatario_email: Optional[EmailStr] = Field(None, description="Email del destinatario")
    destinatario_telefono: Optional[str] = Field(None, max_length=20, description="Teléfono del destinatario")
    destinatario_nombre: Optional[str] = Field(None, max_length=255, description="Nombre del destinatario")

    # Tipo y categoría
    tipo: str = Field(..., description="Tipo de notificación: EMAIL, SMS, WHATSAPP, PUSH")
    categoria: str = Field(default="GENERAL", description="Categoría de la notificación")
    asunto: Optional[str] = Field(None, max_length=255, description="Asunto de la notificación")
    mensaje: str = Field(..., description="Mensaje de la notificación")

    # Estado y control
    estado: str = Field(default="PENDIENTE", description="Estado: PENDIENTE, ENVIADA, FALLIDA, CANCELADA")
    prioridad: str = Field(default="MEDIA", description="Prioridad: BAJA, MEDIA, ALTA")
    programada_para: Optional[datetime] = Field(None, description="Fecha/hora programada para envío")

    # Metadata
    extra_data: Optional[Dict[str, Any]] = Field(None, description="Datos adicionales en formato JSON")


class NotificacionCreate(NotificacionBase):
    """Schema para crear una notificación"""

    pass


class NotificacionUpdate(BaseModel):
    """Schema para actualizar una notificación"""

    estado: Optional[str] = Field(None, description="Estado de la notificación")
    mensaje: Optional[str] = Field(None, description="Mensaje de la notificación")
    asunto: Optional[str] = Field(None, max_length=255, description="Asunto de la notificación")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="Datos adicionales")
    programada_para: Optional[datetime] = Field(None, description="Fecha/hora programada")
    prioridad: Optional[str] = Field(None, description="Prioridad de la notificación")


# ============================================================================
# Schemas de Respuesta
# ============================================================================
class NotificacionResponse(NotificacionBase):
    """Schema de respuesta de notificación - FASE 2: Sincronizado con modelo ORM"""

    id: int
    enviada_en: Optional[datetime] = Field(None, description="Fecha/hora en que fue enviada")
    leida_en: Optional[datetime] = Field(None, description="Fecha/hora en que fue leída")
    intentos: Optional[int] = Field(None, description="Número de intentos de envío")
    max_intentos: Optional[int] = Field(None, description="Número máximo de intentos permitidos")
    respuesta_servicio: Optional[str] = Field(None, description="Respuesta del servicio de envío")
    error_mensaje: Optional[str] = Field(None, description="Mensaje de error si falló el envío")
    creado_en: Optional[datetime] = Field(None, description="Fecha de creación del registro")
    actualizado_en: Optional[datetime] = Field(None, description="Fecha de última actualización")

    # Propiedades computadas (basadas en estado y timestamps)
    esta_pendiente: bool = Field(default=False, description="Indica si está pendiente de envío")
    fue_enviada: bool = Field(default=False, description="Indica si fue enviada exitosamente")
    fallo: bool = Field(default=False, description="Indica si falló el envío")
    puede_reintentar: bool = Field(default=False, description="Indica si se puede reintentar el envío")

    model_config = ConfigDict(from_attributes=True)

    def model_post_init(self, __context: Any) -> None:
        """Calcula propiedades computadas después de inicializar"""
        # Calcular propiedades basadas en estado
        self.esta_pendiente = self.estado == "PENDIENTE"
        self.fue_enviada = self.estado == "ENVIADA"
        self.fallo = self.estado == "FALLIDA"
        # Puede reintentar si falló y no excedió intentos máximos
        if self.fallo and self.max_intentos:
            self.puede_reintentar = (self.intentos or 0) < self.max_intentos
        else:
            self.puede_reintentar = False


# ============================================================================
# Schemas para acciones específicas
# ============================================================================
class NotificacionMarcarEnviada(BaseModel):
    """Schema para marcar notificación como enviada"""

    respuesta_servicio: Optional[str] = Field(None, description="Respuesta del servicio de envío")


class NotificacionMarcarFallida(BaseModel):
    """Schema para marcar notificación como fallida"""

    error_mensaje: str = Field(..., description="Mensaje de error")


class NotificacionRecordatorioPago(BaseModel):
    """Schema para crear recordatorio de pago"""

    cliente_id: int = Field(..., description="ID del cliente")
    tipo: str = Field(..., description="Tipo de notificación: EMAIL, SMS, WHATSAPP")
    mensaje: str = Field(..., description="Mensaje del recordatorio")
    programada_para: Optional[datetime] = Field(None, description="Fecha/hora programada")


# ============================================================================
# Schemas de Listado y Filtrado
# ============================================================================
class NotificacionFilters(BaseModel):
    """Schema para filtrar notificaciones"""

    tipo: Optional[str] = Field(None, description="Filtrar por tipo")
    categoria: Optional[str] = Field(None, description="Filtrar por categoría")
    estado: Optional[str] = Field(None, description="Filtrar por estado")
    prioridad: Optional[str] = Field(None, description="Filtrar por prioridad")
    user_id: Optional[int] = Field(None, description="Filtrar por usuario")
    cliente_id: Optional[int] = Field(None, description="Filtrar por cliente")
    fecha_desde: Optional[datetime] = Field(None, description="Fecha desde")
    fecha_hasta: Optional[datetime] = Field(None, description="Fecha hasta")


class NotificacionListResponse(BaseModel):
    """Schema para listar notificaciones"""

    total: int = Field(..., description="Total de notificaciones")
    items: List[NotificacionResponse] = Field(..., description="Lista de notificaciones")
    page: int = Field(..., description="Página actual")
    page_size: int = Field(..., description="Tamaño de página")
    total_pages: int = Field(..., description="Total de páginas")


# ============================================================================
# Schemas de Estadísticas
# ============================================================================
class NotificacionStats(BaseModel):
    """Estadísticas de notificaciones"""

    total: int = Field(..., description="Total de notificaciones")
    pendientes: int = Field(..., description="Notificaciones pendientes")
    enviadas: int = Field(..., description="Notificaciones enviadas")
    fallidas: int = Field(..., description="Notificaciones fallidas")
    leidas: int = Field(..., description="Notificaciones leídas")
    por_tipo: Dict[str, int] = Field(default_factory=dict, description="Conteo por tipo")
    por_categoria: Dict[str, int] = Field(default_factory=dict, description="Conteo por categoría")
    por_prioridad: Dict[str, int] = Field(default_factory=dict, description="Conteo por prioridad")
