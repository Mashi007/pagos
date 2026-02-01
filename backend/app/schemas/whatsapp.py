"""
Schemas para validación de mensajes de WhatsApp (Meta API)
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class WhatsAppContact(BaseModel):
    """Información de contacto de WhatsApp"""
    profile: Optional[dict] = None
    wa_id: str = Field(..., description="WhatsApp ID del contacto")


class WhatsAppText(BaseModel):
    """Contenido de mensaje de texto"""
    body: str = Field(..., description="Cuerpo del mensaje")


class WhatsAppImage(BaseModel):
    """Contenido de mensaje de imagen (Meta API)"""
    id: str = Field(..., description="ID del media en Meta")
    sha256: Optional[str] = None
    mime_type: Optional[str] = None
    caption: Optional[str] = None


class WhatsAppMessage(BaseModel):
    """Mensaje recibido de WhatsApp"""
    from_: str = Field(..., alias="from", description="Número de teléfono remitente")
    id: str = Field(..., description="ID único del mensaje")
    timestamp: str = Field(..., description="Timestamp del mensaje")
    type: str = Field(..., description="Tipo de mensaje (text, image, etc.)")
    text: Optional[WhatsAppText] = None
    image: Optional[WhatsAppImage] = None

    class Config:
        populate_by_name = True


class WhatsAppValue(BaseModel):
    """Valor del webhook de WhatsApp"""
    messaging_product: str = Field(..., description="Producto de mensajería")
    metadata: dict = Field(..., description="Metadatos del mensaje")
    contacts: Optional[List[WhatsAppContact]] = None
    messages: Optional[List[WhatsAppMessage]] = None
    statuses: Optional[List[dict]] = None


class WhatsAppEntry(BaseModel):
    """Entrada del webhook de WhatsApp"""
    id: str = Field(..., description="ID de la entrada")
    changes: List[dict] = Field(..., description="Cambios recibidos")


class WhatsAppWebhookPayload(BaseModel):
    """Payload completo del webhook de WhatsApp"""
    object: str = Field(..., description="Tipo de objeto (whatsapp_business_account)")
    entry: List[WhatsAppEntry] = Field(..., description="Entradas del webhook")


class WhatsAppWebhookChallenge(BaseModel):
    """Modelo para verificación del webhook (challenge de Meta)"""
    hub_mode: str = Field(..., alias="hub.mode")
    hub_challenge: str = Field(..., alias="hub.challenge")
    hub_verify_token: str = Field(..., alias="hub.verify_token")
    
    class Config:
        populate_by_name = True


class WhatsAppResponse(BaseModel):
    """Respuesta estándar para webhook"""
    success: bool = True
    message: str = "Mensaje procesado correctamente"
    message_id: Optional[str] = None
