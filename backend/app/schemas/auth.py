# backend/app/schemas/auth.py
"""Schemas de autenticación: Login, Token, Register"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Constantes de validación
MIN_PASSWORD_LENGTH = 8


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
    expires_in: int  # Tiempo de expiración en segundos
    user: Dict[str, Any]  # Información básica del usuario


class TokenPayload(BaseModel):
    """Schema para el payload del token"""

    sub: Optional[str] = None
    exp: Optional[int] = None
    type: Optional[str] = None


class TokenResponse(BaseModel):
    """Schema para respuesta de token"""

    access_token: str = Field(..., description="Token de acceso")
    refresh_token: str = Field(..., description="Token de refresh")
    token_type: str = Field(default="bearer", description="Tipo de token")
    expires_in: int = Field(..., description="Tiempo de expiración en segundos")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "token_type": "bearer",
                "expires_in": 1800,
            }
        }
    )


class LoginRequest(BaseModel):
    """Schema para request de login"""

    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., min_length=6, description="Contraseña del usuario")

    model_config = ConfigDict(json_schema_extra={"example": {"email": "usuario@ejemplo.com", "password": "contraseña123"}})


class RefreshTokenRequest(BaseModel):
    """Schema para refresh token"""

    refresh_token: str = Field(..., description="Refresh token")


class ChangePasswordRequest(BaseModel):
    """Schema para cambio de contraseña"""

    current_password: str = Field(..., description="Contraseña actual")
    new_password: str = Field(..., min_length=6, description="Nueva contraseña")
    confirm_password: str = Field(..., description="Confirmar nueva contraseña")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_password": "contraseña_actual",
                "new_password": "nueva_contraseña123",
                "confirm_password": "nueva_contraseña123",
            }
        }
    )


class PasswordResetRequest(BaseModel):
    """Schema para solicitud de reset de contraseña"""

    email: EmailStr = Field(..., description="Email del usuario")


class PasswordResetConfirm(BaseModel):
    """Schema para confirmar reset de contraseña"""

    token: str = Field(..., description="Token de reset")
    new_password: str = Field(..., min_length=6, description="Nueva contraseña")
    confirm_password: str = Field(..., description="Confirmar nueva contraseña")


class LogoutRequest(BaseModel):
    """Schema para logout (opcional, por si se implementa blacklist)"""

    refresh_token: Optional[str] = None
