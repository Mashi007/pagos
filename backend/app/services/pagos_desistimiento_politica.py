# -*- coding: utf-8 -*-
"""
Politica de pagos cuando el prestamo esta en LIQUIDADO o DESISTIMIENTO
(desestimado).

Reglas (producto):
1) CLIENTES / portal publico / jobs automaticos (sin usuario staff): NUNCA
   crear pagos ni aplicar cascada en LIQUIDADO/DESISTIMIENTO.
2) ADMIN, OPERADOR y GERENTE (sesion autenticada): SI pueden crear pagos,
   editar/aplicar cascada y operar revision manual en cualquier estado.
3) Visualizador (viewer): mismo bloqueo que portal para alta/cascada.

Notificaciones a clientes en esos estados siguen excluidas en
`notificaciones_exclusion_desistimiento`.
"""
from __future__ import annotations

from typing import Optional, Union

from sqlalchemy.orm import Session, object_session

from app.constants.prestamo_estados import (
    ESTADO_PRESTAMO_DESISTIMIENTO,
    ESTADOS_PRESTAMO_EXCLUIDOS_COBRANZA_NOTIF,
)
from app.core.rol_normalization import canonical_rol
from app.models.prestamo import Prestamo
from app.schemas.auth import UserResponse

_ESTADOS_BLOQUEAN_ALTA_PAGO = frozenset(
    {
        str(e).strip().upper()
        for e in ESTADOS_PRESTAMO_EXCLUIDOS_COBRANZA_NOTIF
    }
    | {"DESESTIMADO", "DESISTIDO"}
)

# Panel interno con permiso de operar cartera en liquidados/desestimados.
_ROLES_STAFF_EXCEPCION_PAGO = frozenset({"admin", "operator", "manager"})

MSG_NO_PAGO_LIQUIDADO = (
    "Este credito esta LIQUIDADO: no se pueden cargar pagos desde el portal "
    "ni canales automaticos. Solo personal interno (operador/admin/gerente) "
    "puede registrarlos."
)

MSG_NO_PAGO_DESISTIMIENTO = (
    "Este credito esta en DESISTIMIENTO (desestimado): no se pueden cargar pagos "
    "desde el portal ni canales automaticos. Solo personal interno "
    "(operador/admin/gerente) puede registrarlos."
)

MSG_NO_PAGO_ESTADO = (
    "Este credito no admite carga de pagos (estado {estado}) desde el portal "
    "ni canales automaticos. Solo personal interno puede registrarlos."
)

MSG_NO_PAGO_ROL_INSUFICIENTE = (
    "Prestamo en DESISTIMIENTO o LIQUIDADO: su rol no tiene permiso para "
    "cargar o aplicar pagos a cuotas (se requiere operador, administrador o gerente)."
)

MSG_DESISTIMIENTO_NO_CUOTAS = (
    "Prestamo en DESISTIMIENTO o LIQUIDADO: no se aplican pagos a cuotas "
    "desde el portal ni canales automaticos. Solo personal interno "
    "(operador/admin/gerente) puede aplicarlos."
)
MSG_DESISTIMIENTO_NO_CARTERA_AUTO = MSG_NO_PAGO_DESISTIMIENTO
MSG_DESISTIMIENTO_STAFF_FORBIDDEN = MSG_NO_PAGO_ROL_INSUFICIENTE
MSG_DESISTIMIENTO_SOLO_STAFF = MSG_NO_PAGO_ROL_INSUFICIENTE


def _norm_estado(estado: Optional[str]) -> str:
    return (estado or "").strip().upper()


def _rol_raw_usuario(user: Optional[Union[UserResponse, object]]) -> str:
    if user is None:
        return ""
    raw = getattr(user, "rol", None)
    if raw is None:
        raw = getattr(user, "role", None)
    if isinstance(user, dict):
        raw = user.get("rol") or user.get("role") or raw
    return str(raw or "").strip()


def _rol_de_usuario(user: Optional[Union[UserResponse, object]]) -> str:
    return canonical_rol(_rol_raw_usuario(user))


def usuario_puede_cargar_pago_desistimiento_a_cartera(
    user: Optional[Union[UserResponse, object]],
) -> bool:
    """True si el usuario de sesion puede alta/aplicar en LIQUIDADO/DESISTIMIENTO."""
    if user is None:
        return False
    if bool(getattr(user, "is_admin", False)):
        return True
    rol = _rol_de_usuario(user)
    if rol in _ROLES_STAFF_EXCEPCION_PAGO:
        return True
    # Alias residual por si el token trae texto no normalizado.
    raw = _rol_raw_usuario(user).lower()
    if raw in {"operador", "operario", "operadora", "administrador", "gerente", "supervisor"}:
        return True
    return False


