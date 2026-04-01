"""
Schemas para carga masiva de usuarios (bulk import).
"""
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, validator


class UserBulkItem(BaseModel):
    """Fila individual de usuarios para importación masiva."""
    email: EmailStr
    cedula: str = Field(..., min_length=1, max_length=50, description="Cédula única")
    nombre: str = Field(..., min_length=1, max_length=255, description="Nombre completo")
    cargo: Optional[str] = Field(None, max_length=100)
    rol: str = Field("viewer", description="admin|manager|operator|viewer")
    password: str = Field(..., min_length=6, max_length=100)
    
    @validator('rol')
    def validate_rol(cls, v):
        valid_roles = {'admin', 'manager', 'operator', 'viewer'}
        if v not in valid_roles:
            raise ValueError(f"Rol debe ser uno de: {', '.join(valid_roles)}")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "email": "usuario@example.com",
                "cedula": "12345678-9",
                "nombre": "Juan Pérez García",
                "cargo": "Operario",
                "rol": "viewer",
                "password": "SeguraPassword123"
            }
        }


class UserBulkImportRequest(BaseModel):
    """Solicitud de importación masiva de usuarios."""
    usuarios: List[UserBulkItem] = Field(..., min_items=1, max_items=1000, description="Máximo 1000 usuarios")


class BulkImportResult(BaseModel):
    """Resultado de una fila procesada."""
    email: str
    status: str  # 'success', 'error'
    mensaje: str
    usuario_id: Optional[int] = None


class UserBulkImportResponse(BaseModel):
    """Respuesta de importación masiva."""
    total_solicitados: int
    total_exitosos: int
    total_errores: int
    resultados: List[BulkImportResult]
    
    class Config:
        schema_extra = {
            "example": {
                "total_solicitados": 3,
                "total_exitosos": 2,
                "total_errores": 1,
                "resultados": [
                    {
                        "email": "usuario1@example.com",
                        "status": "success",
                        "mensaje": "Usuario creado exitosamente",
                        "usuario_id": 10
                    },
                    {
                        "email": "usuario2@example.com",
                        "status": "error",
                        "mensaje": "Email duplicado: usuario2@example.com ya existe"
                    }
                ]
            }
        }
