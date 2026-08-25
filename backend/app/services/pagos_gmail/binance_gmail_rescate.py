# -*- coding: utf-8 -*-
"""
Rescate Binance plantilla C (Gmail / Actualizaciones): misma lógica que Cobros reportados.

Si Gemini marcó control_usuario_operaciones=false pero monto+serial son válidos,
re-ejecuta compare_form_with_image (con rescate determinístico) sobre la imagen.
Solo eleva a control=true si coincide_exacto (incl. operaciones@ + monto/serial).
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

from app.services.pagos_gmail.plantilla_abcd_proceso_negocio import (
    binance_control_usuario_operaciones_cumple,
)
from app.services.cobros.comprobante_coincidencia_rescate import (
    montos_coinciden_determinista,
    seriales_coinciden_determinista,
)

logger = logging.getLogger(__name__)


def _cedula_columna_a_form(cedula_columna: str) -> Tuple[str, str]:
    s = (cedula_columna or "").strip().upper().replace("-", "").replace(" ", "")
    if len(s) >= 2 and s[0] in ("V", "E", "G", "J") and s[1:].isdigit():
        num = s[1:].lstrip("0") or "0"
        return s[0], num
    if s.isdigit():
        return "V", s.lstrip("0") or "0"
    return "V", s


def _form_compare_desde_campos_gmail_c(
    *,
    monto_str: str,
    numero_referencia: str,
    cedula_columna: str,
    fecha_pago_str: str,
) -> dict[str, Any]:
    tipo, num = _cedula_columna_a_form(cedula_columna)
    return {
        "fecha_pago": (fecha_pago_str or "").strip(),
        "institucion_financiera": "BINANCE",
        "numero_operacion": (numero_referencia or "").strip(),
        "monto": (monto_str or "").strip(),
        "moneda": "USDT",
        "tipo_cedula": tipo,
        "numero_cedula": num,
    }


def _campos_criticos_gmail_c_validos(
    monto_str: str,
    numero_referencia: str,
) -> bool:
    m = (monto_str or "").strip()
    r = (numero_referencia or "").strip()
    if not m or not r:
        return False
    if not seriales_coinciden_determinista(r, r, institucion="BINANCE"):
        return False
    mf = montos_coinciden_determinista(m, m, moneda_form="USDT", moneda_ext="USDT")
    return bool(mf)


def cargar_comprobante_bytes_gmail(
    db: Any,
    comprobante_imagen_id: Optional[str],
) -> Tuple[Optional[bytes], str]:
    cid = (comprobante_imagen_id or "").strip()
    if not cid or db is None:
        return None, "comprobante.jpg"
    try:
        from app.models.pago_comprobante_imagen import PagoComprobanteImagen

        row = db.get(PagoComprobanteImagen, cid)
        if row is None or not getattr(row, "imagen_data", None):
            return None, "comprobante.jpg"
        ct = (getattr(row, "content_type", None) or "image/jpeg").strip().lower()
        ext = "pdf" if "pdf" in ct else "jpg"
        return bytes(row.imagen_data), f"comprobante.{ext}"
    except Exception:
        logger.exception("[PAGOS_GMAIL] Binance rescate: no se pudo cargar comprobante %s", cid)
        return None, "comprobante.jpg"


def resolver_control_usuario_operaciones_gmail_plantilla_c(
    *,
    control_actual: Optional[str],
    monto_str: str,
    numero_referencia: str,
    cedula_columna: str,
    fecha_pago_str: str,
    image_bytes: Optional[bytes],
    filename: str = "comprobante.jpg",
) -> Tuple[str, bool, str]:
    """
    Devuelve (control_resuelto, rescate_aplicado, motivo_log).

    No debilita OCR: solo compare_form_with_image + rescate determinístico Cobros.
    """
    if binance_control_usuario_operaciones_cumple(control_actual):
        return (str(control_actual or "true").strip().lower(), False, "ya_ok")

    if not _campos_criticos_gmail_c_validos(monto_str, numero_referencia):
        return ((control_actual or "false").strip().lower(), False, "criticos_invalidos")

    if not image_bytes:
        return ((control_actual or "false").strip().lower(), False, "sin_imagen")

    form_compare = _form_compare_desde_campos_gmail_c(
        monto_str=monto_str,
        numero_referencia=numero_referencia,
        cedula_columna=cedula_columna,
        fecha_pago_str=fecha_pago_str,
    )

    try:
        from app.services.pagos_gmail.gemini_service import compare_form_with_image

        result = compare_form_with_image(form_compare, image_bytes, filename)
    except Exception as exc:
        logger.warning(
            "[PAGOS_GMAIL] Binance rescate compare falló ref=%s: %s",
            (numero_referencia or "")[:24],
            str(exc)[:200],
        )
        return ((control_actual or "false").strip().lower(), False, "compare_error")

    if not result.get("coincide_exacto"):
        com = (result.get("comentario") or "").strip()
        logger.info(
            "[PAGOS_GMAIL] Binance rescate no aplica ref=%s comentario=%s",
            (numero_referencia or "")[:24],
            com[:120],
        )
        return ((control_actual or "false").strip().lower(), False, "compare_no_coincide")

    logger.info(
        "[PAGOS_GMAIL] Binance rescate plantilla C OK ref=%s monto=%s",
        (numero_referencia or "")[:24],
        (monto_str or "")[:16],
    )
    return ("true", True, "compare_binance_digital")


def aplicar_rescate_binance_pending_gmail(pending_row: dict[str, Any]) -> dict[str, Any]:
    """Actualiza control_usuario_operaciones en fila pending del pipeline si aplica rescate."""
    if (pending_row.get("fmt") or "").strip().upper() != "C":
        return pending_row
    ctrl, rescate, motivo = resolver_control_usuario_operaciones_gmail_plantilla_c(
        control_actual=pending_row.get("control_usuario_operaciones"),
        monto_str=pending_row.get("m") or "",
        numero_referencia=pending_row.get("r") or "",
        cedula_columna=pending_row.get("c") or "",
        fecha_pago_str=pending_row.get("f") or "",
        image_bytes=pending_row.get("content"),
        filename=pending_row.get("filename") or "comprobante.jpg",
    )
    if rescate:
        pending_row["control_usuario_operaciones"] = ctrl
        pending_row["_binance_rescate"] = motivo
    return pending_row
