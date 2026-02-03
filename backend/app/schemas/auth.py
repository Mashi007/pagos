"""
Schemas para autenticación
"""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Mínimo 6 caracteres")
    remember: Optional[bool] = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None


class UserResponse(BaseModel):
    id: int
    email: str
    nombre: str
    apellido: str
    cargo: Optional[str] = None
    rol: str  # 'administrador' | 'operativo'
    is_active: bool
    created_at: str
    updated_at: Optional[str] = None
    last_login: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str


class AdminResetPasswordRequest(BaseModel):
    """Solo uso interno: sincroniza contraseña del usuario en BD con ADMIN_PASSWORD."""
    email: EmailStr
