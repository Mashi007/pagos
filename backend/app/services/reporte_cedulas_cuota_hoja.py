"""
Excel Cédula | Cuota | Ene–Ago 2026 para las cédulas de la hoja Drive.

Cuota: prestamos.cuota_periodo (APROBADO; si no hay, LIQUIDADO o DESISTIMIENTO).
Meses: saldo vencido pendiente acumulado desde enero hasta ese mes
(febrero = enero + febrero, solo cuotas VENCIDO/MORA).
No se estima ni se rellena con 0: sin vencidos hasta ese mes, la celda queda vacía.
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

from sqlalchemy import select
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
_ESTADOS_PRESTAMO = ("APROBADO", "LIQUIDADO", "DESISTIMIENTO")
_ANIO_VENCIDOS = 2026
_MES_DESDE = 1
_MES_HASTA = 8
MESES_VENCIDOS: Tuple[Tuple[int, int, str], ...] = tuple(
    (_ANIO_VENCIDOS, m, nombre)
    for m, nombre in enumerate(
        (
            "Hasta enero 2026",
            "Hasta febrero 2026",
            "Hasta marzo 2026",
            "Hasta abril 2026",
            "Hasta mayo 2026",
            "Hasta junio 2026",
            "Hasta julio 2026",
            "Hasta agosto 2026",
        ),
        start=1,
    )
)
_CLAVES_MES = tuple(f"{anio}-{mes:02d}" for anio, mes, _ in MESES_VENCIDOS)


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

    Prioriza APROBADO. Si no hay, LIQUIDADO o DESISTIMIENTO.
    Distintos montos → None (no se elige ni se promedia).
    """
    if not prestamos:
        return None
    aprobados = [
        _a_decimal(m)
        for est, m in prestamos
        if str(est or "").strip().upper() == "APROBADO"
    ]
    pool = [x for x in aprobados if x is not None]
    if not pool:
        otros = [
            _a_decimal(m)
            for est, m in prestamos
            if str(est or "").strip().upper() in ("LIQUIDADO", "DESISTIMIENTO")
        ]
        pool = [x for x in otros if x is not None]
    if not pool:
        return None
    montos = {x.quantize(Decimal("0.01")) for x in pool}
    if len(montos) != 1:
        return None
    return montos.pop()


def _clave_mes(fv: date) -> Optional[str]:
    if fv.year != _ANIO_VENCIDOS or not (_MES_DESDE <= fv.month <= _MES_HASTA):
        return None
    return f"{fv.year}-{fv.month:02d}"


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
    claves = [c for c in {x for x in cedulas_norm if x}]
    if not claves:
        return {}
    ced_expr = expr_cedula_normalizada_para_comparar(Prestamo.cedula)
    estado = Prestamo.estado
    rows = db.execute(
        select(ced_expr, estado, Prestamo.cuota_periodo).where(
            ced_expr.in_(claves),
            estado.in_(_ESTADOS_PRESTAMO),
        )
    ).all()
    out: Dict[str, List[Tuple[str, Any]]] = {}
    for ced, est, cuota in rows:
        k = texto_cedula_comparable_bd(ced or "")
        if not k:
            continue
        out.setdefault(k, []).append((str(est or ""), cuota))
    return out


def _vencidos_por_cedula_mes(
    db: Session,
    cedulas_norm: Iterable[str],
    fecha_ref: Optional[date] = None,
) -> Dict[str, Dict[str, Decimal]]:
    """ced_norm -> { '2026-01': Decimal, ... } solo saldos VENCIDO/MORA de ese mes."""
    from app.models.cuota import Cuota
    from app.services.cuota_estado import hoy_negocio

    claves = [c for c in {x for x in cedulas_norm if x}]
    if not claves:
        return {}
    ref = fecha_ref or hoy_negocio()
    inicio = date(_ANIO_VENCIDOS, _MES_DESDE, 1)
    fin = date(_ANIO_VENCIDOS, _MES_HASTA, 31)
    ced_expr = expr_cedula_normalizada_para_comparar(Prestamo.cedula)
    rows = db.execute(
        select(
            ced_expr,
            Cuota.fecha_vencimiento,
            Cuota.monto,
            Cuota.total_pagado,
            Cuota.fecha_pago,
        )
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .where(
            ced_expr.in_(claves),
            Prestamo.estado.in_(_ESTADOS_PRESTAMO),
            Cuota.fecha_vencimiento >= inicio,
            Cuota.fecha_vencimiento <= fin,
            Cuota.fecha_vencimiento < ref,
        )
    ).all()
    out: Dict[str, Dict[str, Decimal]] = {}
    for ced, fv, monto, pagado, f_pago in rows:
        k = texto_cedula_comparable_bd(ced or "")
        if not k or fv is None:
            continue
        fv_d = fv.date() if hasattr(fv, "date") else fv
        clave = _clave_mes(fv_d)
        if not clave:
            continue
        saldo = pendiente_vencido(monto, pagado, fv_d, f_pago, ref)
        if saldo is None:
            continue
        bucket = out.setdefault(k, {})
        bucket[clave] = (bucket.get(clave, Decimal("0")) + saldo).quantize(
            Decimal("0.01")
        )
    return out


