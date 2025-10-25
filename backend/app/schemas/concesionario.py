from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


from datetime import date
class ConcesionarioBase(BaseModel):
    nombre: str = Field
    activo: bool = Field(True, description="Estado activo del concesionario")


class ConcesionarioCreate(ConcesionarioBase):
    pass


class ConcesionarioUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=255)
    activo: Optional[bool] = None


class ConcesionarioResponse(ConcesionarioBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ConcesionarioListResponse(BaseModel):
    items: list[ConcesionarioResponse]
    total: int
    page: int
    size: int
    pages: int
