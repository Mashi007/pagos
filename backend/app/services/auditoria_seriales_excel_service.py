"""
Auditoría → Seriales / Pagos: Excel (Deposito | Referencia | Monto | SI/NO)
compara columna B contra pagos.numero_documento y pagos.referencia_pago.
"""
from __future__ import annotations

import io
import logging
import re
from typing import Any, Optional

from fastapi import HTTPException
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.documento import normalize_documento, split_numero_documento_almacenado
from app.models.pago import Pago

logger = logging.getLogger(__name__)

MAX_FILAS_DATOS = 20000
_RE_CONTROL5 = re.compile(r"_[AP]\d{4}$", re.IGNORECASE)
_RE_SERIAL_MIXTO_SPLIT = re.compile(r"\s*[-–—/|]\s*")


def _celda_a_string_documento(val: Any) -> str:
    """Convierte celda Excel a string (evita notación científica en enteros)."""
    if val is None:
        return ""
    if isinstance(val, float):
        if val != val:
            return ""
        if val == int(val):
            return str(int(val))
        return str(val)
    if isinstance(val, int):
        return str(val)
    return str(val).strip()


def _clave_serial(raw: Any) -> str:
    """
    Normaliza serial Excel/BD: quita §CD:, sufijo Control5 y deja solo dígitos
    (sin ceros a la izquierda). Misma idea que Conciliación Bancos.
    """
    s = _celda_a_string_documento(raw)
    if not s:
        return ""
    if re.fullmatch(r"\d+\.0+", s):
        s = s.split(".", 1)[0]
    base, _codigo = split_numero_documento_almacenado(s)
    s = normalize_documento(base) or (base or s).strip()
    s = _RE_CONTROL5.sub("", s).strip() or s
    dig = re.sub(r"\D+", "", s)
    return dig.lstrip("0") or (dig if dig else "")


def _partes_serial(raw: Any) -> list[str]:
    """Partes numéricas si el campo trae seriales mixtos separados."""
    s = _celda_a_string_documento(raw)
    if not s:
        return []
    chunks = [c.strip() for c in _RE_SERIAL_MIXTO_SPLIT.split(s) if c and c.strip()]
    if len(chunks) <= 1:
        k = _clave_serial(s)
        return [k] if k else []
    out: list[str] = []
    seen: set[str] = set()
    for ch in chunks:
        k = _clave_serial(ch)
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    if not out:
        k = _clave_serial(s)
        if k:
            out.append(k)
    return out


def _claves_desde_campos_pago(numero_documento: Any, referencia_pago: Any) -> set[str]:
    """Claves normalizadas solo desde numero_documento y referencia_pago."""
    out: set[str] = set()
    for cand in (numero_documento, referencia_pago):
        for dig in _partes_serial(cand):
            out.add(dig)
    return out


def _es_fila_encabezado(a: Any, b: Any, c: Any, d: Any) -> bool:
    textos = " ".join(
        str(x or "").strip().lower() for x in (a, b, c, d)
    )
    return (
        "referencia" in textos
        or "serial" in textos
        or "deposito" in textos
        or "depósito" in textos
        or "si/no" in textos
        or textos.strip() in ("si/no", "si", "no")
    )


def _cargar_claves_bd(db: Session) -> set[str]:
    """Set de seriales normalizados presentes en pagos (cualquier estado)."""
    rows = db.execute(
        select(Pago.numero_documento, Pago.referencia_pago).where(
            or_(
                Pago.numero_documento.isnot(None),
                Pago.referencia_pago.isnot(None),
            )
        )
    ).all()
    claves: set[str] = set()
    for num, ref in rows:
        if (ref or "").strip() == "" and not (num or "").strip():
            continue
        claves |= _claves_desde_campos_pago(num, ref)
    return claves


