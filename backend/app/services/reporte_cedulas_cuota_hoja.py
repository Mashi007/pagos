"""
Excel Cédula | Cuota | dos cortes (1 jun 2026 y hoy) para cédulas de la hoja Drive.

Cuota: prestamos.cuota_periodo (APROBADO; si no hay, LIQUIDADO, DESISTIMIENTO u otro).
Cédula hoja E84491751 cruza con V84491751 o 84491751 en sistema.
Solo cuotas del préstamo APROBADO (misma vista que el front); no mezcla LIQUIDADO u otros.

Por corte (1 jun 2026 y hoy Caracas):
- Cuotas en mora: cantidad con estado MORA (no VENCIDO).
- Saldo vencido: suma pendiente de esas cuotas en MORA.
APROBADO: ambas columnas solo si hay 4+ en mora en ese corte (mismo filtro en junio y hoy).
"""
from __future__ import annotations

import csv
import io
import logging
import urllib.error
import urllib.request
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.prestamo import Prestamo
from app.utils.cedula_almacenamiento import (
    expr_cedula_normalizada_para_comparar,
    texto_cedula_comparable_bd,
)

logger = logging.getLogger(__name__)

_SHEET_EXPORT = (
    "https://docs.google.com/spreadsheets/d/{sid}/export?format=csv"
)
_ESTADOS_EXCLUIDOS = ("DRAFT", "RECHAZADO")
FECHA_CORTE_JUNIO = date(2026, 6, 1)
MIN_CUOTAS_MORA_APROBADO = 4

CLAVE_JUNIO = "junio"
CLAVE_HOY = "hoy"


def _sheet_id() -> str:
    from app.core.config import settings

    return (
        getattr(settings, "REPORTE_CUOTAS_JUN_AGO_SHEET_ID", None)
        or "1_Qean5MoSc1vWy6hMAAqOcMJeZzn9iUspJTqsOqZEqs"
    ).strip()


def _a_decimal(val: Any) -> Optional[Decimal]:
    if val is None or val == "":
        return None
    try:
        d = Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return d


def cuota_unica_de_prestamos(
    prestamos: Sequence[Tuple[str, Any]],
) -> Optional[Decimal]:
    """
    Un solo monto si todos los préstamos elegibles coinciden.

    Prioriza APROBADO. Si no hay, LIQUIDADO/DESISTIMIENTO u otro estado con un solo monto.
    Distintos montos → None (no se elige ni se promedia).
    """
    if not prestamos:
        return None
    aprobados = [
        _a_decimal(m)
        for est, m in prestamos
        if str(est or "").strip().upper() == "APROBADO"
    ]
    aprobados = [m for m in aprobados if m is not None]
    if aprobados:
        montos = set(aprobados)
        if len(montos) != 1:
            return None
        return montos.pop()
    montos = {_a_decimal(m) for _e, m in prestamos}
    montos.discard(None)
    if len(montos) != 1:
        return None
    return montos.pop()


def estado_actual_de_prestamos(
    prestamos: Sequence[Tuple[str, Any]],
) -> Optional[str]:
    """
    Estado actual del préstamo. Si hay APROBADO, ese.
    Si no, un único estado; si hay varios reales, se listan separados por ' / '.
    """
    estados: List[str] = []
    for est, _m in prestamos:
        e = str(est or "").strip().upper()
        if e and e not in estados:
            estados.append(e)
    if not estados:
        return None
    if "APROBADO" in estados:
        return "APROBADO"
    if len(estados) == 1:
        return estados[0]
    orden = ("LIQUIDADO", "DESISTIMIENTO")
    ordenados = [e for e in orden if e in estados]
    ordenados.extend(e for e in estados if e not in orden)
    return " / ".join(ordenados)


def _digitos_cedula(ced: str) -> str:
    return "".join(ch for ch in (ced or "") if ch.isdigit())


def _claves_equivalentes_cedula(ced: str) -> List[str]:
    """E84491751, V84491751 y 84491751 se tratan como la misma persona."""
    full = texto_cedula_comparable_bd(ced)
    digits = _digitos_cedula(full)
    keys: List[str] = []
    for k in (full, digits, *(f"{p}{digits}" for p in "VEJG" if digits)):
        if k and k not in keys:
            keys.append(k)
    return keys


