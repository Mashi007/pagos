# -*- coding: utf-8 -*-
"""
Visibilidad y operacion de prestamos en DESISTIMIENTO (regla de negocio).

- Listados / detalle: administrador y operador pueden ver y abrir.
- Gerentes/lectores: no ven filas en DESISTIMIENTO.

Las notificaciones al cliente siguen centralizadas en
`app.services.notificaciones_exclusion_desistimiento`.
"""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, true
from sqlalchemy.sql.elements import ColumnElement

from app.core.rol_normalization import canonical_rol
from app.models.prestamo import Prestamo
from app.schemas.auth import UserResponse

_ROLES_DESISTIMIENTO = frozenset({"admin", "operator"})


def usuario_puede_ver_prestamos_desistimiento(user: UserResponse) -> bool:
    """Admin u operador pueden ver/abrir prestamos en DESISTIMIENTO."""
    return canonical_rol(getattr(user, "rol", None)) in _ROLES_DESISTIMIENTO


def usuario_puede_mutar_prestamo_desistimiento(user: UserResponse) -> bool:
    """Misma regla que visibilidad: admin/operador pueden editar/eliminar."""
    return usuario_puede_ver_prestamos_desistimiento(user)


def prestamo_estado_es_desistimiento(estado: Optional[str]) -> bool:
    return (estado or "").strip().upper() == "DESISTIMIENTO"


def assert_lectura_prestamo_desistimiento(p: Prestamo, user: UserResponse) -> None:
    """403 si el prestamo esta en desistimiento y el usuario no es admin/operador."""
    if not prestamo_estado_es_desistimiento(getattr(p, "estado", None)):
        return
    if usuario_puede_ver_prestamos_desistimiento(user):
        return
    raise HTTPException(
        status_code=403,
        detail="Prestamo en desistimiento: solo administrador u operador pueden consultarlo.",
    )


def filtro_prestamo_visible_listado(user: UserResponse) -> ColumnElement[bool]:
    """Predicado SQL para excluir DESISTIMIENTO a roles sin permiso."""
    if usuario_puede_ver_prestamos_desistimiento(user):
        return true()
    return func.upper(func.coalesce(Prestamo.estado, "")) != "DESISTIMIENTO"