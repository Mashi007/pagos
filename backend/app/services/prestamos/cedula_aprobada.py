# -*- coding: utf-8 -*-
"""
Criterio único de «cliente aprobado»: la cédula tiene al menos un préstamo en
estado APROBADO, sea por ``prestamos.cedula`` (la vía del cupo) o por la cédula
del cliente al que apunta el préstamo.

Vive aquí y no dentro del módulo de recibos porque el pipeline de Gmail necesita
la misma respuesta *antes* de gastar OCR en un correo. Si las dos puertas no
comparten criterio, un comprobante puede superar el escaneo y luego desaparecer
de Recibos sin dejar rastro de por qué.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _variantes_clave_cedula(clave: str) -> list[str]:
    """V30771164 y 30771164 son la misma persona para el filtro de Recibos."""
    k = (clave or "").strip().upper()
    if not k:
        return []
    out = [k]
    if k[0] in ("V", "E", "J", "G") and k[1:].isdigit() and 6 <= len(k) - 1 <= 11:
        out.append(k[1:])
    elif k.isdigit() and 6 <= len(k) <= 11:
        out.append("V" + k)
    return list(dict.fromkeys(out))


def claves_con_prestamo_aprobado(db: Session, claves: Iterable[str]) -> set[str]:
    """Subconjunto de `claves` (ya normalizadas) que tiene préstamo APROBADO."""
    from app.models.cliente import Cliente
    from app.models.prestamo import Prestamo
    from app.services.prestamos.cupo_cedula_aprobados import (
        contar_aprobados_por_claves_cupo,
    )
    from app.utils.cedula_almacenamiento import (
        expr_cedula_normalizada_para_comparar,
        normalizar_cedula_clave_cupo,
    )

    uniq = list(dict.fromkeys(c for c in claves if c))
    if not uniq:
        return set()
    # OCR a veces trae 30771164 y el préstamo V30771164 (o al revés).
    # Pedimos ambas formas al cupo; devolvemos las claves originales.
    consulta = list(dict.fromkeys(v for k in uniq for v in _variantes_clave_cedula(k)))
    cupo = contar_aprobados_por_claves_cupo(db, consulta)
    found: set[str] = set()
    for k in uniq:
        if any(int(cupo.get(v) or 0) > 0 for v in _variantes_clave_cedula(k)):
            found.add(k)
    missing = [k for k in uniq if k not in found]
    if not missing:
        return found

    # Pase extra: préstamo guardado como «V-30.771.164» vs clave OCR «V30771164».
    # Solo suma coincidencias. El cupo no se toca: también valida altas.
    missing_consulta = list(
        dict.fromkeys(v for k in missing for v in _variantes_clave_cedula(k))
    )
    missing_set = set(missing)
    consulta_set = set(missing_consulta)
    ced_norm = expr_cedula_normalizada_para_comparar(Prestamo.cedula)
    for raw in (
        db.execute(
            select(ced_norm)
            .where(Prestamo.estado == "APROBADO", ced_norm.in_(missing_consulta))
            .distinct()
        )
        .scalars()
        .all()
    ):
        hit = (str(raw) if raw is not None else "").strip()
        if hit not in consulta_set:
            continue
        for orig in missing:
            if hit in _variantes_clave_cedula(orig) or orig == hit:
                found.add(orig)
    missing = [k for k in missing if k not in found]
    if not missing:
        return found
    missing_consulta = list(
        dict.fromkeys(v for k in missing for v in _variantes_clave_cedula(k))
    )
    consulta_set = set(missing_consulta)
    cli_norm = expr_cedula_normalizada_para_comparar(Cliente.cedula)
    rows = (
        db.execute(
            select(Cliente.cedula)
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(Prestamo.estado == "APROBADO", cli_norm.in_(missing_consulta))
            .distinct()
        )
        .scalars()
        .all()
    )
    missing_set = set(missing)
    for raw in rows:
        k = normalizar_cedula_clave_cupo(raw)
        if not k:
            continue
        for orig in missing:
            if k in _variantes_clave_cedula(orig) or orig == k:
                if orig in missing_set:
                    found.add(orig)
    return found


def cedula_tiene_prestamo_aprobado(db: Session, cedula: Optional[str]) -> bool:
    """Versión de una sola cédula, tolerante a puntos, guiones y prefijo suelto."""
    from app.utils.cedula_almacenamiento import normalizar_cedula_clave_cupo

    clave = normalizar_cedula_clave_cupo(cedula or "")
    if not clave:
        return False
    return clave in claves_con_prestamo_aprobado(db, [clave])


# Columna Auditoría Email Recibos: solo APROBADO (no DESISTIMIENTO / LIQUIDADO).
ESTADOS_COLUMNA_PRESTAMO = ("APROBADO",)
_ESTADOS_SQL_COLUMNA = ("APROBADO",)
# Misma tolerancia que listado préstamos / TablaAmortizacionPrestamo (PENDIENTE POR PAGAR).
_TOL_SALDO_CUPO_RECIBOS = 0.01


def prestamo_ids_aprobados_con_cupo_recibos(
    db: Session, prestamo_ids: Iterable[int]
) -> set[int]:
    """
    Subconjunto de préstamos APROBADO con saldo pendiente > tol.

    Excluye LIQUIDADO (ya fuera por estado) y APROBADO «Pagado» con $0,00
    (cartera cerrada pendiente de job LIQUIDADO).
    """
    from app.models.prestamo import Prestamo
    from app.services.notificacion_service import (
        sum_saldo_pendiente_cuotas_tabla_amortizacion_ui,
    )

    ids = sorted({int(x) for x in prestamo_ids if x is not None})
    if not ids:
        return set()
    aprobados = {
        int(r[0])
        for r in db.execute(
            select(Prestamo.id).where(
                Prestamo.id.in_(ids),
                Prestamo.estado == "APROBADO",
            )
        ).all()
    }
    if not aprobados:
        return set()
    saldos = sum_saldo_pendiente_cuotas_tabla_amortizacion_ui(db, sorted(aprobados))
    return {
        pid
        for pid in aprobados
        if float(saldos.get(pid, 0) or 0) > _TOL_SALDO_CUPO_RECIBOS
    }


def prestamo_aprobado_operativo_recibos(
    db: Session, prestamo_id: Optional[int]
) -> bool:
    """True si el crédito es APROBADO y aún tiene cupo (saldo pendiente)."""
    if prestamo_id is None:
        return False
    try:
        pid = int(prestamo_id)
    except (TypeError, ValueError):
        return False
    return pid in prestamo_ids_aprobados_con_cupo_recibos(db, [pid])


def claves_con_prestamo_aprobado_operativo_recibos(
    db: Session, claves: Iterable[str]
) -> set[str]:
    """
    Cédulas con al menos un préstamo APROBADO **con saldo pendiente**.

    Usar en Recibos (OK / columna Préstamo / materializar): no pasar LIQUIDADO
    ni créditos ya pagados al 100 % (Estado «Pagado», $0 pendiente).
    """
    from app.models.cliente import Cliente
    from app.models.prestamo import Prestamo
    from app.utils.cedula_almacenamiento import (
        expr_cedula_normalizada_para_comparar,
        normalizar_cedula_clave_cupo,
    )

    base = claves_con_prestamo_aprobado(db, claves)
    if not base:
        return set()
    consulta = list(
        dict.fromkeys(v for k in base for v in _variantes_clave_cedula(k))
    )
    if not consulta:
        return set()

    p_norm = expr_cedula_normalizada_para_comparar(Prestamo.cedula)
    c_norm = expr_cedula_normalizada_para_comparar(Cliente.cedula)
    consulta_set = set(consulta)
    rows = db.execute(
        select(Prestamo.id, p_norm, c_norm)
        .select_from(Prestamo)
        .outerjoin(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Prestamo.estado == "APROBADO",
            or_(p_norm.in_(consulta), c_norm.in_(consulta)),
        )
    ).all()
    if not rows:
        return set()

    operativos = prestamo_ids_aprobados_con_cupo_recibos(
        db, [int(r[0]) for r in rows]
    )
    if not operativos:
        return set()

    claves_con_cupo: set[str] = set()
    for pid, p_hit, c_hit in rows:
        if int(pid) not in operativos:
            continue
        for hit in (p_hit, c_hit):
            hs = (str(hit) if hit is not None else "").strip()
            if hs and hs in consulta_set:
                claves_con_cupo.add(hs)

    out: set[str] = set()
    for clave in base:
        if any(v in claves_con_cupo for v in _variantes_clave_cedula(clave)):
            out.add(clave)
    return out


def cedula_tiene_prestamo_aprobado_operativo_recibos(
    db: Session, cedula: Optional[str]
) -> bool:
    """APROBADO con cupo: excluye LIQUIDADO y Pagado/$0 (sin deuda activa)."""
    from app.utils.cedula_almacenamiento import normalizar_cedula_clave_cupo

    clave = normalizar_cedula_clave_cupo(cedula or "")
    if not clave:
        return False
    return clave in claves_con_prestamo_aprobado_operativo_recibos(db, [clave])


def prestamo_estado_es_aprobado_activo_recibos(raw: Optional[str]) -> bool:
    """
    True solo si el crédito está operativo para cola Recibos / OK.

    Exige ``estado == APROBADO`` exacto. LIQUIDADO (terminado, revisión
    contable, finiquito, etc.), DESISTIMIENTO y cualquier otro → False.
    """
    return (raw or "").strip().upper() == "APROBADO"


def canon_estado_columna_prestamo(raw: Optional[str]) -> Optional[str]:
    """Normaliza estado de ``prestamos`` a APROBADO / DESISTIMIENTO / LIQUIDADO."""
    from app.constants.prestamo_estados import prestamo_estado_es_desistimiento

    u = (raw or "").strip().upper()
    if u == "APROBADO":
        return "APROBADO"
    if u == "LIQUIDADO":
        return "LIQUIDADO"
    if prestamo_estado_es_desistimiento(u):
        return "DESISTIMIENTO"
    return None


def estados_cartera_visibles_por_cedulas(
    db: Session, cedulas: Iterable[Optional[str]]
) -> Dict[str, List[str]]:
    """
    Por cédula cruda (recibo/bandeja): solo **APROBADO con cupo** en la columna Préstamo.

    DESISTIMIENTO / LIQUIDADO / APROBADO pagado al 100 % ($0 pendiente) no se listan.
    """
    from app.models.cliente import Cliente
    from app.models.prestamo import Prestamo
    from app.utils.cedula_almacenamiento import (
        expr_cedula_normalizada_para_comparar,
        normalizar_cedula_clave_cupo,
    )

    raws = [str(c).strip() for c in cedulas if str(c or "").strip()]
    if not raws:
        return {}
    raw_to_clave: Dict[str, str] = {}
    consulta: List[str] = []
    for raw in raws:
        clave = normalizar_cedula_clave_cupo(raw)
        if not clave:
            continue
        raw_to_clave[raw] = clave
        consulta.extend(_variantes_clave_cedula(clave))
    consulta = list(dict.fromkeys(consulta))
    if not consulta:
        return {}

    p_norm = expr_cedula_normalizada_para_comparar(Prestamo.cedula)
    c_norm = expr_cedula_normalizada_para_comparar(Cliente.cedula)
    rows = db.execute(
        select(p_norm, Prestamo.estado, c_norm, Prestamo.id)
        .select_from(Prestamo)
        .outerjoin(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            func.upper(func.trim(Prestamo.estado)).in_(_ESTADOS_SQL_COLUMNA),
            or_(p_norm.in_(consulta), c_norm.in_(consulta)),
        )
    ).all()

    prestamos_operativos = prestamo_ids_aprobados_con_cupo_recibos(
        db, [int(r[3]) for r in rows if r[3] is not None]
    )

    by_hit: Dict[str, set[str]] = {}
    consulta_set = set(consulta)
    for p_hit, estado, c_hit, pid in rows:
        canon = canon_estado_columna_prestamo(estado)
        if canon != "APROBADO":
            continue
        if pid is None or int(pid) not in prestamos_operativos:
            continue
        for hit in (p_hit, c_hit):
            hs = (str(hit) if hit is not None else "").strip()
            if hs and hs in consulta_set:
                by_hit.setdefault(hs, set()).add(canon)

    clave_to_estados: Dict[str, set[str]] = {}
    for clave in dict.fromkeys(raw_to_clave.values()):
        acc: set[str] = set()
        for v in _variantes_clave_cedula(clave):
            acc.update(by_hit.get(v) or ())
        if acc:
            clave_to_estados[clave] = acc

    out: Dict[str, List[str]] = {}
    for raw, clave in raw_to_clave.items():
        found = clave_to_estados.get(clave) or set()
        out[raw] = [e for e in ESTADOS_COLUMNA_PRESTAMO if e in found]
    return out


def attach_prestamo_estado_items(
    db: Session, items: List[Dict[str, Any]], *, cedula_key: str = "cedula"
) -> None:
    """Rellena ``prestamoEstado`` / ``prestamoEstados`` en cada dict (in-place)."""
    try:
        by_raw = estados_cartera_visibles_por_cedulas(
            db, [it.get(cedula_key) for it in items]
        )
    except Exception:
        logger.exception("[AUDITORIA_EMAIL] estados préstamo por cédula falló")
        by_raw = {}
    for it in items:
        raw = str(it.get(cedula_key) or "").strip()
        estados = list(by_raw.get(raw) or [])
        it["prestamoEstados"] = estados
        it["prestamoEstado"] = estados[0] if estados else None
