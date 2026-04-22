"""
Cédulas autorizadas para reportar pagos en Bolívares (tabla cedulas_reportar_bs).

Punto único de articulación entre:
- Formulario público / infopagos (cobros_publico)
- Listado y edición admin (cobros)
- Carga Excel y alta manual (pagos)

Incluye la misma normalización que clientes/pagos reportados (ceros a la izquierda en el número)
y variantes V+E+J+G+número / solo número para que coincidan lista BD y datos del reporte.
"""
from __future__ import annotations

from typing import Optional, Set, Union

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cedula_reportar_bs import CedulaReportarBs

from app.services.tasa_cambio_service import normalizar_fuente_tasa


def normalize_cedula_lookup_key(cedula: str) -> str:
    """
    Normaliza cédula para comparar listas y reportes (igual que cobros._normalize_cedula_for_client_lookup).
    Sin guiones/espacios, mayúsculas; sin ceros a la izquierda en el número (V08752971 -> V8752971).
    """
    s = (cedula or "").replace("-", "").replace(" ", "").strip().upper()
    if not s:
        return s
    if len(s) >= 2 and s[0] in ("V", "E", "J", "G") and s[1:].isdigit():
        num = s[1:].lstrip("0") or "0"
        return s[0] + num
    return s


def expand_cedula_variants_for_bs_list(norm: str) -> Set[str]:
    """Variantes de una cédula ya normalizada para cruzar con distintas formas en BD o en formularios."""
    out: Set[str] = set()
    if not norm:
        return out
    out.add(norm)
    if len(norm) >= 2 and norm[0] in ("V", "E", "J", "G") and norm[1:].isdigit():
        out.add(norm[1:])
    if len(norm) >= 6 and norm.isdigit():
        num = norm.lstrip("0") or "0"
        out.add(num)
        out.add("V" + num)
    return out


def load_autorizados_bs_claves(db: Session) -> frozenset[str]:
    """
    Conjunto de todas las claves reconocidas como autorizadas para Bs (derivadas de cedulas_reportar_bs).
    Incluye formas normalizadas y variantes (solo dígitos, V+dígitos) por fila.
    """
    rows = db.execute(select(CedulaReportarBs.cedula)).scalars().all()
    out: Set[str] = set()
    for c in rows:
        if c is None:
            continue
        raw = str(c).strip().upper().replace("-", "").replace(" ", "").replace(".", "")
        if not raw:
            continue
        norm = normalize_cedula_lookup_key(raw)
        if not norm:
            continue
        out.update(expand_cedula_variants_for_bs_list(norm))
    return frozenset(out)


def cedula_coincide_autorizados_bs(cedula_norm: str, autorizados: Union[set[str], frozenset[str]]) -> bool:
    """True si la cédula normalizada del reporte coincide con alguna clave autorizada."""
    if not cedula_norm:
        return False
    candidatos = {cedula_norm} | expand_cedula_variants_for_bs_list(cedula_norm)
    return bool(candidatos & autorizados)


def cedula_autorizada_para_bs(db: Session, cedula_sin_guion: str) -> bool:
    """
    Indica si la cédula (como string tipo V12345678 o valor_formateado sin guión) puede usar moneda Bs.
    Carga la lista desde BD en cada llamada; en endpoints con muchas filas preferir load_autorizados_bs_claves una vez.
    """
    raw = str(cedula_sin_guion or "").strip().upper().replace("-", "").replace(" ", "").replace(".", "")
    if not raw:
        return False
    norm = normalize_cedula_lookup_key(raw)
    if not norm:
        return False
    claves = load_autorizados_bs_claves(db)
    return cedula_coincide_autorizados_bs(norm, claves)


def obtener_fuente_tasa_lista_bs(db: Session, cedula_sin_guion: str) -> Optional[str]:
    """
    Si la cédula está autorizada para Bs, devuelve fuente_tasa_cambio normalizada (bcv|euro|binance).
    Si no está en lista, None. La tabla suele ser pequeña: cruza variantes V/dígitos en memoria.
    """
    raw = str(cedula_sin_guion or "").strip().upper().replace("-", "").replace(" ", "").replace(".", "")
    if not raw:
        return None
    norm_in = normalize_cedula_lookup_key(raw)
    if not norm_in:
        return None
    candidatos_in = {norm_in} | expand_cedula_variants_for_bs_list(norm_in)
    rows = db.execute(select(CedulaReportarBs)).scalars().all()
    for r in rows:
        rk = normalize_cedula_lookup_key(str(r.cedula or ""))
        if not rk:
            continue
        candidatos_row = {rk} | expand_cedula_variants_for_bs_list(rk)
        if candidatos_in & candidatos_row:
            return normalizar_fuente_tasa(getattr(r, "fuente_tasa_cambio", None))
    return None


def normalize_cedula_para_almacenar_lista_bs(cedula: str) -> Optional[str]:
    """
    Normaliza cédula para guardar en cedulas_reportar_bs (clave canónica).
    Letra V/E/J/G + 6–11 dígitos (tras quitar ceros a la izquierda del número); solo dígitos se guardan como V+número.
    Retorna None si el formato no es válido para la lista.
    """
    if not cedula or not isinstance(cedula, str):
        return None
    s = cedula.strip().upper().replace("-", "").replace(" ", "").replace(".", "")
    if not s:
        return None
    if s.isdigit():
        if not (6 <= len(s) <= 11):
            return None
        num = s.lstrip("0") or "0"
        if not (6 <= len(num) <= 11):
            return None
        return "V" + num
    if len(s) >= 2 and s[0] in ("V", "E", "J", "G") and s[1:].isdigit():
        num = s[1:].lstrip("0") or "0"
        if not (6 <= len(num) <= 11):
            return None
        return s[0] + num
    return None
