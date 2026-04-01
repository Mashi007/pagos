"""
Normalización de roles a valores RBAC canónicos (admin, manager, operator, viewer).

Sirve para respuestas API y comprobaciones de permisos cuando en BD o tokens
legados aparecen variantes en español o mayúsculas.
"""
from __future__ import annotations

from typing import Optional

_CANONICAL = frozenset({"admin", "manager", "operator", "viewer"})


def canonical_rol(rol: Optional[str]) -> str:
    """
    Devuelve el rol RBAC canónico en minúsculas.

    Alias reconocidos:
    - operator: operador, operario, operadora
    - admin: administrador, finiquitador (migración legada)
    - manager: gerente, supervisor
    - viewer: operativo (migración legada)
    """
    r = (rol or "").strip().lower()
    if not r:
        return "viewer"
    if r in _CANONICAL:
        return r
    if r in ("operador", "operario", "operadora"):
        return "operator"
    if r in ("administrador", "finiquitador"):
        return "admin"
    if r in ("gerente", "supervisor"):
        return "manager"
    if r == "operativo":
        return "viewer"
    return r