def verificar_seriales_excel(db: Session, content: bytes) -> dict[str, Any]:
    """
    Lee Excel (columna B = Referencia), marca si/no según BD.

    Retorna resumen + items (una entrada por fila de datos).
    """
    try:
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"No se pudo leer el Excel: {exc}",
        ) from exc

    ws = wb.active
    if ws is None:
        raise HTTPException(status_code=400, detail="El Excel no tiene hojas.")

    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not rows:
        raise HTTPException(status_code=400, detail="El Excel está vacío.")

    start = 0
    if rows and _es_fila_encabezado(
        rows[0][0] if len(rows[0]) > 0 else None,
        rows[0][1] if len(rows[0]) > 1 else None,
        rows[0][2] if len(rows[0]) > 2 else None,
        rows[0][3] if len(rows[0]) > 3 else None,
    ):
        start = 1

    data_rows = rows[start:]
    if len(data_rows) > MAX_FILAS_DATOS:
        raise HTTPException(
            status_code=400,
            detail=f"Máximo {MAX_FILAS_DATOS} filas de datos por archivo.",
        )

    claves_bd = _cargar_claves_bd(db)

    items: list[dict[str, Any]] = []
    n_si = 0
    n_no = 0
    n_vacios = 0

    for i, row in enumerate(data_rows):
        fila_excel = start + i + 1
        if not row or all(c is None or str(c).strip() == "" for c in row[:3]):
            continue
        serial_raw = _celda_a_string_documento(row[1] if len(row) > 1 else None)
        clave = _clave_serial(serial_raw)
        if not clave:
            n_vacios += 1
            n_no += 1
            resultado = "no"
        elif clave in claves_bd:
            n_si += 1
            resultado = "si"
        else:
            n_no += 1
            resultado = "no"
        items.append(
            {
                "fila": fila_excel,
                "serial_archivo": serial_raw,
                "serial_norm": clave or None,
                "resultado": resultado,
                "en_bd": resultado == "si",
            }
        )

    return {
        "total_filas": len(items),
        "encontrados_si": n_si,
        "no_encontrados_no": n_no,
        "seriales_vacios": n_vacios,
        "items": items,
    }


def _escribir_si_no_en_hoja(ws: Worksheet, payload: dict[str, Any]) -> None:
    """Escribe 'si'/'no' en columna D según items (por número de fila Excel)."""
    por_fila = {int(it["fila"]): it["resultado"] for it in payload.get("items") or []}
    # Encabezado SI/NO
    header_val = ws.cell(1, 4).value
    if header_val is None or str(header_val).strip() == "":
        # Si fila 1 parece datos (sin encabezado), no forzar; si hay encabezados A-C, poner D.
        a = str(ws.cell(1, 1).value or "").strip().lower()
        b = str(ws.cell(1, 2).value or "").strip().lower()
        if "deposito" in a or "referencia" in b or "serial" in b:
            ws.cell(1, 4).value = "SI/NO"
    else:
        # Normaliza título si ya existe vacío de significado
        pass

    for fila, resultado in por_fila.items():
        ws.cell(fila, 4).value = resultado


def exportar_excel_con_si_no(content: bytes, payload: dict[str, Any]) -> bytes:
    """
    Devuelve el mismo Excel con columna D rellenada (si/no).
    Conserva el resto de celdas del archivo original.
    """
    try:
        wb = load_workbook(io.BytesIO(content))
    except Exception as exc:
        # Fallback: armar un Excel nuevo desde items
        logger.warning("No se pudo reabrir Excel para anotar; se genera uno nuevo: %s", exc)
        return _excel_nuevo_desde_payload(payload)

    ws = wb.active
    if ws is None:
        return _excel_nuevo_desde_payload(payload)

    _escribir_si_no_en_hoja(ws, payload)
    buf = io.BytesIO()
    wb.save(buf)
    wb.close()
    return buf.getvalue()


def _excel_nuevo_desde_payload(payload: dict[str, Any]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Seriales"
    ws.append(["Deposito", "Referencia", "Monto", "SI/NO"])
    for it in payload.get("items") or []:
        ws.append([None, it.get("serial_archivo"), None, it.get("resultado")])
    buf = io.BytesIO()
    wb.save(buf)
    wb.close()
    return buf.getvalue()
