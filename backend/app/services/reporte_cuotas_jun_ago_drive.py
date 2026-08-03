"""
REPORTE cuotas jun-ago: informe estatico que actualiza Google Drive.

Universo: solo cedulas de la hoja.
Escribe solo columnas D y E (delta del periodo; no reescribe la base).

Regla (jun/jul 2026 por fecha de pago, no por vencimiento de cuota):
  Mes "cubierto" = hubo pago operativo (abono o total) en ese mes calendario
  aplicado a CUALQUIER cuota del prestamo (o pago operativo del prestamo
  en ese mes). Cascada / vencimiento de la cuota no importa.

  D = (meses sin pago) - (meses con pago)
    ej. sin pagos jun ni jul => +2; pago solo un mes => 0; pago ambos => -2.

  E = suma positiva de montos de esos pagos en jun+jul (0 si no hubo).
"""
from __future__ import annotations

import logging
import re
import unicodedata
from calendar import monthrange
from datetime import date
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.cliente import Cliente
from app.models.cuota_pago import CuotaPago
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.utils.cedula_almacenamiento import (
    expr_cedula_normalizada_para_comparar,
    texto_cedula_comparable_bd,
)

logger = logging.getLogger(__name__)

FECHA_CORTE = date(2026, 8, 2)
MESES_PERIODO: Tuple[Tuple[int, int], ...] = ((2026, 6), (2026, 7))
_DEFAULT_SHEET_ID = "1_Qean5MoSc1vWy6hMAAqOcMJeZzn9iUspJTqsOqZEqs"
IDX_COL_D = 3
IDX_COL_E = 4


def _sheet_id() -> str:
    return (
        getattr(settings, "REPORTE_CUOTAS_JUN_AGO_SHEET_ID", None)
        or _DEFAULT_SHEET_ID
    ).strip()


def _norm_header(h: str) -> str:
    s = unicodedata.normalize("NFKD", (h or "").strip().lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s)


def _pick_col(headers: List[str], *names: str) -> Optional[int]:
    wanted = {_norm_header(n) for n in names}
    for i, h in enumerate(headers):
        if _norm_header(str(h)) in wanted:
            return i
    for i, h in enumerate(headers):
        hl = _norm_header(str(h))
        for n in names:
            if _norm_header(n) in hl:
                return i
    return None


def _col_index_to_a1(col_1based: int) -> str:
    n = col_1based
    letters = []
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters.append(chr(65 + rem))
    return "".join(reversed(letters))


def _mes_bounds(anio: int, mes: int) -> Tuple[date, date]:
    ultimo = monthrange(anio, mes)[1]
    return date(anio, mes, 1), date(anio, mes, ultimo)


