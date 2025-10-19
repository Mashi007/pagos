# backend/app/api/v1/endpoints/__init__.py
"""
Endpoints de la API v1
"""

# Importar todos los routers disponibles
from . import (
    health,
    auth,
    users,
    clientes,
    prestamos,
    pagos,
    conciliacion_bancaria,
    amortizacion,
    conciliacion,
    reportes,
    kpis,
    notificaciones,
    aprobaciones,
    auditoria,
    configuracion,
    validadores,
    dashboard,
    inteligencia_artificial,
    modelos_vehiculos,
    concesionarios,
    analistas,
    carga_masiva,
    solicitudes,
    scheduler_notificaciones,
    notificaciones_multicanal,
    plantilla_clientes
)

__all__ = [
    "health",
    "auth", 
    "users",
    "clientes",
    "prestamos",
    "pagos",
    "conciliacion_bancaria",
    "amortizacion",
    "conciliacion",
    "reportes",
    "kpis",
    "notificaciones",
    "aprobaciones",
    "auditoria",
    "configuracion",
    "validadores",
    "dashboard",
    "inteligencia_artificial",
    "modelos_vehiculos",
    "concesionarios",
    "analistas",
    "carga_masiva",
    "solicitudes",
    "scheduler_notificaciones",
    "notificaciones_multicanal",
    "plantilla_clientes"
]