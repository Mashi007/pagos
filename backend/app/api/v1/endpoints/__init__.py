# backend/app/api/v1/endpoints/__init__.py
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

# ✅ CORRECTO: Importar routers desde archivos individuales
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.clientes import router as clientes_router
from app.api.v1.endpoints.prestamos import router as prestamos_router
from app.api.v1.endpoints.pagos import router as pagos_router
from app.api.v1.endpoints.amortizacion import router as amortizacion_router

__all__ = [
    "health_router",
    "auth_router",
    "users_router",
    "clientes_router",
    "prestamos_router",
    "pagos_router",
    "amortizacion_router",
]
