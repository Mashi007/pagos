"""
Validadores compartidos para snapshot y guardado de candidatos préstamo (Drive / CONCILIACIÓN).

1) Formato de cédula: se delega a `validate_cedula` en el job y en `_motivos_no_100`.
2) Tabla `prestamos` (misma cédula normalizada):
   - **V** o **E**: máximo **un** préstamo en estado **APROBADO**.
   - **V** (solo): si ya hay préstamo(s) en cartera, **todos** deben estar en
     **Liquidado / Terminado** (`estado=LIQUIDADO` y `estado_gestion_finiquito=TERMINADO`).
     REVISION, EN_PROCESO u otra fase de finiquito **bloquean** alta nueva desde Drive.
   - **J** (jurídico): puede tener **uno o más** créditos APROBADO.
   - **DESISTIMIENTO** (o alias DESESTIMADO/DESISTIDO): **nunca** se puede cargar un préstamo
     nuevo desde Drive para esa cédula (cualquier letra).
   `duplicada_en_hoja` en payload es solo informativo (misma cédula en varias filas Drive); el
   auto-guardar además evita una 2.ª alta V/E en el mismo lote.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.constants.prestamo_estados import ESTADOS_PRESTAMO_DESISTIMIENTO_VARIANTES
from app.models.prestamo import Prestamo

MSG_DRIVE_BLOQUEO_DESISTIMIENTO = (
    "Cédula con préstamo en DESISTIMIENTO (o DESESTIMADO/DESISTIDO): "
    "no se puede cargar ningún préstamo nuevo desde Drive."
)

MSG_DRIVE_BLOQUEO_V_NO_LIQUIDADO_TERMINADO = (
    "Cédula tipo V: solo se puede importar un crédito nuevo desde Drive si el préstamo "
    "en cartera está en Liquidado / Terminado (estado LIQUIDADO y gestión de finiquito "
    "TERMINADO). No aplica si está en revisión u otra fase de finiquito."
)


def cedula_cmp_es_tipo_venezolano_v(cmp_e: str) -> bool:
    """
    True si la cédula normalizada corresponde a documento con letra V
    (primera letra de la clave comparada, p. ej. V12345678).
    """
    u = (cmp_e or "").strip().upper()
    return bool(u) and u[0] == "V"


def cedula_cmp_es_tipo_j(cmp_e: str) -> bool:
    """True si la cédula normalizada empieza por **J** (persona jurídica / RIF típico)."""
    u = (cmp_e or "").strip().upper()
    return bool(u) and u[0] == "J"


def cedula_cmp_es_tipo_v_o_e(cmp_e: str) -> bool:
    """
    True si la cédula normalizada empieza por **V** o **E** (misma clave que carga masiva).
    Regla de negocio: solo pueden tener un préstamo en cartera; más de uno no cumple validador.
    """
    u = (cmp_e or "").strip().upper()
    return bool(u) and u[0] in ("V", "E")


def _conteo_prestamos_por_cedula_norm_filtrado(
    db: Session,
    *,
    solo_aprobado: bool,
) -> Dict[str, int]:
    """Conteo por cédula normalizada (misma regla que check-cédulas / carga masiva)."""
    from app.api.v1.endpoints.clientes import _cedula_clave_comparacion_clientes

    stmt = select(Prestamo.cedula)
    if solo_aprobado:
        stmt = stmt.where(func.upper(func.trim(func.coalesce(Prestamo.estado, ""))) == "APROBADO")
    out: Dict[str, int] = {}
    for cel in db.execute(stmt).scalars().all() or []:
        n = _cedula_clave_comparacion_clientes(cel or "")
        if not n:
            continue
        out[n] = out.get(n, 0) + 1
    return out


def conteo_prestamos_por_cedula_norm(db: Session) -> Dict[str, int]:
    """Total de filas en `prestamos` por cédula (cualquier estado)."""
    return _conteo_prestamos_por_cedula_norm_filtrado(db, solo_aprobado=False)


def conteo_prestamos_aprobados_por_cedula_norm(db: Session) -> Dict[str, int]:
    """
    Préstamos en estado APROBADO por cédula normalizada.
    Regla V/E en Drive: máximo un APROBADO activo; LIQUIDADO u otros no bloquean un nuevo alta.
    """
    return _conteo_prestamos_por_cedula_norm_filtrado(db, solo_aprobado=True)


def conteo_prestamos_liquidados_por_cedula_norm(db: Session) -> Dict[str, int]:
    """Préstamos LIQUIDADO por cédula (solo informativo en UI; no bloquea cupo V/E)."""
    from app.api.v1.endpoints.clientes import _cedula_clave_comparacion_clientes

    stmt = select(Prestamo.cedula).where(
        func.upper(func.trim(func.coalesce(Prestamo.estado, ""))) == "LIQUIDADO"
    )
    out: Dict[str, int] = {}
    for cel in db.execute(stmt).scalars().all() or []:
        n = _cedula_clave_comparacion_clientes(cel or "")
        if not n:
            continue
        out[n] = out.get(n, 0) + 1
    return out


def conteo_prestamos_desistimiento_por_cedula_norm(db: Session) -> Dict[str, int]:
    """Préstamos en DESISTIMIENTO / DESESTIMADO / DESISTIDO por cédula comparable."""
    from app.api.v1.endpoints.clientes import _cedula_clave_comparacion_clientes

    estados = sorted(ESTADOS_PRESTAMO_DESISTIMIENTO_VARIANTES)
    stmt = select(Prestamo.cedula).where(
        func.upper(func.trim(func.coalesce(Prestamo.estado, ""))).in_(estados)
    )
    out: Dict[str, int] = {}
    for cel in db.execute(stmt).scalars().all() or []:
        n = _cedula_clave_comparacion_clientes(cel or "")
        if not n:
            continue
        out[n] = out.get(n, 0) + 1
    return out


def cedula_bloqueada_por_desistimiento_drive(n_desistimiento: int) -> bool:
    """True si hay al menos un préstamo en desistimiento: Drive no puede alta nueva."""
    return int(n_desistimiento or 0) >= 1


def prestamo_esta_liquidado_terminado(
    estado: Optional[str],
    estado_gestion_finiquito: Optional[str],
) -> bool:
    """
    True solo para la etiqueta de negocio **Liquidado / Terminado**:
    `prestamos.estado = LIQUIDADO` y `estado_gestion_finiquito = TERMINADO`.
    """
    return (
        (estado or "").strip().upper() == "LIQUIDADO"
        and (estado_gestion_finiquito or "").strip().upper() == "TERMINADO"
    )


def _expr_prestamo_liquidado_terminado():
    estado_u = func.upper(func.trim(func.coalesce(Prestamo.estado, "")))
    gestion_u = func.upper(
        func.trim(func.coalesce(Prestamo.estado_gestion_finiquito, ""))
    )
    return and_(estado_u == "LIQUIDADO", gestion_u == "TERMINADO")


def conteo_prestamos_no_liquidado_terminado_por_cedula_norm(db: Session) -> Dict[str, int]:
    """
    Préstamos que **no** están en Liquidado / Terminado, por cédula comparable.
    Usado para bloquear alta Drive en cédulas tipo **V**.
    """
    from app.api.v1.endpoints.clientes import _cedula_clave_comparacion_clientes

    stmt = select(Prestamo.cedula).where(~_expr_prestamo_liquidado_terminado())
    out: Dict[str, int] = {}
    for cel in db.execute(stmt).scalars().all() or []:
        n = _cedula_clave_comparacion_clientes(cel or "")
        if not n:
            continue
        out[n] = out.get(n, 0) + 1
    return out


def cedula_v_bloqueada_por_no_liquidado_terminado(
    *,
    es_v: bool,
    n_no_liquidado_terminado: int,
) -> bool:
    """
    Cédula **V**: si hay al menos un préstamo que no está Liquidado / Terminado,
    Drive no puede importar un crédito nuevo.
    """
    if not es_v:
        return False
    return int(n_no_liquidado_terminado or 0) >= 1


def conteos_cupo_para_una_cedula(db: Session, cedula_cmp: str) -> Dict[str, int]:
    """
    Conteos total / APROBADO / LIQUIDADO / DESISTIMIENTO / no Liquidado-Terminado
    solo para una cédula (edición puntual).
    Evita escanear toda la tabla `prestamos` en cada POST actualizar-campos.
    """
    from app.api.v1.endpoints.clientes import _cedula_clave_comparacion_clientes
    from app.utils.cedula_almacenamiento import (
        expr_cedula_normalizada_para_comparar,
        texto_cedula_comparable_bd,
    )

    key = _cedula_clave_comparacion_clientes(cedula_cmp or "") or texto_cedula_comparable_bd(
        cedula_cmp or ""
    )
    if not key:
        return {"total": 0, "aprob": 0, "liq": 0, "desist": 0, "no_liq_term": 0}

    ced_sql = expr_cedula_normalizada_para_comparar(Prestamo.cedula)
    estado_u = func.upper(func.trim(func.coalesce(Prestamo.estado, "")))
    rows = db.execute(
        select(estado_u, func.count())
        .where(ced_sql == key)
        .group_by(estado_u)
    ).all()
    total = 0
    aprob = 0
    liq = 0
    desist = 0
    desist_set = {e.upper() for e in ESTADOS_PRESTAMO_DESISTIMIENTO_VARIANTES}
    for est, n in rows or []:
        nn = int(n or 0)
        total += nn
        eu = (est or "").strip().upper()
        if eu == "APROBADO":
            aprob = nn
        elif eu == "LIQUIDADO":
            liq = nn
        elif eu in desist_set:
            desist += nn
    no_liq_term = int(
        db.scalar(
            select(func.count())
            .where(ced_sql == key)
            .where(~_expr_prestamo_liquidado_terminado())
        )
        or 0
    )
    return {
        "total": total,
        "aprob": aprob,
        "liq": liq,
        "desist": desist,
        "no_liq_term": no_liq_term,
    }


def n_aprobados_en_payload(payload: Dict[str, Any]) -> int:
    """Cuenta APROBADO en payload; nunca infiere desde el total (LIQUIDADO no cuenta)."""
    try:
        return max(0, int(payload.get("prestamos_aprobados_misma_cedula_norm_count") or 0))
    except (TypeError, ValueError):
        return 0


def n_desistimiento_en_payload(payload: Dict[str, Any]) -> int:
    try:
        return max(0, int(payload.get("prestamos_desistimiento_misma_cedula_norm_count") or 0))
    except (TypeError, ValueError):
        return 0


def n_no_liquidado_terminado_en_payload(payload: Dict[str, Any]) -> int:
    try:
        return max(
            0,
            int(payload.get("prestamos_no_liquidado_terminado_misma_cedula_norm_count") or 0),
        )
    except (TypeError, ValueError):
        return 0


def cupo_ve_permite_nuevo_prestamo(*, es_ve: bool, es_j: bool, n_aprob: int) -> bool:
    """V/E: solo si hay 0 APROBADO. J: siempre. (V además exige Liquidado/Terminado aparte.)"""
    if es_j:
        return True
    if not es_ve:
        return n_aprob < 1
    return n_aprob < 1


def enriquecer_payload_conteos_cupo_bd(
    payload: Dict[str, Any],
    cedula_cmp: str,
    *,
    prestamo_counts_total: Dict[str, int],
    prestamo_counts_aprob: Dict[str, int],
    prestamo_counts_liq: Dict[str, int],
    prestamo_counts_desist: Optional[Dict[str, int]] = None,
    prestamo_counts_no_liq_term: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """Actualiza conteos y validador cupo V/E desde BD (no mezcla LIQUIDADO con APROBADO)."""
    pl = dict(payload or {})
    cmp_e = (cedula_cmp or pl.get("cedula_cmp") or "").strip()
    n_total = int(prestamo_counts_total.get(cmp_e, 0) or 0)
    n_aprob = int(prestamo_counts_aprob.get(cmp_e, 0) or 0)
    n_liq = int(prestamo_counts_liq.get(cmp_e, 0) or 0)
    n_desist = int((prestamo_counts_desist or {}).get(cmp_e, 0) or 0)
    if n_desist == 0:
        try:
            n_desist = max(0, int(pl.get("prestamos_desistimiento_misma_cedula_norm_count") or 0))
        except (TypeError, ValueError):
            n_desist = 0
    n_no_liq_term = int((prestamo_counts_no_liq_term or {}).get(cmp_e, 0) or 0)
    if n_no_liq_term == 0:
        try:
            n_no_liq_term = max(
                0,
                int(pl.get("prestamos_no_liquidado_terminado_misma_cedula_norm_count") or 0),
            )
        except (TypeError, ValueError):
            n_no_liq_term = 0
    es_ve = cedula_cmp_es_tipo_v_o_e(cmp_e)
    es_j = cedula_cmp_es_tipo_j(cmp_e)
    es_v = cedula_cmp_es_tipo_venezolano_v(cmp_e)
    permite = cupo_ve_permite_nuevo_prestamo(es_ve=es_ve, es_j=es_j, n_aprob=n_aprob)
    sin_desist = not cedula_bloqueada_por_desistimiento_drive(n_desist)
    sin_v_bloqueo = not cedula_v_bloqueada_por_no_liquidado_terminado(
        es_v=es_v, n_no_liquidado_terminado=n_no_liq_term
    )
    pl["prestamos_misma_cedula_norm_count"] = n_total
    pl["prestamos_aprobados_misma_cedula_norm_count"] = n_aprob
    pl["prestamos_liquidados_misma_cedula_norm_count"] = n_liq
    pl["prestamos_desistimiento_misma_cedula_norm_count"] = n_desist
    pl["prestamos_no_liquidado_terminado_misma_cedula_norm_count"] = n_no_liq_term
    # Recalcular tipo desde la clave (evita flags stale tras editar E → J).
    pl["cedula_es_tipo_j"] = es_j
    pl["cedula_es_tipo_ve"] = es_ve and not es_j
    pl["cedula_es_tipo_v_venezolano"] = es_v
    pl["cedula_es_tipo_e"] = bool(es_ve and not es_v)
    pl["validador_ve_max_un_prestamo_ok"] = permite and sin_desist and sin_v_bloqueo
    pl["validador_v_max_un_prestamo_ok"] = permite and sin_desist and sin_v_bloqueo
    pl["validador_sin_desistimiento_ok"] = sin_desist
    pl["validador_v_liquidado_terminado_ok"] = sin_v_bloqueo
    return pl
