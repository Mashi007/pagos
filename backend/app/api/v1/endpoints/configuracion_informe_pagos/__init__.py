"""Configuración informe de pagos / Google OAuth: router autenticado y callback público."""

from .routes import router, router_google_callback

__all__ = ["router", "router_google_callback"]
