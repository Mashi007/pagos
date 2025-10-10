# backend/app/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class Token(BaseModel):
    """Respuesta de token JWT"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30 minutos en segundos


class TokenData(BaseModel):
    """Datos extraídos del token"""
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[str] = None


class LoginRequest(BaseModel):
    """Request para login"""
    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., min_length=6, description="Contraseña del usuario")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "admin@example.com",
                "password": "admin123"
            }
        }


class RefreshTokenRequest(BaseModel):
    """Request para refresh token"""
    refresh_token: str = Field(..., description="Refresh token válido")


class ChangePasswordRequest(BaseModel):
    """Request para cambiar contraseña"""
    current_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    """Respuesta con datos del usuario"""
    id: int
    email: str
    nombre: str
    apellido: str
    rol: str
    activo: bool
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True
