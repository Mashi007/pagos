# -*- coding: utf-8 -*-
"""
Politica de pagos cuando el prestamo esta en LIQUIDADO o DESISTIMIENTO
(desestimado).

Reglas (producto):
1) CLIENTES / portal publico / jobs automaticos: NUNCA crear fila en `pagos`
   ni recibir notificaciones asociadas a esos estados.
2) OPERADOR y ADMINISTRADOR: SI pueden crear pagos y aplicar cascada a cuotas
   (revision manual, POST /pagos, aplicar-cuotas, etc.).
3) Otros roles staff (p. ej. viewer/manager): mismo bloqueo que clientes para alta.

Excepciones internas de reconstruccion (finiquito / conciliar cartera) no usan
estos helpers; siguen su propio flujo de negocio.
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

# Alias posibles en datos / lenguaje de negocio ("desestimados").
_ESTADOS_BLOQUEAN_ALTA_PAGO = frozenset(
    {
        str(e).strip().upper()
        for e in ESTADOS_PRESTAMO_EXCLUIDOS_COBRANZA_NOTIF
    }
    | {"DESESTIMADO", "DESISTIDO"}
)

# Roles que pueden operar pagos en LIQUIDADO / DESISTIMIENTO.
_ROLES_STAFF_EXCEPCION_PAGO = frozenset({"admin", "operator"})

MSG_NO_PAGO_LIQUIDADO = (
    "Este credito esta LIQUIDADO: no se pueden cargar pagos desde el portal "
    "ni canales automaticos. Solo operadores y administradores pueden registrarlos."
)

MSG_NO_PAGO_DESISTIMIENTO = (
    "Este credito esta en DESISTIMIENTO (desestimado): no se pueden cargar pagos "
    "desde el portal ni canales automaticos. Solo operadores y administradores "
    "pueden registrarlos."
)

MSG_NO_PAGO_ESTADO = (
    "Este credito no admite carga de pagos (estado {estado}) desde el portal "
    "ni canales automaticos. Solo operadores y administradores pueden registrarlos."
)

MSG_NO_PAGO_ROL_INSUFICIENTE = (
    "Prestamo en DESISTIMIENTO o LIQUIDADO: solo operadores y administradores "
    "pueden cargar o aplicar pagos a cuotas."
)

# Compat: nombres historicos usados por callers.
MSG_DESISTIMIENTO_NO_CUOTAS = (
    "Prestamo en DESISTIMIENTO o LIQUIDADO: no se aplican pagos a cuotas "
    "desde el portal ni canales automaticos. Solo operadores y administradores "
    "pueden aplicarlos."
)
MSG_DESISTIMIENTO_NO_CARTERA_AUTO = MSG_NO_PAGO_DESISTIMIENTO
MSG_DESISTIMIENTO_STAFF_FORBIDDEN = MSG_NO_PAGO_ROL_INSUFICIENTE
MSG_DESISTIMIENTO_SOLO_STAFF = MSG_NO_PAGO_ROL_INSUFICIENTE


def _norm_estado(estado: Optional[str]) -> str:
    return (estado or "").strip().upper()


def _rol_de_usuario(user: Optional[Union[UserResponse, object]]) -> str:
    if user is None:
        return ""
    return canonical_rol(getattr(user, "rol", None))


def usuario_puede_cargar_pago_desistimiento_a_cartera(
    user: Optional[Union[UserResponse, object]],
) -> bool:
    """True si admin u operador pueden alta/aplicar en LIQUIDADO/DESISTIMIENTO."""
    return _rol_de_usuario(user) in _ROLES_STAFF_EXCEPCION_PAGO


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

    Admin/operador: no bloquea. Sin usuario (portal/auto) o rol insuficiente: si.
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
    """
    Bloquea alta de pago en LIQUIDADO / DESISTIMIENTO salvo admin/operador.
    Nombre historico conservado por compatibilidad con callers.
    """
    from fastapi import HTTPException

    estado = obtener_estado_prestamo(db, prestamo_id)
    if not prestamo_estado_bloquea_alta_pago(estado):
        return
    if usuario_puede_cargar_pago_desistimiento_a_cartera(user):
        return
    if user is None:
        raise HTTPException(status_code=403, detail=mensaje_bloqueo_alta_pago(estado))
    raise HTTPException(status_code=403, detail=MSG_NO_PAGO_ROL_INSUFICIENTE)


def assert_puede_crear_pago_en_cartera(
    db: Session,
    *,
    prestamo_id: Optional[int],
    user: Optional[Union[UserResponse, object]] = None,
) -> None:
    """Alias explicito del bloqueo de alta (staff/API)."""
    assert_staff_puede_crear_pago_en_desistimiento(
        db, prestamo_id=prestamo_id, user=user
    )


def bloquear_carga_automatica_a_cartera_si_desistimiento(
    db: Session,
    prestamo_id: Optional[int],
) -> Optional[str]:
    """
    Portal / Gmail / Excel sin excepcion de rol / reportados auto: no crear en `pagos`.
    Devuelve mensaje de bloqueo o None.
    Cubre LIQUIDADO y DESISTIMIENTO (nombre historico conservado).
    """
    estado = obtener_estado_prestamo(db, prestamo_id)
    if prestamo_estado_bloquea_alta_pago(estado):
        return mensaje_bloqueo_alta_pago(estado)
    return None


def bloquear_alta_pago_a_cartera(
    db: Session,
    prestamo_id: Optional[int],
) -> Optional[str]:
    """Alias explicito de bloquear_carga_automatica_a_cartera_si_desistimiento."""
    return bloquear_carga_automatica_a_cartera_si_desistimiento(db, prestamo_id)