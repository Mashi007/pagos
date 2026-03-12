"""
Schemas Pydantic para CRM Campañas (envío por lotes a correos de clientes).
HTML, To/CC, adjunto (1 archivo jpg/png/pdf), destinatarios: todos o seleccionados.
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class CampanaCrmBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    asunto: str = Field(..., min_length=1, max_length=500)
    cuerpo_texto: str = Field(default="", description="Versión texto plano (puede estar vacío si solo hay HTML)")
    cuerpo_html: Optional[str] = Field(None, description="Cuerpo en HTML para envío")
    batch_size: int = Field(default=25, ge=5, le=100, description="Correos por lote")
    delay_entre_batches_seg: int = Field(default=3, ge=1, le=60, description="Segundos entre lotes")
    cc_emails: Optional[List[str]] = Field(None, description="Emails en copia (CC)")
    destinatarios_cliente_ids: Optional[List[int]] = Field(
        None,
        description="Si se envía: solo a estos clientes. Si null/vacío: a todos los de tabla clientes",
    )


class CampanaCrmCreate(CampanaCrmBase):
    pass


class CampanaCrmUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=200)
    asunto: Optional[str] = Field(None, min_length=1, max_length=500)
    cuerpo_texto: Optional[str] = None
    cuerpo_html: Optional[str] = None
    batch_size: Optional[int] = Field(None, ge=5, le=100)
    delay_entre_batches_seg: Optional[int] = Field(None, ge=1, le=60)
    cc_emails: Optional[List[str]] = None
    destinatarios_cliente_ids: Optional[List[int]] = None


class CampanaCrmResponse(BaseModel):
    id: int
    nombre: str
    asunto: str
    cuerpo_texto: str
    cuerpo_html: Optional[str] = None
    estado: str
    total_destinatarios: int
    enviados: int
    fallidos: int
    batch_size: int
    delay_entre_batches_seg: int
    cc_emails: Optional[str] = None
    tiene_adjunto: bool = False
    destinatarios_modo: str = "todos"
    fecha_creacion: Optional[datetime] = None
    fecha_actualizacion: Optional[datetime] = None
    fecha_envio_inicio: Optional[datetime] = None
    fecha_envio_fin: Optional[datetime] = None
    usuario_creacion: Optional[str] = None

    class Config:
        from_attributes = True


class DestinatarioPreview(BaseModel):
    email: str
    cliente_id: Optional[int] = None
    nombres: Optional[str] = None


class CampanaDestinatarioResponse(BaseModel):
    id: int
    campana_id: int
    cliente_id: Optional[int] = None
    email: str
    estado: str
    fecha_envio: Optional[datetime] = None
    error_mensaje: Optional[str] = None

    class Config:
        from_attributes = True
