"""
Notificaciones por pestañas: mismos símbolos que el antiguo módulo plano.

Se reexporta todo desde ``routes`` para que sigan funcionando
``@patch("app.api.v1.endpoints.notificaciones_tabs.…")`` y ``import … as nt`` / ``nt._…``.
"""

from __future__ import annotations

import sys

from . import routes as _routes

_pkg = sys.modules[__name__]
for _key, _val in vars(_routes).items():
    if _key.startswith("__"):
        continue
    setattr(_pkg, _key, _val)

__all__ = sorted(_k for _k in vars(_routes) if not _k.startswith("__"))