def _delta_cobertura_por_cedula(
    db: Session,
    cedulas: Set[str],
    fecha_corte: date = FECHA_CORTE,
) -> Dict[str, Dict[str, Any]]:
    """
    D/E por cedula segun pagos calendario en junio/julio a cualquier cuota.
    """
    if not cedulas:
        return {}

    estado_pago = func.upper(func.trim(func.coalesce(Pago.estado, "")))
    pago_operativo = and_(
        ~estado_pago.like("ANULADO%"),
        estado_pago.is_distinct_from("DUPLICADO"),
    )
    estado_prestamo = func.upper(func.trim(Prestamo.estado))
    ced_expr = expr_cedula_normalizada_para_comparar(Prestamo.cedula)

    # Pagos operativos en jun/jul que tienen al menos una aplicacion a cuota
    # (abono o total a cualquier cuota).
    d_ini = date(2026, 6, 1)
    d_fin = date(2026, 7, 31)
    if fecha_corte < d_fin:
        d_fin = fecha_corte

    rows = db.execute(
        select(
            ced_expr.label("ced"),
            Pago.id.label("pago_id"),
            Pago.fecha_pago,
            Pago.monto_pagado,
            func.coalesce(func.sum(CuotaPago.monto_aplicado), 0).label("aplicado"),
        )
        .select_from(Pago)
        .join(Prestamo, Pago.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .join(CuotaPago, CuotaPago.pago_id == Pago.id)
        .where(
            Cliente.estado == "ACTIVO",
            estado_prestamo.in_(("APROBADO", "LIQUIDADO")),
            ced_expr.in_(list(cedulas)),
            pago_operativo,
            Pago.fecha_pago >= d_ini,
            Pago.fecha_pago <= d_fin,
        )
        .group_by(ced_expr, Pago.id, Pago.fecha_pago, Pago.monto_pagado)
    ).all()

    # ced -> mes -> monto (preferir monto_pagado del pago; si falta, aplicado)
    by_ced_mes: Dict[str, Dict[int, float]] = {c: {6: 0.0, 7: 0.0} for c in cedulas}
    pagos_vistos: Set[Tuple[str, int]] = set()
    for ced, pago_id, fecha_pago, monto_pagado, aplicado in rows:
        k = texto_cedula_comparable_bd(ced or "")
        if k not in by_ced_mes:
            continue
        if fecha_pago is None:
            continue
        fp = fecha_pago.date() if hasattr(fecha_pago, "date") else fecha_pago
        if fp.year != 2026 or fp.month not in (6, 7):
            continue
        key = (k, int(pago_id))
        if key in pagos_vistos:
            continue
        pagos_vistos.add(key)
        mon = float(monto_pagado or 0)
        if mon <= 0.009:
            mon = float(aplicado or 0)
        if mon <= 0.009:
            continue
        by_ced_mes[k][int(fp.month)] = round(by_ced_mes[k][int(fp.month)] + mon, 2)

    # Cedulas de la hoja sin filas de pago quedan en 0/0
    out: Dict[str, Dict[str, Any]] = {}
    for ced in cedulas:
        montos = by_ced_mes.get(ced, {6: 0.0, 7: 0.0})
        meses_info = []
        for _anio, mes in MESES_PERIODO:
            pagado = float(montos.get(mes, 0.0) or 0.0)
            cubierto = pagado > 0.009
            meses_info.append(
                {
                    "mes": mes,
                    "cubierto": cubierto,
                    "pagado": round(pagado, 2),
                    "motivo": "pago_calendario_mes" if cubierto else "sin_pago_calendario_mes",
                    "aporte": -1 if cubierto else 1,
                }
            )
        n_cubiertos = sum(1 for m in meses_info if m["cubierto"])
        n_descubiertos = sum(1 for m in meses_info if not m["cubierto"])
        delta_n = n_descubiertos - n_cubiertos
        delta_m = round(sum(float(m["pagado"]) for m in meses_info if m["pagado"] > 0.009), 2)
        out[ced] = {
            "neto_cuotas": float(delta_n),
            "neto_monto": delta_m,
            "detalle": meses_info,
        }
    return out


def actualizar_reporte_cuotas_jun_ago_drive(
    db: Session,
    *,
    dry_run: bool = False,
    spreadsheet_id: Optional[str] = None,
    tab_name: Optional[str] = None,
) -> Dict[str, Any]:
    from app.services.conciliacion_sheet_sync import (
        _build_sheets_service,
        _escape_sheet_title_for_range,
        _get_sheets_credentials,
        _resolve_sheet_title,
        _sheets_execute,
    )

    fecha_corte = FECHA_CORTE
    sid = (spreadsheet_id or _sheet_id()).strip()
    if not sid:
        raise RuntimeError("REPORTE_CUOTAS_JUN_AGO_SHEET_ID no configurado.")

    creds = _get_sheets_credentials()
    if creds is None:
        raise RuntimeError(
            "Sin credenciales Google (Sheets). Configure cuenta de servicio / OAuth."
        )
    service = _build_sheets_service(creds)

    tab_cfg = (
        tab_name
        if tab_name is not None
        else (getattr(settings, "REPORTE_CUOTAS_JUN_AGO_TAB_NAME", None) or "")
    ).strip()
    if tab_cfg:
        title = _resolve_sheet_title(service, sid, tab_cfg)
    else:
        meta = _sheets_execute(
            service.spreadsheets().get(
                spreadsheetId=sid, fields="sheets.properties.title"
            )
        )
        sheets = meta.get("sheets") or []
        if not sheets:
            raise RuntimeError("El spreadsheet no tiene pestanas.")
        title = sheets[0]["properties"]["title"]

    rng = f"{_escape_sheet_title_for_range(title)}!A:Z"
    resp = _sheets_execute(
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=sid,
            range=rng,
            majorDimension="ROWS",
            valueRenderOption="UNFORMATTED_VALUE",
        )
    )
    values: List[List[Any]] = resp.get("values") or []
    if not values:
        raise RuntimeError("La hoja no devolvio filas.")

    headers = [str(h) if h is not None else "" for h in values[0]]
    idx_ced = _pick_col(headers, "cedula", "cedula identidad", "nro cedula")
    if idx_ced is None:
        idx_ced = 0

    filas: List[Dict[str, Any]] = []
    claves: Set[str] = set()
    for row_i, row in enumerate(values[1:], start=2):
        row = list(row)
        while len(row) <= max(idx_ced, IDX_COL_E):
            row.append("")
        ced = texto_cedula_comparable_bd(str(row[idx_ced] or "").strip())
        if not ced:
            continue
        claves.add(ced)
        filas.append({"sheet_row": row_i, "cedula": ced})

    metricas = _delta_cobertura_por_cedula(db, claves, fecha_corte)
    updates: List[Dict[str, Any]] = []
    data_cells: List[Dict[str, Any]] = []
    esc = _escape_sheet_title_for_range(title)
    col_d = _col_index_to_a1(IDX_COL_D + 1)
    col_e = _col_index_to_a1(IDX_COL_E + 1)

    for f in filas:
        m = metricas.get(f["cedula"], {"neto_cuotas": 0.0, "neto_monto": 0.0})
        neto_n = int(m["neto_cuotas"])
        neto_m = round(float(m["neto_monto"]), 2)
        item = {
            **f,
            "neto_cuotas": neto_n,
            "neto_monto": neto_m,
            "detalle": m.get("detalle"),
        }
        updates.append(item)
        data_cells.append(
            {"range": f"{esc}!{col_d}{f['sheet_row']}", "values": [[neto_n]]}
        )
        data_cells.append(
            {"range": f"{esc}!{col_e}{f['sheet_row']}", "values": [[neto_m]]}
        )

    written = 0
    if not dry_run and data_cells:
        body = {"valueInputOption": "RAW", "data": data_cells}
        _sheets_execute(
            service.spreadsheets().values().batchUpdate(spreadsheetId=sid, body=body)
        )
        written = len(data_cells)
        logger.info(
            "[reporte_cuotas_jun_ago] escritas=%s filas=%s tab=%r",
            written,
            len(filas),
            title,
        )

    return {
        "spreadsheet_id": sid,
        "tab": title,
        "fecha_corte": fecha_corte.isoformat(),
        "meses": ["2026-06", "2026-07"],
        "fecha_desde": "2026-06-01",
        "fecha_hasta": fecha_corte.isoformat(),
        "dry_run": bool(dry_run),
        "filas_leidas": len(filas),
        "celdas_escritas": written,
        "columnas": {"neto_cuotas": "D", "neto_monto": "E"},
        "formula": (
            "D=(meses sin pago calendario)-(meses con pago a cualquier cuota); "
            "E=suma positiva de pagos jun+jul"
        ),
        "items": updates[:200],
        "items_total": len(updates),
    }
