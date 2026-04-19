"""Validación de configuración email / envíos (sin router; helpers para guardado)."""

from .routes import (
    validar_config_email_para_guardar,
    validar_notificaciones_envios_payload,
)

__all__ = [
    "validar_config_email_para_guardar",
    "validar_notificaciones_envios_payload",
]
