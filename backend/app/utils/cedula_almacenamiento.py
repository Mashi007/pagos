"""Normalizacion de cedula para almacenamiento: trim + mayusculas."""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement


def texto_cedula_comparable_bd(value: Optional[str]) -> str:
    """
    Misma semantica que expr_cedula_normalizada_para_comparar pero en Python
    (batch, comparaciones en memoria). NFKC, mayusculas, solo VEGJ y digitos.
    """
    if value is None:
        return ""
    s = unicodedata.normalize("NFKC", str(value).strip()).upper()
    s = re.sub(r"[\u200B-\u200D\uFEFF]", "", s)
    return re.sub(r"[^VEGJ0-9]", "", s)


def expr_cedula_normalizada_para_comparar(column) -> ColumnElement:
    """
    Expresión SQL para comparar cédulas con la misma lógica que validate_cedula / _cedula_lookup:
    mayúsculas y sin guión, punto ni espacio (ej. V-20.235.335 y V20235335 coinciden).
    """
    x = func.upper(column)
    x = func.replace(x, "-", "")
    x = func.replace(x, ".", "")
    x = func.replace(x, " ", "")
    return x


def normalizar_cedula_almacenamiento(value: Optional[str]) -> Optional[str]:
    """Devuelve la cedula lista para persistir: strip + MAYUSCULAS. None si no hay valor."""
    if value is None:
        return None
    s = str(value).strip()
    return s.upper() if s else None


def normalizar_cedula_clave_cupo(value: Optional[str]) -> str:
    """
    Clave canonica para cupo de prestamos APROBADO por documento: trim, mayusculas,
    sin guiones ni espacios (ej. V-123 y V123 coinciden).
    """
    if value is None:
        return ""
    s = str(value).strip().upper().replace("-", "").replace(" ", "")
    return s


def prefijo_politica_cupo_aprobados(clave: str) -> Optional[str]:
    """
    Primer caracter de la clave normalizada. Solo E, V, J son validos para cupo.
    None si vacio o prefijo no permitido.
    """
    if not clave:
        return None
    c0 = clave[0]
    if c0 in ("E", "V", "J"):
        return c0
    return None


def max_aprobados_permitidos_por_prefijo(prefijo: Optional[str]) -> Optional[int]:
    """E/V: 1 APROBADO por clave; J: hasta 5 APROBADO por clave. None si prefijo invalido."""
    if prefijo in ("E", "V"):
        return 1
    if prefijo == "J":
        return 5
    return None


def alinear_cedulas_clientes_existentes(db: Session, cedulas: Iterable[Optional[str]]) -> None:
    """
    Pone clientes.cedula en mayusculas cuando coincide en mayusculas con la clave canonica.
    Evita violar fk_pagos_cedula al insertar pagos con cedula en mayusculas.
    """
    from app.models.cliente import Cliente

    norms = {str(c).strip().upper() for c in cedulas if c is not None and str(c).strip()}
    if not norms:
        return
    for cn in norms:
        rows = db.execute(select(Cliente).where(func.upper(Cliente.cedula) == cn)).scalars().all()
        for r in rows:
            if (r.cedula or "") != cn:
                r.cedula = cn
    db.flush()
