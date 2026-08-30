"""Cupo de prestamos APROBADO por cedula (politica E/V max 1, J varios, solo prefijos E V J)."""
from __future__ import annotations

from typing import Iterable, Optional

from fastapi import HTTPException
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.utils.cedula_almacenamiento import (
    max_aprobados_permitidos_por_prefijo,
    normalizar_cedula_clave_cupo,
    prefijo_politica_cupo_aprobados,
)

# Expresión única en SQL para alinear conteo unitario y por lotes (PostgreSQL).
# Solo dígitos 6-11 → antepone V (30771164 ≡ V30771164).
_CEDULA_NORM_INNER = (
    "REPLACE(REPLACE(REPLACE(UPPER(TRIM(COALESCE(p.cedula, ''))), '-', ''), ' ', ''), '.', '')"
)
_CEDULA_NORM_SQL = (
    f"CASE WHEN {_CEDULA_NORM_INNER} ~ '^[0-9]{{6,11}}$' "
    f"THEN 'V' || {_CEDULA_NORM_INNER} "
    f"ELSE {_CEDULA_NORM_INNER} END"
)


def contar_aprobados_misma_clave_cupo(
    db: Session,
    clave: str,
    *,
    exclude_prestamo_id: Optional[int] = None,
) -> int:
    """Cuenta prestamos APROBADO con la misma clave (normalizada en SQL, alineada con Python)."""
    q = f"""
        SELECT COUNT(*) FROM prestamos p
        WHERE p.estado = 'APROBADO'
          AND {_CEDULA_NORM_SQL} = :clave
    """
    params: dict = {"clave": clave}
    if exclude_prestamo_id is not None:
        q += " AND p.id != :ex"
        params["ex"] = exclude_prestamo_id
    return int(db.execute(text(q), params).scalar() or 0)


def contar_aprobados_por_claves_cupo(db: Session, claves: Iterable[str]) -> dict[str, int]:
    """
    Una sola consulta: conteos de préstamos APROBADO por cédula normalizada.
    Misma normalización que ``contar_aprobados_misma_clave_cupo`` (sin exclude_prestamo_id).
    Las claves inexistentes en cartera no aparecen en el dict (usar .get(clave, 0)).
    """
    uniq = list(dict.fromkeys(c for c in claves if c))
    if not uniq:
        return {}
    q = text(
        f"""
        SELECT {_CEDULA_NORM_SQL} AS k, COUNT(*)::int AS n
        FROM prestamos p
        WHERE p.estado = 'APROBADO'
          AND {_CEDULA_NORM_SQL} IN :claves
        GROUP BY 1
        """
    ).bindparams(bindparam("claves", expanding=True))
    rows = db.execute(q, {"claves": uniq}).all()
    out: dict[str, int] = {}
    for k, n in rows:
        if k is None:
            continue
        ks = str(k).strip()
        if ks:
            out[ks] = int(n or 0)
    return out


def validar_cupo_nuevo_prestamo_aprobado(
    db: Session,
    cedula_prestamo: str,
    *,
    exclude_prestamo_id: Optional[int] = None,
) -> None:
    """
    Bloquea alta o paso a APROBADO si se excede cupo o la cedula no cumple prefijo E/V/J.
    Raises HTTPException 400.
    """
    clave = normalizar_cedula_clave_cupo(cedula_prestamo)
    pref = prefijo_politica_cupo_aprobados(clave)
    max_n = max_aprobados_permitidos_por_prefijo(pref)
    if max_n is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cedula no valida para cupo de prestamos APROBADO: vacia o prefijo no permitido "
                "(solo documentos que tras normalizar guiones/espacios empiezan por E, V o J)."
            ),
        )
    n = contar_aprobados_misma_clave_cupo(db, clave, exclude_prestamo_id=exclude_prestamo_id)
    if n >= max_n:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cupo de prestamos APROBADO por cedula excedido: prefijo {pref} permite maximo {max_n} "
                f"con la misma cedula normalizada; hay {n} en cartera."
            ),
        )


def claves_cedula_con_n_prestamos_en_cartera(
    db: Session,
    *,
    min_prestamos: int = 2,
) -> set[str]:
    """
    Cédulas normalizadas con al menos ``min_prestamos`` filas en ``prestamos`` (todos los estados).
    Misma expresión SQL que cupo/auditoría de cartera.
    """
    if min_prestamos < 2:
        min_prestamos = 2
    q = f"""
        WITH agr AS (
          SELECT {_CEDULA_NORM_SQL} AS ced_norm, COUNT(*)::int AS n
          FROM prestamos p
          GROUP BY 1
        )
        SELECT ced_norm FROM agr
        WHERE ced_norm IS NOT NULL
          AND TRIM(BOTH FROM ced_norm::text) <> ''
          AND n >= :min_n
    """
    rows = db.execute(text(q), {"min_n": int(min_prestamos)}).all()
    return {str(r[0]).strip() for r in rows if r[0]}
