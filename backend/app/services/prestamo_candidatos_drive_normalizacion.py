"""
Normalización unificada para snapshot/guardado de candidatos Drive.

Centraliza reglas de cédula, monto, cuotas, modalidad y fecha Q para evitar
divergencias entre refresco de snapshot, validación y guardado.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple


def cell_str(v: object) -> str:
    if v is None:
        return ""
    return str(v).strip()


def normalizar_cedula_cmp_drive(raw: str) -> str:
    """
    Devuelve cédula comparable en formato VEJG + dígitos.
    Reglas:
    - Si aparece un patrón válido dentro del texto, usa el primero (ej: teléfonos + V123...).
    - Si es numérica pura (6-11), asume V.
    - Corrige prefijos repetidos (VV123 -> V123).
    """
    s = re.sub(r"[^A-Z0-9]", "", (raw or "").upper())
    if not s:
        return ""
    m = re.search(r"(V|E|J|G)\d{6,11}", s)
    if m:
        return m.group(0)
    m2 = re.match(r"^(V|E|J|G){2,}(\d{6,11})$", s)
    if m2:
        return f"{m2.group(1)}{m2.group(2)}"
    if re.match(r"^\d{6,11}$", s):
        return f"V{s}"
    return ""


def parse_decimal_monto_drive(raw: str) -> Optional[Decimal]:
    t = (raw or "").strip().replace(" ", "")
    for sym in ("$", "€", "Bs.", "Bs", "USD", "VES"):
        t = re.sub(re.escape(sym), "", t, flags=re.I).strip()
    if not t:
        return None
    last_comma = t.rfind(",")
    last_dot = t.rfind(".")
    if "," in t and "." in t:
        if last_comma > last_dot:
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
    elif "," in t:
        t = t.replace(",", ".")
    try:
        d = Decimal(t)
        return d if d > 0 else None
    except (InvalidOperation, ValueError):
        return None


def parse_numero_cuotas_drive(raw: str) -> Optional[int]:
    t = re.sub(r"\D", "", raw or "")
    if not t:
        return None
    try:
        n = int(t)
        return n if 1 <= n <= 50 else None
    except ValueError:
        return None


def normalizar_modalidad_drive(raw: str) -> Optional[str]:
    t = cell_str(raw).upper()
    if not t:
        return None
    if "QUINCENA" in t:
        return "QUINCENAL"
    if "SEMANA" in t:
        return "SEMANAL"
    if "MENS" in t or "MES" in t:
        return "MENSUAL"
    if t in {"MENSUAL", "QUINCENAL", "SEMANAL"}:
        return t
    return None


def parse_fecha_q_iso_y_ambigua(raw: str) -> Tuple[Optional[date], bool]:
    s = cell_str(raw)
    if not s:
        return None, False
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        try:
            return date.fromisoformat(s), False
        except ValueError:
            return None, False
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s)
    if not m:
        return None, False
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    amb = 1 <= d <= 12 and 1 <= mo <= 12
    if amb:
        return None, True
    try:
        return date(y, mo, d), False
    except ValueError:
        return None, False
