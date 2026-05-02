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


def _database_url_es_postgresql() -> bool:
    """True si la URL de BD apunta a PostgreSQL (misma heurística que ``app.core.database``)."""
    try:
        from app.core.config import settings

        u = (getattr(settings, "DATABASE_URL", None) or "").strip().lower()
    except Exception:
        return False
    return u.startswith("postgresql") or u.startswith("postgres://")


def expr_cedula_normalizada_para_comparar(column) -> ColumnElement:
    """
    Expresión SQL alineada con ``texto_cedula_comparable_bd`` (mayúsculas, solo V/E/G/J y dígitos).

    En PostgreSQL se eliminan además otros separadores vía ``regexp_replace``; en SQLite (p. ej. tests)
    se aplica solo guión, punto y espacio como antes.
    """
    x = func.upper(func.trim(func.coalesce(column, "")))
    x = func.replace(x, "-", "")
    x = func.replace(x, ".", "")
    x = func.replace(x, " ", "")
    if _database_url_es_postgresql():
        return func.regexp_replace(x, "[^VEGJ0-9]", "", "g")
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


def resolver_cedula_almacenada_en_clientes(
    db: Session, cedula_raw: Optional[str]
) -> Optional[str]:
    """
    Devuelve la cedula EXACTA como esta guardada en `clientes` para `cedula_raw`, o None.

    Maneja el caso real de carga masiva donde el origen trae solo digitos (p.ej. `22621583`)
    pero `clientes.cedula` esta almacenada con prefijo (`V22621583`). Probamos en este orden:
      1) la cedula limpia tal cual (post-upper/trim)
      2) si arranca con digito, los candidatos `V<digits>`, `E<digits>`, `J<digits>`, `G<digits>`

    Devolver el valor exacto evita violar `fk_pagos_cedula` al insertar `pagos`.
    """
    from app.models.cliente import Cliente

    cedula_norm = normalizar_cedula_almacenamiento(cedula_raw) or ""
    if not cedula_norm:
        return None

    candidatos: list[str] = [cedula_norm]
    if cedula_norm[0].isdigit():
        for prefijo in ("V", "E", "J", "G"):
            candidatos.append(f"{prefijo}{cedula_norm}")

    for cand in candidatos:
        existente = db.execute(
            select(Cliente.cedula).where(Cliente.cedula == cand).limit(1)
        ).scalar_one_or_none()
        if existente:
            return existente
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
