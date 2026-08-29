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
    found: set[str] = {
        k for k, n in contar_aprobados_por_claves_cupo(db, uniq).items() if int(n or 0) > 0
    }
    missing = [k for k in uniq if k not in found]
    if not missing:
        return found

    # La normalización del cupo solo quita guiones y espacios, mientras que la
    # clave que sale del OCR descarta todo lo que no sea VEGJ o dígito. Un
    # préstamo guardado como «V-30.771.164» no casaba con «V30771164» y el
    # comprobante se caía de la cola de Recibos sin dejar rastro. Este pase usa
    # la expresión alineada con Python; solo suma coincidencias, nunca las quita
    # (no se toca la del cupo porque también valida altas de préstamos).
    ced_norm = expr_cedula_normalizada_para_comparar(Prestamo.cedula)
    for raw in (
        db.execute(
            select(ced_norm)
            .where(Prestamo.estado == "APROBADO", ced_norm.in_(missing))
            .distinct()
        )
        .scalars()
        .all()
    ):
        k = (str(raw) if raw is not None else "").strip()
        if k in set(missing):
            found.add(k)
    missing = [k for k in missing if k not in found]
    if not missing:
        return found
    # Segunda vía: la cédula vive en Cliente y el préstamo apunta al cliente.
    # Se compara con la misma expresión normalizada, no con variantes literales,
    # para no volver a fallar por un punto o un prefijo suelto.
    cli_norm = expr_cedula_normalizada_para_comparar(Cliente.cedula)
    rows = (
        db.execute(
            select(Cliente.cedula)
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(Prestamo.estado == "APROBADO", cli_norm.in_(missing))
            .distinct()
        )
        .scalars()
        .all()
    )
    missing_set = set(missing)
    for raw in rows:
        k = normalizar_cedula_clave_cupo(raw)
        if k and k in missing_set:
            found.add(k)
    return found


def cedula_tiene_prestamo_aprobado(db: Session, cedula: Optional[str]) -> bool:
    """Versión de una sola cédula, tolerante a puntos, guiones y prefijo suelto."""
    from app.utils.cedula_almacenamiento import normalizar_cedula_clave_cupo

    clave = normalizar_cedula_clave_cupo(cedula or "")
    if not clave:
        return False
    return clave in claves_con_prestamo_aprobado(db, [clave])
