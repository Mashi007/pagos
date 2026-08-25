"""Normalizacion de cedula para almacenamiento: trim + mayusculas."""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement


def _anteponer_v_si_solo_digitos(s: str) -> str:
    """Misma regla que validate_cedula / _cedula_clave_comparacion_clientes: 6-11 dígitos → V+."""
    if re.fullmatch(r"\d{6,11}", s or ""):
        return "V" + s
    return s or ""


def texto_cedula_comparable_bd(value: Optional[str]) -> str:
    """
    Misma semantica que expr_cedula_normalizada_para_comparar pero en Python
    (batch, comparaciones en memoria). NFKC, mayusculas, solo VEGJ y digitos.
    Si quedan solo 6-11 dígitos, antepone V (evita duplicar 30771164 vs V30771164).
    """
    if value is None:
        return ""
    s = unicodedata.normalize("NFKC", str(value).strip()).upper()
    s = re.sub(r"[\u200B-\u200D\uFEFF]", "", s)
    s = re.sub(r"[^VEGJ0-9]", "", s)
    return _anteponer_v_si_solo_digitos(s)


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

    En PostgreSQL se eliminan además otros separadores vía ``regexp_replace`` y, si el
    resultado es solo 6-11 dígitos, antepone V (misma regla que validate_cedula).
    En SQLite (tests) se aplica solo guión/punto/espacio sin anteponer V en SQL.
    """
    from sqlalchemy import case, literal

    x = func.upper(func.trim(func.coalesce(column, "")))
    x = func.replace(x, "-", "")
    x = func.replace(x, ".", "")
    x = func.replace(x, " ", "")
    if not _database_url_es_postgresql():
        return x
    x = func.regexp_replace(x, "[^VEGJ0-9]", "", "g")
    return case(
        (x.op("~")(literal(r"^[0-9]{6,11}$")), func.concat(literal("V"), x)),
        else_=x,
    )


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
    Solo digitos 6-11 → antepone V (30771164 ≡ V30771164).
    """
    return texto_cedula_comparable_bd(value)


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
    """E/V: 1 APROBADO por clave; J: varios APROBADO por clave. None si prefijo invalido."""
    if prefijo in ("E", "V"):
        return 1
    if prefijo == "J":
        return 99
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


class CedulaPagoFkError(ValueError):
    """Cédula de pago no resoluble contra `clientes` (FK fk_pagos_cedula)."""


def asegurar_cedula_pago_para_fk(
    db: Session,
    *,
    cedula_raw: Optional[str],
    prestamo_id: Optional[int],
) -> Optional[str]:
    """
    Devuelve la cédula exacta en `clientes` para `pagos.cedula` (FK fk_pagos_cedula).

    Con `prestamo_id`, prioriza la del préstamo/cliente. Vacío sin préstamo → None.
    Si hay valor que no existe en clientes, lanza CedulaPagoFkError.
    """
    from app.models.cliente import Cliente
    from app.models.prestamo import Prestamo

    cedula_solicitada = normalizar_cedula_almacenamiento(cedula_raw)

    if prestamo_id:
        prestamo = db.get(Prestamo, prestamo_id)
        if prestamo:
            cli_cedula: Optional[str] = None
            if prestamo.cliente_id:
                cli = db.get(Cliente, prestamo.cliente_id)
                if cli and (cli.cedula or "").strip():
                    cli_cedula = (cli.cedula or "").strip()
            for candidato in (
                (prestamo.cedula or "").strip() or None,
                cli_cedula,
            ):
                if not candidato:
                    continue
                res = resolver_cedula_almacenada_en_clientes(db, candidato)
                if res:
                    return res
                existente = db.execute(
                    select(Cliente.cedula).where(Cliente.cedula == candidato).limit(1)
                ).scalar_one_or_none()
                if existente:
                    return existente

    if not cedula_solicitada:
        return None

    alinear_cedulas_clientes_existentes(db, [cedula_solicitada])
    res = resolver_cedula_almacenada_en_clientes(db, cedula_solicitada)
    if res:
        return res

    cli_row = db.execute(
        select(Cliente.cedula)
        .where(func.upper(Cliente.cedula) == cedula_solicitada)
        .limit(1)
    ).scalar_one_or_none()
    if cli_row:
        return cli_row

    raise CedulaPagoFkError(
        f"La cédula «{cedula_solicitada}» no existe en clientes. "
        "Asigne un crédito válido o corrija el documento del cliente en CRM."
    )


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
