"""
Validadores compartidos para snapshot y guardado de candidatos préstamo (Drive / CONCILIACIÓN).

1) Formato de cédula: se delega a `validate_cedula` en el job y en `_motivos_no_100`.
2) Tabla `prestamos` (misma cédula normalizada):
   - **V** o **E**: máximo **un** préstamo en estado **APROBADO** (puede tener varios **LIQUIDADO**).
   - **J** (jurídico): puede tener **uno o más** créditos APROBADO.
   `duplicada_en_hoja` en payload es solo informativo (misma cédula en varias filas Drive); no bloquea el guardado.
"""
from __future__ import annotations

from typing import Any, Dict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.prestamo import Prestamo


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
    from app.api.v1.endpoints.clientes import _normalizar_cedula_carga_masiva

    stmt = select(Prestamo.cedula)
    if solo_aprobado:
        stmt = stmt.where(func.upper(func.trim(func.coalesce(Prestamo.estado, ""))) == "APROBADO")
    out: Dict[str, int] = {}
    for cel in db.execute(stmt).scalars().all() or []:
        n = _normalizar_cedula_carga_masiva(cel or "")
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
    from sqlalchemy import func

    from app.api.v1.endpoints.clientes import _normalizar_cedula_carga_masiva

    stmt = select(Prestamo.cedula).where(
        func.upper(func.trim(func.coalesce(Prestamo.estado, ""))) == "LIQUIDADO"
    )
    out: Dict[str, int] = {}
    for cel in db.execute(stmt).scalars().all() or []:
        n = _normalizar_cedula_carga_masiva(cel or "")
        if not n:
            continue
        out[n] = out.get(n, 0) + 1
    return out


def n_aprobados_en_payload(payload: Dict[str, Any]) -> int:
    """Cuenta APROBADO en payload; nunca infiere desde el total (LIQUIDADO no cuenta)."""
    try:
        return max(0, int(payload.get("prestamos_aprobados_misma_cedula_norm_count") or 0))
    except (TypeError, ValueError):
        return 0


def cupo_ve_permite_nuevo_prestamo(*, es_ve: bool, es_j: bool, n_aprob: int) -> bool:
    """V/E: solo si hay 0 APROBADO (varios LIQUIDADO están permitidos). J: siempre."""
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
) -> Dict[str, Any]:
    """Actualiza conteos y validador cupo V/E desde BD (no mezcla LIQUIDADO con APROBADO)."""
    pl = dict(payload or {})
    cmp_e = (cedula_cmp or pl.get("cedula_cmp") or "").strip()
    n_total = int(prestamo_counts_total.get(cmp_e, 0) or 0)
    n_aprob = int(prestamo_counts_aprob.get(cmp_e, 0) or 0)
    n_liq = int(prestamo_counts_liq.get(cmp_e, 0) or 0)
    es_ve = cedula_cmp_es_tipo_v_o_e(cmp_e)
    es_j = cedula_cmp_es_tipo_j(cmp_e)
    permite = cupo_ve_permite_nuevo_prestamo(es_ve=es_ve, es_j=es_j, n_aprob=n_aprob)
    pl["prestamos_misma_cedula_norm_count"] = n_total
    pl["prestamos_aprobados_misma_cedula_norm_count"] = n_aprob
    pl["prestamos_liquidados_misma_cedula_norm_count"] = n_liq
    pl["validador_ve_max_un_prestamo_ok"] = permite
    pl["validador_v_max_un_prestamo_ok"] = permite
    return pl
