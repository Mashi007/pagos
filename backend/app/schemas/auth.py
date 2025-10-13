# backend/app/schemas/auth.py
"""
Schemas de autenticación: Login, Token, Register
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional


class Token(BaseModel):
    """Schema para respuesta de token"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    """Schema para respuesta de login (tokens + usuario)"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict  # Información básica del usuario


class TokenPayload(BaseModel):
    """Schema para el payload del token"""
    sub: Optional[str] = None
    exp: Optional[int] = None
    type: Optional[str] = None


class LoginRequest(BaseModel):
    """Schema para request de login"""
    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., min_length=1, description="Contraseña del usuario")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "admin@sistema.com",
                "password": "Admin123!"
            }
        }
    )


class RefreshTokenRequest(BaseModel):
    """Schema para refresh token"""
    refresh_token: str = Field(..., description="Refresh token")


class ChangePasswordRequest(BaseModel):
    """Schema para cambio de contraseña"""
    current_password: str = Field(..., min_length=8, description="Contraseña actual")
    new_password: str = Field(..., min_length=8, description="Nueva contraseña")
    confirm_password: str = Field(..., min_length=8, description="Confirmar nueva contraseña")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_password": "OldPassword123!",
                "new_password": "NewPassword123!",
                "confirm_password": "NewPassword123!"
            }
        }
    )


class PasswordResetRequest(BaseModel):
    """Schema para solicitud de reset de contraseña"""
    email: EmailStr = Field(..., description="Email del usuario")


class PasswordResetConfirm(BaseModel):
    """Schema para confirmar reset de contraseña"""
    token: str = Field(..., description="Token de reset")
    new_password: str = Field(..., min_length=8, description="Nueva contraseña")
    confirm_password: str = Field(..., min_length=8, description="Confirmar nueva contraseña")


class LogoutRequest(BaseModel):
    """Schema para logout (opcional, por si se implementa blacklist de tokens)"""
    refresh_token: Optional[str] = None