def acumular_vencidos_hasta_mes(
    por_mes: Dict[str, Decimal],
) -> Dict[str, Decimal]:
    """
    Acumulado de cuotas vencidas pendientes: cada mes = suma de ese mes y los anteriores.
    Solo aparecen meses desde el primer vencido; no se rellena 0.
    """
    acc = Decimal("0")
    hubo = False
    out: Dict[str, Decimal] = {}
    for clave in _CLAVES_MES:
        extra = por_mes.get(clave)
        if extra is not None:
            acc = (acc + extra).quantize(Decimal("0.01"))
            hubo = True
        if hubo and acc > Decimal("0.00"):
            out[clave] = acc
    return out


def filas_cedula_cuota(
    cedulas_hoja: Sequence[str],
    prestamos_por_norm: Dict[str, List[Tuple[str, Any]]],
    vencidos_por_norm: Optional[Dict[str, Dict[str, Decimal]]] = None,
) -> List[Dict[str, Any]]:
    vencidos_por_norm = vencidos_por_norm or {}
    filas: List[Dict[str, Any]] = []
    for raw in cedulas_hoja:
        k = texto_cedula_comparable_bd(raw)
        cuota = cuota_unica_de_prestamos(prestamos_por_norm.get(k, []))
        meses = acumular_vencidos_hasta_mes(vencidos_por_norm.get(k, {}))
        fila: Dict[str, Any] = {
            "cedula": raw,
            "cuota": float(cuota) if cuota is not None else None,
        }
        for clave in _CLAVES_MES:
            val = meses.get(clave)
            fila[clave] = float(val) if val is not None else None
        filas.append(fila)
    return filas


def generar_excel_cedulas_cuota(filas: Sequence[Dict[str, Any]]) -> bytes:
    import openpyxl
    from openpyxl.styles import Alignment, Font, numbers

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Cedula cuota"
    headers = ["Cédula", "Cuota"] + [nombre for _a, _m, nombre in MESES_VENCIDOS]
    ws.append(headers)
    for col in range(1, len(headers) + 1):
        ws.cell(1, col).font = Font(bold=True)
    for f in filas:
        cuota = f.get("cuota")
        row: List[Any] = [f.get("cedula") or "", cuota if cuota is not None else None]
        for clave in _CLAVES_MES:
            row.append(f.get(clave) if f.get(clave) is not None else None)
        ws.append(row)
        for col in range(2, len(headers) + 1):
            cell = ws.cell(ws.max_row, col)
            if cell.value is not None:
                cell.number_format = numbers.FORMAT_NUMBER_COMMA_SEPARATED2
            cell.alignment = Alignment(horizontal="right")
    ws.column_dimensions["A"].width = 18
    for col in range(2, len(headers) + 1):
        ws.column_dimensions[chr(64 + col)].width = 14
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
    vencidos = _vencidos_por_cedula_mes(db, normas)
    filas = filas_cedula_cuota(lista, mapa, vencidos)
    con_cuota = sum(1 for f in filas if f.get("cuota") is not None)
    logger.info(
        "[reporte_cedulas_cuota_hoja] filas=%s con_cuota=%s sin_cuota=%s",
        len(filas),
        con_cuota,
        len(filas) - con_cuota,
    )
    return generar_excel_cedulas_cuota(filas), len(filas), con_cuota
