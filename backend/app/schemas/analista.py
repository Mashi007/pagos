from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class AnalistaBase(BaseModel):
    nombre: str
    activo: bool = True

    @field_validator("nombre")
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("El nombre no puede estar vacío")
        return v.strip()


class AnalistaCreate(AnalistaBase):
    pass


class AnalistaUpdate(BaseModel):
    nombre: Optional[str] = None
    activo: Optional[bool] = None

    @field_validator("nombre")
    @classmethod
    def name_must_not_be_empty(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError("El nombre no puede estar vacío")
        return v.strip() if v else v


class AnalistaResponse(AnalistaBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class AnalistaListResponse(BaseModel):
    items: List[AnalistaResponse]
    total: int
    page: int
    size: int
    pages: int
