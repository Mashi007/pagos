"""Validadores reutilizados por otros endpoints y servicios."""

from .routes import (
    router,
    validate_cedula,
    validate_email,
    validate_fecha,
    validate_phone,
)

__all__ = [
    "router",
    "validate_cedula",
    "validate_email",
    "validate_fecha",
    "validate_phone",
]
