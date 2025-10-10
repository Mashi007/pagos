# backend/app/api/v1/__init__.py
"""
API v1 - Endpoints del sistema de Préstamos y Cobranza

Módulos disponibles:
- health: Health check y status
- auth: Autenticación (login, logout, refresh)
- users: CRUD de usuarios
- clientes: CRUD de clientes
- prestamos: CRUD de préstamos
- pagos: CRUD de pagos
- amortizacion: Tablas de amortización
"""

from app.api.v1.endpoints import (
    health,
    auth,
    users,
    clientes,
    prestamos,
    pagos,
    amortizacion,
)

__all__ = [
    "health",
    "auth",
    "users",
    "clientes",
    "prestamos",
    "pagos",
    "amortizacion",
]
