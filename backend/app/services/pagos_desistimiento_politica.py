# -*- coding: utf-8 -*-
"""
Politica de pagos cuando el prestamo esta en DESISTIMIENTO.

Reglas (producto):
1) NUNCA aplicar pagos a cuotas (cascada / cuota_pagos) por ningun medio.
2) Fuentes automaticas (Gmail, OCR, Excel masivo, reportados, mover desde
   revision): NUNCA crean fila en `pagos` de cartera; van a revision manual
   (`pagos_con_errores` / cola reportados) para no romper el flujo.
3) Solo administrador u operador pueden registrar un pago manual en `pagos`
   (estado de cuenta / historial); aun asi NO se aplica a cuotas.
"""
from __future__ import annotations

from typing import Optional, Union

from sqlalchemy.orm import Session, object_session

from app.constants.prestamo_estados import ESTADO_PRESTAMO_DESISTIMIENTO
from app.core.rol_normalization import canonical_rol
from app.models.prestamo import Prestamo
from app.schemas.auth import UserResponse

MSG_DESISTIMIENTO_NO_CUOTAS = (
    "Prestamo en DESISTIMIENTO: no se aplican pagos a cuotas por ningun medio."
)

MSG_DESISTIMIENTO_NO_CARTERA_AUTO = (
    "Prestamo en DESISTIMIENTO: no se carga al estado de cuenta/cuotas. "
    "El pago queda en revision manual (Gmail/OCR/Excel/reportados no aplican a cartera)."
)

MSG_DESISTIMIENTO_STAFF_FORBIDDEN = (
    "Prestamo en DESISTIMIENTO: su rol no puede registrar pagos. "
    "Solo operador o administrador (y nunca se aplican a cuotas)."
)

MSG_DESISTIMIENTO_SOLO_STAFF = MSG_DESISTIMIENTO_NO_CARTERA_AUTO


def prestamo_estado_es_desistimiento(estado: Optional[str]) -> bool:
    return (estado or "").strip().upper() == ESTADO_PRESTAMO_DESISTIMIENTO


def usuario_puede_cargar_pago_desistimiento_a_cartera(
    user: Optional[Union[UserResponse, object]],
) -> bool:
    """Admin/operador pueden crear fila en `pagos` (sin aplicar a cuotas)."""
    if user is None:
        return False
    rol = canonical_rol(getattr(user, "rol", None))
    return rol in ("admin", "operator")


def obtener_estado_prestamo(db: Session, prestamo_id: Optional[int]) -> Optional[str]:
    if prestamo_id is None:
        return None
    try:
        pid = int(prestamo_id)
    except (TypeError, ValueError):
        return None
    if pid <= 0:
        return None
    p = db.get(Prestamo, pid)
    if p is None:
        return None
    return getattr(p, "estado", None)


def prestamo_id_es_desistimiento(db: Session, prestamo_id: Optional[int]) -> bool:
    return prestamo_estado_es_desistimiento(obtener_estado_prestamo(db, prestamo_id))


def prestamo_bloquea_aplicacion_a_cuotas(
    db: Optional[Session],
    prestamo_id: Optional[int],
) -> bool:
    """True si no se debe aplicar cascada / cuota_pagos (DESISTIMIENTO)."""
    if db is None or prestamo_id is None:
        return False
    return prestamo_id_es_desistimiento(db, prestamo_id)


def pago_bloquea_aplicacion_a_cuotas(pago: object) -> bool:
    """Misma regla usando la sesion del objeto Pago (si esta attached)."""
    prestamo_id = getattr(pago, "prestamo_id", None)
    if not prestamo_id:
        return False
    db = object_session(pago)
    if db is None:
        return False
    return prestamo_id_es_desistimiento(db, int(prestamo_id))


def assert_staff_puede_crear_pago_en_desistimiento(
    db: Session,
    *,
    prestamo_id: Optional[int],
    user: Optional[Union[UserResponse, object]],
) -> None:
    """
    POST /pagos y batch staff.
    DESISTIMIENTO + no admin/operador -> 403.
    (La aplicacion a cuotas se bloquea aparte en cascada.)
    """
    from fastapi import HTTPException

    if not prestamo_id_es_desistimiento(db, prestamo_id):
        return
    if usuario_puede_cargar_pago_desistimiento_a_cartera(user):
        return
    raise HTTPException(status_code=403, detail=MSG_DESISTIMIENTO_STAFF_FORBIDDEN)


def bloquear_carga_automatica_a_cartera_si_desistimiento(
    db: Session,
    prestamo_id: Optional[int],
) -> Optional[str]:
    """
    Gmail/Excel/reportados/mover_a_pagos: no crear en `pagos`.
    Devuelve mensaje de bloqueo o None.
    """
    if prestamo_id_es_desistimiento(db, prestamo_id):
        return MSG_DESISTIMIENTO_NO_CARTERA_AUTO
    return None