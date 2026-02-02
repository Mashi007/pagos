"""
Schemas para API de usuarios (crear, actualizar, respuesta).
UserResponse se reutiliza desde app.schemas.auth.
"""
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    nombre: str = Field(..., min_length=1, max_length=100)
    apellido: str = Field("", max_length=100)
    cargo: Optional[str] = Field(None, max_length=100)
    is_admin: bool = False
    is_active: bool = True
    password: str = Field(..., min_length=6, max_length=100)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    apellido: Optional[str] = Field(None, max_length=100)
    cargo: Optional[str] = Field(None, max_length=100)
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6, max_length=100)
