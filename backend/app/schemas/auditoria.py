from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class AuditoriaBase(BaseModel):
    usuario_id: Optional[int] = None
    usuario_email: Optional[str] = None
    accion: str
    modulo: str
    tabla: str
    registro_id: Optional[int] = None
    descripcion: Optional[str] = None
    datos_anteriores: Optional[Dict[str, Any]] = None
    datos_nuevos: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    resultado: str = "EXITOSO"
    mensaje_error: Optional[str] = None


class AuditoriaCreate(AuditoriaBase):
    pass


class AuditoriaResponse(AuditoriaBase):
    id: int
    fecha: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditoriaListResponse(BaseModel):
    items: List[AuditoriaResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditoriaStatsResponse(BaseModel):
    total_acciones: int
    acciones_por_modulo: Dict[str, int]
    acciones_por_usuario: Dict[str, int]
    acciones_hoy: int
    acciones_esta_semana: int
    acciones_este_mes: int