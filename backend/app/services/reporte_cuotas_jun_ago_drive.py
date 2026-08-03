"""
REPORTE cuotas jun-ago: informe estatico que actualiza Google Drive.

Periodo fijo: 2026-06-01 .. 2026-08-02.
Universo: solo cedulas presentes en la hoja.
Escribe unicamente columnas D y E.

Regla (cuotas con vencimiento en el periodo):
  impagas = vencidas en rango y sin pagar a fecha_hasta
  pagadas = vencidas en rango y pagadas a fecha_hasta
  D = pagadas - impagas   (pago resta, impaga suma invertida al ejemplo de negocio)
  E = monto_pagadas - monto_impagas
  Ejemplo: pago 3 y no pago 4 => D = 3 - 4 = -1
"""
from __future__ import annotations

import logging
import re
import unicodedata
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.utils.cedula_almacenamiento import (
    expr_cedula_normalizada_para_comparar,
    texto_cedula_comparable_bd,
)

logger = logging.getLogger(__name__)

FECHA_DESDE_FIJA = date(2026, 6, 1)
FECHA_HASTA_FIJA = date(2026, 8, 2)
_DEFAULT_SHEET_ID = "1_Qean5MoSc1vWy6hMAAqOcMJeZzn9iUspJTqsOqZEqs"
# Columnas D y E (0-based 3 y 4)
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
    return re.sub(r"\\s+", " ", s)


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


def _pagado_asof_expr(pagado_join, fecha: date):
    return case(
        (
            and_(
                pagado_join <= 0.009,
                Cuota.fecha_pago.is_not(None),
                Cuota.fecha_pago <= fecha,
            ),
            Cuota.monto,
        ),
        else_=pagado_join,
    )


def _pagado_subq(limite_excl):
    estado_pago = func.upper(func.trim(func.coalesce(Pago.estado, "")))
    pago_operativo = and_(
        ~estado_pago.like("ANULADO%"),
        estado_pago.is_distinct_from("DUPLICADO"),
    )
    return (
        select(
            CuotaPago.cuota_id.label("cuota_id"),
            func.coalesce(func.sum(CuotaPago.monto_aplicado), 0).label("pagado_asof"),
        )
        .select_from(CuotaPago)
        .join(Pago, Pago.id == CuotaPago.pago_id)
        .where(Pago.fecha_pago < limite_excl, pago_operativo)
        .group_by(CuotaPago.cuota_id)
        .subquery()
    )


def _metricas_periodo_por_cedula(
    db: Session,
    cedulas: Set[str],
    fecha_desde: date = FECHA_DESDE_FIJA,
    fecha_hasta: date = FECHA_HASTA_FIJA,
) -> Dict[str, Dict[str, float]]:
    """Impagas/pagadas con vencimiento en [desde, hasta], estado a fecha_hasta."""
    if not cedulas:
        return {}
    sub = _pagado_subq(fecha_hasta + timedelta(days=1))
    pagado = _pagado_asof_expr(func.coalesce(sub.c.pagado_asof, 0), fecha_hasta)
    saldo = func.greatest(Cuota.monto - pagado, 0)
    es_pagada = pagado >= (Cuota.monto - 0.01)
    es_impaga = and_(
        pagado < (Cuota.monto - 0.01),
        Cuota.estado.is_distinct_from("CANCELADA"),
    )
    estado_prestamo = func.upper(func.trim(Prestamo.estado))
    ced_expr = expr_cedula_normalizada_para_comparar(Prestamo.cedula)
    base_where = and_(
        Cliente.estado == "ACTIVO",
        estado_prestamo.in_(("APROBADO", "LIQUIDADO")),
        ced_expr.in_(list(cedulas)),
        Cuota.fecha_vencimiento >= fecha_desde,
        Cuota.fecha_vencimiento <= fecha_hasta,
        Cuota.estado.is_distinct_from("CANCELADA"),
    )

    rows_imp = db.execute(
        select(
            ced_expr.label("ced"),
            func.count(Cuota.id),
            func.coalesce(func.sum(saldo), 0),
        )
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .outerjoin(sub, sub.c.cuota_id == Cuota.id)
        .where(base_where, es_impaga)
        .group_by(ced_expr)
    ).all()

    rows_pag = db.execute(
        select(
            ced_expr.label("ced"),
            func.count(Cuota.id),
            func.coalesce(func.sum(Cuota.monto), 0),
        )
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .outerjoin(sub, sub.c.cuota_id == Cuota.id)
        .where(base_where, es_pagada)
        .group_by(ced_expr)
    ).all()

    out: Dict[str, Dict[str, float]] = {
        c: {
            "n_impagas": 0.0,
            "n_pagadas": 0.0,
            "m_impagas": 0.0,
            "m_pagadas": 0.0,
        }
        for c in cedulas
    }
    for ced, n, m in rows_imp:
        k = texto_cedula_comparable_bd(ced or "")
        if k in out:
            out[k]["n_impagas"] = float(n or 0)
            out[k]["m_impagas"] = round(float(m or 0), 2)
    for ced, n, m in rows_pag:
        k = texto_cedula_comparable_bd(ced or "")
        if k in out:
            out[k]["n_pagadas"] = float(n or 0)
            out[k]["m_pagadas"] = round(float(m or 0), 2)
    return out


def _col_index_to_a1(col_1based: int) -> str:
    n = col_1based
    letters = []
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters.append(chr(65 + rem))
    return "".join(reversed(letters))


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

    fecha_desde = FECHA_DESDE_FIJA
    fecha_hasta = FECHA_HASTA_FIJA
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
        idx_ced = 0  # columna A por defecto

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

    metricas = _metricas_periodo_por_cedula(db, claves, fecha_desde, fecha_hasta)
    updates: List[Dict[str, Any]] = []
    data_cells: List[Dict[str, Any]] = []
    esc = _escape_sheet_title_for_range(title)
    col_d = _col_index_to_a1(IDX_COL_D + 1)
    col_e = _col_index_to_a1(IDX_COL_E + 1)

    for f in filas:
        m = metricas.get(
            f["cedula"],
            {"n_impagas": 0.0, "n_pagadas": 0.0, "m_impagas": 0.0, "m_pagadas": 0.0},
        )
        n_imp = int(m["n_impagas"])
        n_pag = int(m["n_pagadas"])
        # D = pagadas - impagas (ej. pago 3, no pago 4 => -1)
        neto_n = n_pag - n_imp
        neto_m = round(float(m["m_pagadas"]) - float(m["m_impagas"]), 2)
        item = {
            **f,
            "n_impagas": n_imp,
            "n_pagadas": n_pag,
            "neto_cuotas": neto_n,
            "neto_monto": neto_m,
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
        "fecha_desde": fecha_desde.isoformat(),
        "fecha_hasta": fecha_hasta.isoformat(),
        "dry_run": bool(dry_run),
        "filas_leidas": len(filas),
        "celdas_escritas": written,
        "columnas": {"neto_cuotas": "D", "neto_monto": "E"},
        "formula": "D = pagadas - impagas; E = monto_pagadas - monto_impagas (venc. en periodo)",
        "items": updates[:200],
        "items_total": len(updates),
    }
