from datetime import date

# backend/app/schemas/user.py
"""
Schemas de usuario simplificado.
Solo 2 roles: ADMIN (acceso completo) y USER (acceso limitado)
Compatible con Pydantic v2.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# ============================================
# SCHEMAS BASE
# ============================================


class UserBase(BaseModel):
    email: EmailStr
    nombre: str = Field(..., min_length=1, max_length=100)
    apellido: str = Field(..., min_length=1, max_length=100)
    cargo: Optional[str] = Field(None, max_length=100)
    is_admin: bool = Field(default=False)  # Cambio clave: rol → is_admin
    is_active: bool = Field(default=True)


class UserCreate(UserBase):
    """Schema para crear usuario."""

    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema para actualizar usuario."""

    email: Optional[EmailStr] = None
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    apellido: Optional[str] = Field(None, min_length=1, max_length=100)
    cargo: Optional[str] = Field(None, max_length=100)
    is_admin: Optional[bool] = None  # Cambio clave: rol → is_admin
    is_active: Optional[bool] = None
    password: Optional[str] = Field(
        None,
        min_length=8,
        description="Nueva contraseña (opcional, solo se valida si se provee)",
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        """Validar contraseña solo si se proporciona un valor no vacío"""
        if v is not None and v.strip() != "":
            if len(v) < 8:
                raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v


# ============================================
# SCHEMAS DE RESPUESTA
# ============================================


class UserResponse(UserBase):
    """Schema de respuesta de usuario."""

    id: int

    model_config = ConfigDict(from_attributes=True)

    @property
    def full_name(self) -> str:
        """Nombre completo del usuario."""
        return f"{self.nombre} {self.apellido}"


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int


# ============================================
# SCHEMAS DE AUTENTICACIÓN
# ============================================


class LoginRequest(BaseModel):
    """Schema para login."""

    email: EmailStr
    password: str
    remember_me: bool = Field(default=False)


class LoginResponse(BaseModel):
    """Schema de respuesta de login."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserMeResponse(UserResponse):
    """Schema para respuesta de usuario actual (/me endpoint)."""

    permissions: list[str] = Field(default_factory=list)

    @property
    def rol(self) -> str:
        """Propiedad para compatibilidad hacia atrás."""
        return "ADMIN" if self.is_admin else "USER"


class TokenPayload(BaseModel):
    """Schema del payload del token JWT."""

    sub: str  # email del usuario
    is_admin: bool  # Cambio clave: rol → is_admin
    exp: int
    iat: int
