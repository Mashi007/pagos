"""
Schemas para KPIs y estadísticas de usuarios.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class UsuarioInfo(BaseModel):
    """Información básica de un usuario."""
    email: str
    fecha: Optional[str] = None


class RoleStats(BaseModel):
    """Estadísticas por rol."""
    admin: int
    manager: int
    operator: int
    viewer: int


class KpiUsuariosResponse(BaseModel):
    """Respuesta con KPIs y estadísticas de usuarios."""
    total_usuarios: int
    usuarios_activos: int
    usuarios_inactivos: int
    porcentaje_activos: float
    por_rol: RoleStats
    usuarios_ultimo_mes: int
    usuarios_ultima_semana: int
    ultimo_usuario_creado: UsuarioInfo
    ultimo_login: UsuarioInfo
    
    class Config:
        schema_extra = {
            "example": {
                "total_usuarios": 5,
                "usuarios_activos": 5,
                "usuarios_inactivos": 0,
                "porcentaje_activos": 100.0,
                "por_rol": {
                    "admin": 1,
                    "manager": 1,
                    "operator": 2,
                    "viewer": 1
                },
                "usuarios_ultimo_mes": 3,
                "usuarios_ultima_semana": 1,
                "ultimo_usuario_creado": {
                    "email": "usuario@empresa.com",
                    "fecha": "2026-04-01T10:30:00"
                },
                "ultimo_login": {
                    "email": "admin@sistema.com",
                    "fecha": "2026-04-01T15:45:00"
                }
            }
        }
