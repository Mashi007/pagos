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
    user: Dict[str, Any]  # Información básica del usuario


class TokenPayload(BaseModel):
    """Schema para el payload del token"""
    sub: Optional[str] = None
    exp: Optional[int] = None
    type: Optional[str] = None


class LoginRequest(BaseModel):
    """Schema para request de login"""
    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field
    )

    model_config = ConfigDict
    )


class RefreshTokenRequest(BaseModel):
    """Schema para refresh token"""
    refresh_token: str = Field(..., description="Refresh token")


class ChangePasswordRequest(BaseModel):
    """Schema para cambio de contraseña"""
    current_password: str = Field
    )
    new_password: str = Field
    )
    confirm_password: str = Field
    )

    model_config = ConfigDict
    )


class PasswordResetRequest(BaseModel):
    """Schema para solicitud de reset de contraseña"""
    email: EmailStr = Field(..., description="Email del usuario")


class PasswordResetConfirm(BaseModel):
    """Schema para confirmar reset de contraseña"""
    token: str = Field(..., description="Token de reset")
    new_password: str = Field
    )
    confirm_password: str = Field
    )


class LogoutRequest(BaseModel):
    """Schema para logout (opcional, por si se implementa blacklist)"""
    refresh_token: Optional[str] = None
