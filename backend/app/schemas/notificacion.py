from datetime import date
# import Any, Dict, Optionalfrom pydantic import BaseModel, ConfigDict, EmailStr, Field#
# ============================================================================# Schemas Base#
# ============================================================================class NotificacionBase(BaseModel): """Schema"""
# destinatario_email: Optional[EmailStr] = None destinatario_telefono: Optional[str] = Field(None, max_length=20)
# destinatario_nombre: Optional[str] = Field(None, max_length=255) # Tipo y categoría tipo: str = Field
# description="EMAIL, SMS, WHATSAPP, PUSH") categoria: str = Field
# metadata) extra_data: Optional[Dict[str, Any]] = None # Configuración prioridad: str = Field
# ge=1, le=10)class NotificacionCreate(NotificacionBase): """Schema para crear una notificación"""class
# NotificacionUpdate(BaseModel): """Schema para actualizar una notificación""" estado: Optional[str] = None mensaje:
# Optional[str] = None asunto: Optional[str] = None extra_data: Optional[Dict[str, Any]] = None programada_para:
# ============================================================================# Schemas de Respuesta#
# ============================================================================class NotificacionInDB(NotificacionBase):
# model_config = ConfigDict(from_attributes=True)class NotificacionResponse(NotificacionInDB): """Schema de respuesta de
# notificación""" # Propiedades computadas esta_pendiente: bool = False fue_enviada: bool = False fallo: bool = False"""
# puede_reintentar: bool = False# ============================================================================# Schemas para
# acciones específicas# ============================================================================class
# NotificacionMarcarEnviada(BaseModel): """Schema para marcar notificación como enviada""" respuesta_servicio: Optional[str]
# = Noneclass NotificacionMarcarFallida(BaseModel): """Schema para marcar notificación como fallida""" error_mensaje:
# strclass NotificacionRecordatorioPago(BaseModel): """Schema para crear recordatorio de pago""" cliente_id: int tipo: str =
# ============================================================================# Schemas de Listado y Filtrado#
# para listar notificaciones""" tipo: Optional[str] = None categoria: Optional[str] = None estado: Optional[str] = None"""
# prioridad: Optional[str] = None user_id: Optional[int] = None cliente_id: Optional[int] = None fecha_desde:
# notificaciones""" total: int items: list[NotificacionResponse] page: int page_size: int total_pages: int#"""
# ============================================================================# Schemas de Estadísticas#
# ============================================================================class NotificacionStats(BaseModel):
# """Estadísticas de notificaciones""" total: int pendientes: int enviadas: int fallidas: int leidas: int por_tipo: Dict[str,
# int] = {} por_categoria: Dict[str, int] = {} por_prioridad: Dict[str, int] = {}

""""""