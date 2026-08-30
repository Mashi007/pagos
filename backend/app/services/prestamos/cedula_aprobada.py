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

from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session


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
