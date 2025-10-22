# backend/app/schemas/notificacion.py
"""
Schemas de Pydantic para Notificación
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ============================================================================
# Schemas Base
# ============================================================================

class NotificacionBase(BaseModel):
    """Schema base para Notificación"""

    # Destinatarios
    user_id: Optional[int] = None
    cliente_id: Optional[int] = None
    destinatario_email: Optional[EmailStr] = None
    destinatario_telefono: Optional[str] = Field(None, max_length=20)
    destinatario_nombre: Optional[str] = Field(None, max_length=255)

    # Tipo y categoría
    tipo: str = Field(..., description="EMAIL, SMS, WHATSAPP, PUSH")
    categoria: str = Field(..., description="RECORDATORIO_PAGO, PRESTAMO_APROBADO, etc.")

    # Contenido
    asunto: Optional[str] = Field(None, max_length=255)
    mensaje: str

    # Datos adicionales (renombrado de metadata)
    extra_data: Optional[Dict[str, Any]] = None

    # Configuración
    prioridad: str = Field(default="NORMAL", description="BAJA, NORMAL, ALTA, URGENTE")
    programada_para: Optional[datetime] = None
    max_intentos: int = Field(default=3, ge=1, le=10)


class NotificacionCreate(NotificacionBase):
    """Schema para crear una notificación"""
    pass


class NotificacionUpdate(BaseModel):
    """Schema para actualizar una notificación"""

    estado: Optional[str] = None
    mensaje: Optional[str] = None
    asunto: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    programada_para: Optional[datetime] = None
    prioridad: Optional[str] = None


# ============================================================================
# Schemas de Respuesta
# ============================================================================

class NotificacionInDB(NotificacionBase):
    """Schema de notificación en base de datos"""

    id: int
    estado: str
    intentos: int

    # Fechas de envío
    enviada_en: Optional[datetime] = None
    leida_en: Optional[datetime] = None

    # Respuestas del servicio
    respuesta_servicio: Optional[str] = None
    error_mensaje: Optional[str] = None

    # Auditoría
    creado_en: datetime
    actualizado_en: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class NotificacionResponse(NotificacionInDB):
    """Schema de respuesta de notificación"""

    # Propiedades computadas
    esta_pendiente: bool = False
    fue_enviada: bool = False
    fallo: bool = False
    puede_reintentar: bool = False


# ============================================================================
# Schemas para acciones específicas
# ============================================================================

class NotificacionMarcarEnviada(BaseModel):
    """Schema para marcar notificación como enviada"""
    respuesta_servicio: Optional[str] = None


class NotificacionMarcarFallida(BaseModel):
    """Schema para marcar notificación como fallida"""
    error_mensaje: str


class NotificacionRecordatorioPago(BaseModel):
    """Schema para crear recordatorio de pago"""

    cliente_id: int
    tipo: str = Field(..., description="EMAIL, SMS, WHATSAPP")
    mensaje: str
    programada_para: Optional[datetime] = None
    extra_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Datos adicionales como monto, fecha_vencimiento, etc."
    )


# ============================================================================
# Schemas de Listado y Filtrado
# ============================================================================

class NotificacionFilter(BaseModel):
    """Filtros para listar notificaciones"""

    tipo: Optional[str] = None
    categoria: Optional[str] = None
    estado: Optional[str] = None
    prioridad: Optional[str] = None
    user_id: Optional[int] = None
    cliente_id: Optional[int] = None
    fecha_desde: Optional[datetime] = None
    fecha_hasta: Optional[datetime] = None


class NotificacionList(BaseModel):
    """Schema para lista de notificaciones"""

    total: int
    items: list[NotificacionResponse]
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Schemas de Estadísticas
# ============================================================================

class NotificacionStats(BaseModel):
    """Estadísticas de notificaciones"""

    total: int
    pendientes: int
    enviadas: int
    fallidas: int
    leidas: int

    por_tipo: Dict[str, int] = {}
    por_categoria: Dict[str, int] = {}
    por_prioridad: Dict[str, int] = {}