def _expandir_claves_sql(cedulas: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for c in cedulas:
        for k in _claves_equivalentes_cedula(c):
            if k not in seen:
                seen.add(k)
                out.append(k)
    return out


def _prestamos_para_cedula_hoja(
    ced_hoja: str,
    prestamos_por_norm: Dict[str, List[Tuple[str, Any]]],
) -> List[Tuple[str, Any]]:
    k = texto_cedula_comparable_bd(ced_hoja)
    if k in prestamos_por_norm:
        return prestamos_por_norm[k]
    digits = _digitos_cedula(k)
    if not digits:
        return []
    merged: List[Tuple[str, Any]] = []
    seen: set[Tuple[str, str]] = set()
    for mk, prests in prestamos_por_norm.items():
        if _digitos_cedula(mk) != digits:
            continue
        for est, monto in prests:
            ident = (str(est), str(monto))
            if ident in seen:
                continue
            seen.add(ident)
            merged.append((est, monto))
    return merged


def _items_para_cedula_hoja(
    ced_hoja: str,
    items_por_norm: Dict[str, List[Tuple[Any, Any, Any, Any, Any, Any]]],
) -> List[Tuple[Any, Any, Any, Any, Any, Any]]:
    k = texto_cedula_comparable_bd(ced_hoja)
    if k in items_por_norm:
        return items_por_norm[k]
    digits = _digitos_cedula(k)
    if not digits:
        return []
    for mk, items in items_por_norm.items():
        if _digitos_cedula(mk) == digits:
            return items
    return []


def _as_date(v: Any) -> Optional[date]:
    if v is None:
        return None
    return v.date() if hasattr(v, "date") else v


def pendiente_vencido(
    monto: Any,
    total_pagado: Any,
    fecha_vencimiento: Optional[date],
    fecha_pago: Optional[date] = None,
    fecha_ref: Optional[date] = None,
) -> Optional[Decimal]:
    """Saldo pendiente solo si el estado real es VENCIDO o MORA. None si no aplica."""
    from app.services.cuota_estado import clasificar_estado_cuota, hoy_negocio

    m = _a_decimal(monto)
    if m is None or fecha_vencimiento is None:
        return None
    pagado = _a_decimal(total_pagado) or Decimal("0")
    if fecha_pago is not None and pagado < Decimal("0.01"):
        pagado = m
    ref = fecha_ref or hoy_negocio()
    est = clasificar_estado_cuota(float(pagado), float(m), fecha_vencimiento, ref)
    if est not in ("VENCIDO", "MORA"):
        return None
    saldo = (m - pagado).quantize(Decimal("0.01"))
    if saldo <= Decimal("0.00"):
        return None
    return saldo


def _estado_item_al(
    fv: Any,
    monto: Any,
    pagado: Any,
    fp: Any,
    as_of: date,
) -> Optional[str]:
    from app.services.cuota_estado import clasificar_estado_cuota

    fv_d = _as_date(fv)
    if fv_d is None:
        return None
    m = _a_decimal(monto)
    if m is None:
        return None
    fp_d = _as_date(fp)
    if fp_d is not None and fp_d > as_of:
        pag_eff = Decimal("0")
    else:
        pag_eff = _a_decimal(pagado) or Decimal("0")
        if fp_d is not None and pag_eff < Decimal("0.01"):
            pag_eff = m
    return clasificar_estado_cuota(float(pag_eff), float(m), fv_d, as_of)


def _saldo_mora_item_al(
    fv: Any,
    monto: Any,
    pagado: Any,
    fp: Any,
    as_of: date,
) -> Optional[Decimal]:
    """Pendiente de la cuota solo si a as_of está en MORA."""
    if _estado_item_al(fv, monto, pagado, fp, as_of) != "MORA":
        return None
    fv_d = _as_date(fv)
    m = _a_decimal(monto)
    if fv_d is None or m is None:
        return None
    fp_d = _as_date(fp)
    if fp_d is not None and fp_d > as_of:
        pag_eff, fp_eff = Decimal("0"), None
    else:
        pag_eff, fp_eff = pagado, fp_d
    return pendiente_vencido(m, pag_eff, fv_d, fp_eff, as_of)


def conteo_cuotas_en_mora(
    items: Sequence[Tuple[Any, Any, Any, Any, Any, Any]],
    as_of: date,
) -> int:
    """Cantidad de cuotas con estado MORA a la fecha. No incluye VENCIDO."""
    n = 0
    for _nro, fv, monto, pagado, fp, _tot in items:
        if _estado_item_al(fv, monto, pagado, fp, as_of) == "MORA":
            n += 1
    return n


def saldo_vencido_en_mora(
    items: Sequence[Tuple[Any, Any, Any, Any, Any, Any]],
    as_of: date,
) -> Decimal:
    """Suma pendiente de cuotas en MORA a la fecha."""
    total = Decimal("0")
    for _nro, fv, monto, pagado, fp, _tot in items:
        sal = _saldo_mora_item_al(fv, monto, pagado, fp, as_of)
        if sal is not None:
            total += sal
    return total.quantize(Decimal("0.01"))


def metricas_corte_mora(
    items: Sequence[Tuple[Any, Any, Any, Any, Any, Any]],
    as_of: date,
    *,
    es_aprobado: bool,
) -> Tuple[Optional[int], Optional[Decimal]]:
    """
    (cuotas_en_mora, saldo_vencido). APROBADO: vacío si < 4 en mora.
    """
    n = conteo_cuotas_en_mora(items, as_of)
    if es_aprobado and n < MIN_CUOTAS_MORA_APROBADO:
        return None, None
    if n <= 0:
        return None, None
    return n, saldo_vencido_en_mora(items, as_of)


def parsear_cedulas_csv(raw: bytes) -> List[str]:
    if (
        not raw
        or raw.lstrip()[:15].lower().startswith(b"<!doctype")
        or b"<html" in raw[:400].lower()
    ):
        raise RuntimeError(
            "La hoja Drive no devolvio CSV (inicie sesion o publique la hoja)."
        )
    text = raw.decode("utf-8-sig", errors="replace")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return []
    out: List[str] = []
    for i, row in enumerate(rows):
        if not row:
            continue
        cell = str(row[0] or "").strip()
        if not cell:
            continue
        if i == 0 and not any(ch.isdigit() for ch in cell):
            continue
        out.append(cell)
    return out


def leer_cedulas_hoja(spreadsheet_id: Optional[str] = None) -> List[str]:
    sid = (spreadsheet_id or _sheet_id()).strip()
    if not sid:
        raise RuntimeError("REPORTE_CUOTAS_JUN_AGO_SHEET_ID no configurado.")
    url = _SHEET_EXPORT.format(sid=sid)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "pagos-reportes-cedulas-cuota/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
    except urllib.error.URLError as e:
        raise RuntimeError(f"No se pudo leer la hoja Drive: {e}") from e
    return parsear_cedulas_csv(raw)


def _cuotas_bd_por_cedula_norm(
    db: Session, cedulas_norm: Iterable[str]
) -> Dict[str, List[Tuple[str, Any]]]:
    claves = _expandir_claves_sql(cedulas_norm)
    if not claves:
        return {}
    ced_expr = expr_cedula_normalizada_para_comparar(Prestamo.cedula)
    estado_u = func.upper(func.trim(Prestamo.estado))
    rows = db.execute(
        select(ced_expr, Prestamo.estado, Prestamo.cuota_periodo).where(
            ced_expr.in_(claves),
            estado_u.notin_(_ESTADOS_EXCLUIDOS),
        )
    ).all()
    out: Dict[str, List[Tuple[str, Any]]] = {}
    for ced, est, cuota in rows:
        k = texto_cedula_comparable_bd(ced or "")
        if not k:
            continue
        out.setdefault(k, []).append((str(est or ""), cuota))
    return out


def _items_cuotas_para_informe(
    k: str,
    items_all: Dict[str, List[Tuple[Any, Any, Any, Any, Any, Any]]],
    items_aprobado: Dict[str, List[Tuple[Any, Any, Any, Any, Any, Any]]],
    estados_por_k: Dict[str, set],
) -> List[Tuple[Any, Any, Any, Any, Any, Any]]:
    """APROBADO: solo cuotas del préstamo activo; resto: todos los préstamos elegibles."""
    if "APROBADO" in estados_por_k.get(k, set()):
        return items_aprobado.get(k, [])
    return items_all.get(k, [])


def _cargar_items_cuotas_por_cedula(
    db: Session,
    cedulas_norm: Iterable[str],
) -> Dict[str, List[Tuple[Any, Any, Any, Any, Any, Any]]]:
    """ced_norm -> cuotas del préstamo relevante (APROBADO si existe)."""
    from app.models.cuota import Cuota

    claves = _expandir_claves_sql(cedulas_norm)
    if not claves:
        return {}
    ced_expr = expr_cedula_normalizada_para_comparar(Prestamo.cedula)
    estado_u = func.upper(func.trim(Prestamo.estado))
    rows = db.execute(
        select(
            ced_expr,
            Cuota.fecha_vencimiento,
            Cuota.monto,
            Cuota.total_pagado,
            Cuota.fecha_pago,
            Cuota.numero_cuota,
            Prestamo.numero_cuotas,
            Prestamo.estado,
        )
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .where(
            ced_expr.in_(claves),
            estado_u.notin_(_ESTADOS_EXCLUIDOS),
        )
    ).all()
    items_all: Dict[str, List[Tuple[Any, Any, Any, Any, Any, Any]]] = {}
    items_aprobado: Dict[str, List[Tuple[Any, Any, Any, Any, Any, Any]]] = {}
    estados_por_k: Dict[str, set] = {}
    for ced, fv, monto, pagado, f_pago, nro, tot, est in rows:
        k = texto_cedula_comparable_bd(ced or "")
        if not k or fv is None:
            continue
        fv_d = fv.date() if hasattr(fv, "date") else fv
        item = (nro, fv_d, monto, pagado, f_pago, tot)
        items_all.setdefault(k, []).append(item)
        e = str(est or "").strip().upper()
        if e == "APROBADO":
            items_aprobado.setdefault(k, []).append(item)
        if e:
            estados_por_k.setdefault(k, set()).add(e)
    out: Dict[str, List[Tuple[Any, Any, Any, Any, Any, Any]]] = {}
    for k in items_all:
        out[k] = _items_cuotas_para_informe(k, items_all, items_aprobado, estados_por_k)
    return out


def filas_cedula_cuota(
    cedulas_hoja: Sequence[str],
    prestamos_por_norm: Dict[str, List[Tuple[str, Any]]],
    items_por_norm: Optional[
        Dict[str, List[Tuple[Any, Any, Any, Any, Any, Any]]]
    ] = None,
    *,
    fecha_junio: date = FECHA_CORTE_JUNIO,
    fecha_hoy: Optional[date] = None,
) -> List[Dict[str, Any]]:
    from app.services.cuota_estado import hoy_negocio

    items_por_norm = items_por_norm or {}
    hoy = fecha_hoy or hoy_negocio()
    filas: List[Dict[str, Any]] = []
    for raw in cedulas_hoja:
        prests = _prestamos_para_cedula_hoja(raw, prestamos_por_norm)
        estado = estado_actual_de_prestamos(prests)
        es_aprobado = estado == "APROBADO"
        cuota = cuota_unica_de_prestamos(prests)
        items = _items_para_cedula_hoja(raw, items_por_norm)
        n_jun, sal_jun = metricas_corte_mora(
            items, fecha_junio, es_aprobado=es_aprobado
        )
        n_hoy, sal_hoy = metricas_corte_mora(items, hoy, es_aprobado=es_aprobado)
        filas.append(
            {
                "cedula": raw,
                "estado": estado,
                "cuota": float(cuota) if cuota is not None else None,
                "fecha_junio": fecha_junio,
                "fecha_hoy": hoy,
                "mora_junio": n_jun,
                "saldo_junio": float(sal_jun) if sal_jun is not None else None,
                "mora_hoy": n_hoy,
                "saldo_hoy": float(sal_hoy) if sal_hoy is not None else None,
            }
        )
    return filas


def generar_excel_cedulas_cuota(filas: Sequence[Dict[str, Any]]) -> bytes:
    import openpyxl
    from openpyxl.styles import Alignment, Font, numbers
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Cedula cuota"
    bold = Font(bold=True)
    centro = Alignment(horizontal="center")

    fecha_junio = next(
        (f.get("fecha_junio") for f in filas if f.get("fecha_junio")), FECHA_CORTE_JUNIO
    )
    fecha_hoy = next((f.get("fecha_hoy") for f in filas if f.get("fecha_hoy")), None)
    label_junio = (
        f"1 jun {fecha_junio.year}"
        if isinstance(fecha_junio, date)
        else "1 jun 2026"
    )
    label_hoy = (
        f"Hoy ({fecha_hoy.isoformat()})"
        if isinstance(fecha_hoy, date)
        else "Hoy"
    )

    ws.cell(1, 1, "Cédula").font = bold
    ws.cell(1, 2, "Estado").font = bold
    ws.cell(1, 3, "Cuota").font = bold
    ws.merge_cells(start_row=1, start_column=1, end_row=2, end_column=1)
    ws.merge_cells(start_row=1, start_column=2, end_row=2, end_column=2)
    ws.merge_cells(start_row=1, start_column=3, end_row=2, end_column=3)

    for c1, titulo in ((4, label_junio), (6, label_hoy)):
        ws.merge_cells(start_row=1, start_column=c1, end_row=1, end_column=c1 + 1)
        cell_m = ws.cell(1, c1, titulo)
        cell_m.font = bold
        cell_m.alignment = centro
        ws.cell(2, c1, "Cuotas en mora").font = bold
        ws.cell(2, c1 + 1, "Saldo vencido").font = bold

    for f in filas:
        row = [
            f.get("cedula") or "",
            f.get("estado") or None,
            f.get("cuota") if f.get("cuota") is not None else None,
            f.get("mora_junio") if f.get("mora_junio") is not None else None,
            f.get("saldo_junio") if f.get("saldo_junio") is not None else None,
            f.get("mora_hoy") if f.get("mora_hoy") is not None else None,
            f.get("saldo_hoy") if f.get("saldo_hoy") is not None else None,
        ]
        ws.append(row)
        r = ws.max_row
        for col in (3, 5, 7):
            cell = ws.cell(r, col)
            if cell.value is not None:
                cell.number_format = numbers.FORMAT_NUMBER_COMMA_SEPARATED2
            cell.alignment = Alignment(horizontal="right")
        for col in (4, 6):
            ws.cell(r, col).alignment = Alignment(horizontal="center")

    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 18
    for col in range(3, 8):
        ws.column_dimensions[get_column_letter(col)].width = 16
    ws.freeze_panes = "A3"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def construir_excel_cedulas_cuota_hoja(
    db: Session,
    *,
    spreadsheet_id: Optional[str] = None,
    cedulas: Optional[Sequence[str]] = None,
) -> Tuple[bytes, int, int]:
    """
    Devuelve (xlsx, filas, filas_con_cuota).
    `cedulas` solo para tests; en runtime se leen de la hoja.
    """
    lista = list(cedulas) if cedulas is not None else leer_cedulas_hoja(spreadsheet_id)
    if not lista:
        raise RuntimeError("La hoja no tiene cédulas.")
    normas = [texto_cedula_comparable_bd(c) for c in lista]
    mapa = _cuotas_bd_por_cedula_norm(db, normas)
    items = _cargar_items_cuotas_por_cedula(db, normas)
    filas = filas_cedula_cuota(lista, mapa, items)
    con_cuota = sum(1 for f in filas if f.get("cuota") is not None)
    logger.info(
        "[reporte_cedulas_cuota_hoja] filas=%s con_cuota=%s sin_cuota=%s",
        len(filas),
        con_cuota,
        len(filas) - con_cuota,
    )
    return generar_excel_cedulas_cuota(filas), len(filas), con_cuota
