# -*- coding: utf-8 -*-
"""
Visibilidad de préstamos en DESISTIMIENTO (regla de negocio).

- Listados: operadores/gerentes/lectores no ven filas en ese estado (solo administrador).
- Detalle y lecturas asociadas: mismo criterio (403 si no es administrador).

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


def usuario_puede_ver_prestamos_desistimiento(user: UserResponse) -> bool:
    """Solo rol administrador (canónico) puede ver préstamos en DESISTIMIENTO."""
    return canonical_rol(user.rol) == "admin"


def prestamo_estado_es_desistimiento(estado: Optional[str]) -> bool:
    return (estado or "").strip().upper() == "DESISTIMIENTO"


def assert_lectura_prestamo_desistimiento(p: Prestamo, user: UserResponse) -> None:
    """403 si el préstamo está en desistimiento y el usuario no es administrador."""
    if not prestamo_estado_es_desistimiento(getattr(p, "estado", None)):
        return
    if usuario_puede_ver_prestamos_desistimiento(user):
        return
    raise HTTPException(
        status_code=403,
        detail="Préstamo en desistimiento: solo el administrador puede consultar el detalle.",
    )


def filtro_prestamo_visible_listado(user: UserResponse) -> ColumnElement[bool]:
    """Predicado SQL para excluir DESISTIMIENTO a no administradores."""
    if usuario_puede_ver_prestamos_desistimiento(user):
        return true()
    return func.upper(func.coalesce(Prestamo.estado, "")) != "DESISTIMIENTO"
