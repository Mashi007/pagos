# backend/app/core/__init__.py
"""
Módulo core - Lógica de negocio central del sistema.
"""

# ⚠️ IMPORTANTE: Solo importar lo que EXISTE en constants.py
# Si constants.py no tiene MetodoPago, no lo incluyas aquí

try:
    from app.core.constants import (
        UserRole,
        EstadoPrestamo,
        EstadoPago,
        TipoPago,
        # MetodoPago,  # ← COMENTADO hasta verificar que existe
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
        # "MetodoPago",  # ← COMENTADO
        "EstadoNotificacion",
        "TipoNotificacion",
        "EstadoAprobacion",
        "TipoDocumento",
        "FrecuenciaPago",
        "TipoInteres",
        "EstadoConciliacion",
    ]

except ImportError as e:
    # Si falla la importación, al menos el módulo se carga sin romper
    import warnings
    warnings.warn(f"Error al importar constantes desde core: {e}")
    __all__ = []
