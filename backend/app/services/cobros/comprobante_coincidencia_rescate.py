# -*- coding: utf-8 -*-
"""
Rescate determinístico post-Gemini para auto-aprobación Cobros.

No relaja OCR borroso ni duplicados: solo corrige falsos negativos cuando
monto + serial coinciden de forma verificable en la extracción de imagen.

Binance (comprobante digital): con control_usuario_operaciones=true
(operaciones@ arriba del ID de orden), monto+serial determinísticos bastan;
fecha/cédula/banco no bloquean el rescate.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional, Set, Tuple

from app.services.pagos_gmail.parse_campos_comprobante import (
    ocr_borroso_indicado_en_texto,
    parse_monto_comprobante,
    clave_numero_operacion_canonico,
    PAGOS_NA,
)

logger = logging.getLogger(__name__)

# Columnas que Gemini puede marcar pero no impiden rescate en Binance digital.
_COLUMNAS_NO_CRITICAS_BINANCE = frozenset(
    {
        "fecha pago",
        "fecha de pago",
        "cedula",
        "cédula",
        "banco",
        "moneda",
    }
)

# Columnas cosméticas en comprobantes bancarios tradicionales.
_COLUMNAS_NO_CRITICAS_GENERAL = frozenset(
    {
        "fecha pago",
        "fecha de pago",
        "moneda",
    }
)

_COL_MONTO = frozenset({"monto"})
_COL_SERIAL = frozenset({"n operacion", "nº operacion", "numero operacion", "número operacion"})
_COL_CEDULA = frozenset({"cedula", "cédula"})
_COL_BANCO = frozenset({"banco"})


def _norm_col(nombre: str) -> str:
    t = " ".join((nombre or "").strip().lower().split())
    return t.replace("ó", "o").replace("º", "o").replace("n o operacion", "n operacion")


def columnas_comentario_gemini(comentario: Optional[str]) -> Set[str]:
    """Nombres de columna normalizados desde comentario Gemini."""
    raw = (comentario or "").strip()
    if not raw:
        return set()
    if raw.strip().lower() == "usuario operaciones":
        return {"usuario operaciones"}
    parts: list[str] = []
    for chunk in re.split(r"[,/]", raw):
        p = _norm_col(chunk)
        if p:
            parts.append(p)
    return set(parts)


def _cedula_form_norm(tipo: str, numero: str) -> str:
    t = (tipo or "").strip().upper()
    n = (numero or "").strip()
    if not n:
        return ""
    num = n.lstrip("0") or "0"
    if t in ("V", "E", "G", "J"):
        return f"{t}{num}"
    return f"{t}{num}".replace("-", "").replace(" ", "").upper()


def _cedula_extraccion_norm(raw: Any) -> str:
    s = str(raw or "").strip().upper().replace("-", "").replace(" ", "")
    if not s or s in (PAGOS_NA, "N/A", "NA"):
        return ""
    if len(s) >= 2 and s[0] in ("V", "E", "G", "J") and s[1:].isdigit():
        return s[0] + (s[1:].lstrip("0") or "0")
    if s.isdigit():
        return "V" + (s.lstrip("0") or "0")
    return s


def _monedas_equivalentes(a: Optional[str], b: Optional[str]) -> bool:
    def _n(m: Optional[str]) -> str:
        u = (m or "BS").strip().upper()
        return "USD" if u in ("USD", "USDT") else u

    return _n(a) == _n(b)


def montos_coinciden_determinista(
    form_monto: Any,
    ext_monto: Any,
    *,
    moneda_form: Optional[str] = None,
    moneda_ext: Optional[str] = None,
    institucion: Optional[str] = None,
    tolerancia: float = 0.02,
) -> bool:
    mf = parse_monto_comprobante(
        form_monto, moneda=moneda_form, institucion=institucion
    )
    me = parse_monto_comprobante(
        ext_monto, moneda=moneda_ext or moneda_form, institucion=institucion
    )
    if mf is None or me is None:
        return False
    return abs(mf - me) <= tolerancia


def seriales_coinciden_determinista(
    form_op: Any,
    ext_op: Any,
    *,
    institucion: Optional[str] = None,
) -> bool:
    fa = (form_op or "").strip()
    fb = (ext_op or "").strip()
    if not fa or not fb:
        return False
    if fa.upper() in (PAGOS_NA, "N/A") or fb.upper() in (PAGOS_NA, "N/A"):
        return False
    ka = clave_numero_operacion_canonico(fa, institucion=institucion)
    kb = clave_numero_operacion_canonico(fb, institucion=institucion)
    if ka and kb and ka == kb:
        return True
    return fa.replace(" ", "").replace("-", "") == fb.replace(" ", "").replace("-", "")


def _instituciones_equivalentes(form_inst: Any, ext_inst: Any) -> bool:
    a = (form_inst or "").strip().lower()
    b = (ext_inst or "").strip().lower()
    if not a or not b:
        return True
    if a == b:
        return True
    if "binance" in a and "binance" in b:
        return True
    recibo = {"recibo", "recibos"}
    if a in recibo and b in recibo:
        return True
    try:
        from app.services.pagos_gmail.gemini_service import _canonical_institucion_escaner

        return _canonical_institucion_escaner(form_inst).lower() == _canonical_institucion_escaner(
            ext_inst
        ).lower()
    except Exception:
        return a in b or b in a


def _extraccion_util(extraccion: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not extraccion or not isinstance(extraccion, dict):
        return {}
    return extraccion


def _columna_resuelta_determinista(
    col: str,
    form_compare: Dict[str, Any],
    extraccion: Dict[str, Any],
) -> bool:
    inst = form_compare.get("institucion_financiera")
    if col in _COL_MONTO:
        return montos_coinciden_determinista(
            form_compare.get("monto"),
            extraccion.get("monto"),
            moneda_form=form_compare.get("moneda"),
            moneda_ext=extraccion.get("moneda"),
            institucion=inst,
        )
    if col in _COL_SERIAL:
        return seriales_coinciden_determinista(
            form_compare.get("numero_operacion"),
            extraccion.get("numero_operacion"),
            institucion=inst,
        )
    if col in _COL_CEDULA:
        cf = _cedula_form_norm(
            str(form_compare.get("tipo_cedula") or ""),
            str(form_compare.get("numero_cedula") or ""),
        )
        ce = _cedula_extraccion_norm(extraccion.get("cedula_pagador"))
        if not ce:
            return True
        return bool(cf and ce and cf == ce)
    if col in _COL_BANCO:
        return _instituciones_equivalentes(
            form_compare.get("institucion_financiera"),
            extraccion.get("institucion_financiera"),
        )
    if col in _COLUMNAS_NO_CRITICAS_GENERAL or col in _COLUMNAS_NO_CRITICAS_BINANCE:
        return True
    if col == "moneda":
        return _monedas_equivalentes(
            form_compare.get("moneda"), extraccion.get("moneda")
        )
    return False


def evaluar_rescate_coincidencia_determinista(
    form_compare: Dict[str, Any],
    *,
    coincide: bool,
    comentario: str,
    extraccion: Optional[Dict[str, Any]],
    control_usuario_operaciones: Optional[bool] = None,
) -> Tuple[bool, str]:
    """
    True si conviene elevar coincide_exacto a true sin debilitar OCR.

    Requisitos comunes:
    - Gemini dijo false (si ya true, no aplica).
    - Sin indicio de OCR borroso en comentario.
    - Extracción con monto y serial legibles y coincidentes con formulario.

    Binance: además exige control_usuario_operaciones=true.
    """
    if coincide:
        return False, ""
    com = (comentario or "").strip()
    if com.lower().startswith("usuario operaciones"):
        return False, "binance_control_operaciones"
    inst = (form_compare.get("institucion_financiera") or "").strip()
    es_binance = "binance" in inst.lower()
    if ocr_borroso_indicado_en_texto(com, ignorar_fecha=es_binance):
        return False, "ocr_borroso"

    ext = _extraccion_util(extraccion)

    if es_binance and control_usuario_operaciones is not True:
        return False, "binance_sin_control"

    monto_ok = montos_coinciden_determinista(
        form_compare.get("monto"),
        ext.get("monto"),
        moneda_form=form_compare.get("moneda"),
        moneda_ext=ext.get("moneda"),
        institucion=inst,
    )
    serial_ok = seriales_coinciden_determinista(
        form_compare.get("numero_operacion"),
        ext.get("numero_operacion"),
        institucion=inst,
    )
    if not monto_ok or not serial_ok:
        return False, "criticos_no_verificables"

    cols = columnas_comentario_gemini(com)
    if es_binance:
        pendientes = cols - _COLUMNAS_NO_CRITICAS_BINANCE - {"usuario operaciones"}
        for col in pendientes:
            if not _columna_resuelta_determinista(col, form_compare, ext):
                return False, f"binance_columna_{col}"
        logger.info(
            "[COBROS] Rescate determinístico Binance: control operaciones + monto/serial OK"
        )
        return True, "binance_digital"

    if not cols:
        logger.info(
            "[COBROS] Rescate determinístico: Gemini false sin columnas pero monto/serial OK"
        )
        return True, "sin_columnas_criticas"

    for col in cols:
        if col in _COLUMNAS_NO_CRITICAS_GENERAL:
            continue
        if not _columna_resuelta_determinista(col, form_compare, ext):
            return False, f"columna_{col}"

    logger.info(
        "[COBROS] Rescate determinístico: falsos negativos Gemini corregidos (%s)",
        ",".join(sorted(cols)) or "vacío",
    )
    return True, "deterministico"