def prestamo_estado_bloquea_alta_pago(estado: Optional[str]) -> bool:
    return _norm_estado(estado) in _ESTADOS_BLOQUEAN_ALTA_PAGO


def mensaje_bloqueo_alta_pago(estado: Optional[str]) -> str:
    est = _norm_estado(estado)
    if est == "LIQUIDADO":
        return MSG_NO_PAGO_LIQUIDADO
    if est in (
        ESTADO_PRESTAMO_DESISTIMIENTO,
        "DESESTIMADO",
        "DESISTIDO",
    ):
        return MSG_NO_PAGO_DESISTIMIENTO
    if est:
        return MSG_NO_PAGO_ESTADO.format(estado=est)
    return MSG_NO_PAGO_ESTADO.format(estado="desconocido")


def prestamo_estado_es_desistimiento(estado: Optional[str]) -> bool:
    return _norm_estado(estado) == ESTADO_PRESTAMO_DESISTIMIENTO


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


def prestamo_id_bloquea_alta_pago(db: Session, prestamo_id: Optional[int]) -> bool:
    return prestamo_estado_bloquea_alta_pago(obtener_estado_prestamo(db, prestamo_id))


def prestamo_bloquea_aplicacion_a_cuotas(
    db: Optional[Session],
    prestamo_id: Optional[int],
    user: Optional[Union[UserResponse, object]] = None,
) -> bool:
    """
    True si no se debe aplicar cascada / cuota_pagos.

    Con personal interno autenticado (admin/operador/gerente): no bloquea.
    Sin usuario (portal/auto) o rol insuficiente: si.
    """
    if db is None or prestamo_id is None:
        return False
    if not prestamo_id_bloquea_alta_pago(db, prestamo_id):
        return False
    if usuario_puede_cargar_pago_desistimiento_a_cartera(user):
        return False
    return True


def pago_bloquea_aplicacion_a_cuotas(
    pago: object,
    user: Optional[Union[UserResponse, object]] = None,
) -> bool:
    """Misma regla usando la sesion del objeto Pago (si esta attached)."""
    prestamo_id = getattr(pago, "prestamo_id", None)
    if not prestamo_id:
        return False
    db = object_session(pago)
    if db is None:
        return False
    return prestamo_bloquea_aplicacion_a_cuotas(db, int(prestamo_id), user=user)


def assert_staff_puede_crear_pago_en_desistimiento(
    db: Session,
    *,
    prestamo_id: Optional[int],
    user: Optional[Union[UserResponse, object]] = None,
) -> None:
    """Bloquea alta en LIQUIDADO/DESISTIMIENTO salvo personal interno."""
    from fastapi import HTTPException

    estado = obtener_estado_prestamo(db, prestamo_id)
    if not prestamo_estado_bloquea_alta_pago(estado):
        return
    if usuario_puede_cargar_pago_desistimiento_a_cartera(user):
        return
    if user is None:
        raise HTTPException(status_code=403, detail=mensaje_bloqueo_alta_pago(estado))
    rol = _rol_raw_usuario(user) or _rol_de_usuario(user) or "desconocido"
    raise HTTPException(
        status_code=403,
        detail=f"{MSG_NO_PAGO_ROL_INSUFICIENTE} (rol sesion: {rol}).",
    )


def assert_puede_crear_pago_en_cartera(
    db: Session,
    *,
    prestamo_id: Optional[int],
    user: Optional[Union[UserResponse, object]] = None,
) -> None:
    assert_staff_puede_crear_pago_en_desistimiento(
        db, prestamo_id=prestamo_id, user=user
    )


def bloquear_carga_automatica_a_cartera_si_desistimiento(
    db: Session,
    prestamo_id: Optional[int],
) -> Optional[str]:
    """Portal / Gmail / jobs: no crear en `pagos` si LIQUIDADO/DESISTIMIENTO."""
    estado = obtener_estado_prestamo(db, prestamo_id)
    if prestamo_estado_bloquea_alta_pago(estado):
        return mensaje_bloqueo_alta_pago(estado)
    return None


def bloquear_alta_pago_a_cartera(
    db: Session,
    prestamo_id: Optional[int],
) -> Optional[str]:
    return bloquear_carga_automatica_a_cartera_si_desistimiento(db, prestamo_id)