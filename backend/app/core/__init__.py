# app/core/__init__.py
"""
Módulo core - Lógica de negocio central del sistema.
"""

# Importar las constantes principales para facilitar el acceso
from app.core.constants import (
    UserRole,
    EstadoPrestamo,
    EstadoPago,
    TipoPago,
    MetodoPago,
    EstadoNotificacion,
    TipoNotificacion,
    EstadoAprobacion,
    TipoDocumento,
    FrecuenciaPago,
    TipoInteres,
    EstadoConciliacion
)

# Exportar todo lo que debe estar disponible cuando se importe core
__all__ = [
    "UserRole",
    "EstadoPrestamo", 
    "EstadoPago",
    "TipoPago",
    "MetodoPago",
    "EstadoNotificacion",
    "TipoNotificacion",
    "EstadoAprobacion",
    "TipoDocumento",
    "FrecuenciaPago",
    "TipoInteres",
    "EstadoConciliacion",
]
