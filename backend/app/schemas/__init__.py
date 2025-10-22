# backend/app/schemas/__init__.py
"""
Schemas centralizados para la API.
Incluye todos los modelos de datos para validación y serialización.
Schemas organizados por módulo:
- Cliente: Gestión de clientes
- Préstamo: Gestión de préstamos
- Pago: Gestión de pagos
- User: Gestión de usuarios y autenticación (SIMPLIFICADO - solo is_admin boolean)
- Conciliación: Conciliación bancaria
- KPIs: Métricas e indicadores
"""
# ============================================
# SCHEMAS DE CLIENTE
# ============================================
from app.schemas.cliente import (
    ClienteCreate,
    ClienteUpdate,
    ClienteResponse,
)
# ============================================
# SCHEMAS DE PRÉSTAMO
# ============================================
from app.schemas.prestamo import (
    PrestamoCreate,
    PrestamoUpdate,
    PrestamoResponse,
)
# ============================================
# SCHEMAS DE PAGO
# ============================================
from app.schemas.pago import (
    PagoCreate,
    PagoUpdate,
    PagoResponse,
    PagoListResponse,
    ConciliacionCreate,
    ConciliacionResponse,
    KPIsPagos,
    ResumenCliente,
)
# ============================================
# SCHEMAS DE USUARIO Y AUTENTICACIÓN
# ============================================
# NOTA: UserRole eliminado - ahora se usa is_admin boolean
# Los schemas de usuario están en app.schemas.user pero NO se importan aquí
# para evitar conflictos con la migración de roles
# ============================================
# SCHEMAS DE CONCILIACIÓN BANCARIA
# ============================================
from app.schemas.conciliacion import (
    EstadoConciliacion,
    TipoMatch,
    MovimientoBancario,
    MovimientoBancarioResponse,
    ConciliacionCreate,
    ConciliacionMatch,
    ResultadoConciliacion,
    ConciliacionResponse,
    ConfirmacionConciliacion,
    ConfirmacionResponse,
    ReporteConciliacionMensual,
    FiltroConciliacion,
    PagoPendienteConciliacion,
    ExtractoBancarioUpload,
    ValidacionExtracto,
    EstadisticasConciliacion,
)
# ============================================
# SCHEMAS DE KPIs
# ============================================
# ACTUALIZADO: Importaciones corregidas para coincidir con kpis.py
from app.schemas.kpis import (
    KPIBase,
    KPICreate,
    KPIUpdate,
    KPIResponse,
    KPIValorBase,
    KPIValorCreate,
    KPIValorUpdate,
    KPIValorResponse,
    KPIConValores,
    KPIEstadisticas,
    DashboardKPIs,
)
# ============================================
# EXPORTS PÚBLICOS
# ============================================
__all__ = [
    # ========== CLIENTE ==========
    "ClienteCreate",
    "ClienteUpdate",
    "ClienteResponse",

    # ========== PRÉSTAMO ==========
    "PrestamoCreate",
    "PrestamoUpdate",
    "PrestamoResponse",

    # ========== PAGO ==========
    "PagoCreate",
    "PagoUpdate",
    "PagoResponse",
    "PagoListResponse",
    "ConciliacionCreate",
    "ConciliacionResponse",
    "KPIsPagos",
    "ResumenCliente",

    # ========== USUARIO ==========
    # NOTA: UserRole eliminado - ahora se usa is_admin boolean
    # Los schemas de usuario están disponibles directamente desde app.schemas.user

    # ========== CONCILIACIÓN ==========
    "EstadoConciliacion",
    "TipoMatch",
    "MovimientoBancario",
    "MovimientoBancarioResponse",
    "ConciliacionCreate",
    "ConciliacionMatch",
    "ResultadoConciliacion",
    "ConciliacionResponse",
    "ConfirmacionConciliacion",
    "ConfirmacionResponse",
    "ReporteConciliacionMensual",
    "FiltroConciliacion",
    "PagoPendienteConciliacion",
    "ExtractoBancarioUpload",
    "ValidacionExtracto",
    "EstadisticasConciliacion",

    # ========== KPIs (ACTUALIZADO) ==========
    "KPIBase",
    "KPICreate",
    "KPIUpdate",
    "KPIResponse",
    "KPIValorBase",
    "KPIValorCreate",
    "KPIValorUpdate",
    "KPIValorResponse",
    "KPIConValores",
    "KPIEstadisticas",
    "DashboardKPIs",
]
# ============================================
# INFORMACIÓN DEL MÓDULO
# ============================================
__version__ = "1.0.0"
__author__ = "Sistema de Gestión de Préstamos"
__description__ = "Schemas Pydantic v2 para validación de API - SIMPLIFICADO (sin UserRole)"
