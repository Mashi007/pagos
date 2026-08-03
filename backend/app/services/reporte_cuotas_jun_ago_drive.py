"""
REPORTE cuotas jun-ago: informe estatico que actualiza Google Drive.

Universo: solo cedulas de la hoja.
Escribe solo columnas D y E (delta del periodo; no reescribe la base).

Regla de signo (cobertura jun/jul 2026, corte 2026-08-02):
  Por cada mes, "cubierto" = cuota(s) de ese vencimiento pagadas a corte
  (cascada a cuotas viejas NO cubre el mes si esa cuota sigue impaga).
  Sin cuota de ese mes: cubierto=False si hay deuda viva; True si no hay deuda.

  Si hay ALGUN mes cubierto: D = -(cantidad de meses cubiertos)
    (ej. pago solo junio => -1; pago jun y jul => -2).
    Los meses no cubiertos NO suman en este caso.
  Si NINGUN mes cubierto: D = +(cantidad de meses no cubiertos)
    (ej. no pago jun ni jul => +2).

  E = signo(D) * monto asociado a los meses que entran en el conteo.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

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

FECHA_CORTE = date(2026, 8, 2)
# Meses del delta (anio, mes)
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


def _col_index_to_a1(col_1based: int) -> str:
    n = col_1based
    letters = []
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters.append(chr(65 + rem))
    return "".join(reversed(letters))


def _delta_cobertura_por_cedula(
    db: Session,
    cedulas: Set[str],
    fecha_corte: date = FECHA_CORTE,
) -> Dict[str, Dict[str, float]]:
    """
    D/E por cedula segun cobertura real de cuotas de junio y julio.
    """
    if not cedulas:
        return {}

    sub = _pagado_subq(fecha_corte + timedelta(days=1))
    pagado = _pagado_asof_expr(func.coalesce(sub.c.pagado_asof, 0), fecha_corte)
    saldo = func.greatest(Cuota.monto - pagado, 0)
    estado_prestamo = func.upper(func.trim(Prestamo.estado))
    ced_expr = expr_cedula_normalizada_para_comparar(Prestamo.cedula)

    rows = db.execute(
        select(
            ced_expr.label("ced"),
            Cuota.id.label("cuota_id"),
            Cuota.numero_cuota,
            Cuota.fecha_vencimiento,
            Cuota.monto,
            pagado.label("pagado_asof"),
            saldo.label("saldo"),
        )
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .outerjoin(sub, sub.c.cuota_id == Cuota.id)
        .where(
            Cliente.estado == "ACTIVO",
            estado_prestamo.in_(("APROBADO", "LIQUIDADO")),
            ced_expr.in_(list(cedulas)),
            Cuota.estado.is_distinct_from("CANCELADA"),
        )
        .order_by(ced_expr, Cuota.numero_cuota)
    ).all()

    by_ced: Dict[str, List[Dict[str, Any]]] = {c: [] for c in cedulas}
    for ced, _cid, _num, venc, monto, pagado_asof, saldo_v in rows:
        k = texto_cedula_comparable_bd(ced or "")
        if k not in by_ced:
            continue
        mon = float(monto or 0)
        pe = float(pagado_asof or 0)
        cubierta = pe >= (mon - 0.01)
        by_ced[k].append(
            {
                "venc": venc,
                "monto": mon,
                "saldo": round(float(saldo_v or 0), 2),
                "cubierta": cubierta,
            }
        )

    out: Dict[str, Dict[str, float]] = {}
    for ced, cuotas in by_ced.items():
        hay_deuda = any(not c["cubierta"] for c in cuotas)
        monto_tipico = 0.0
        for c in cuotas:
            if not c["cubierta"] and c["monto"] > 0:
                monto_tipico = c["monto"]
                break
        if monto_tipico <= 0 and cuotas:
            monto_tipico = float(cuotas[0]["monto"] or 0)

        meses_info = []  # {mes, cubierto, monto}
        for anio, mes in MESES_PERIODO:
            del_mes = [
                c
                for c in cuotas
                if c["venc"] is not None
                and int(c["venc"].year) == anio
                and int(c["venc"].month) == mes
            ]
            if del_mes:
                descubiertas = [c for c in del_mes if not c["cubierta"]]
                cubierto = len(descubiertas) == 0
                if cubierto:
                    monto_mes = sum(float(c["monto"] or 0) for c in del_mes)
                    motivo = "cuota_mes_cubierta"
                else:
                    monto_mes = sum(float(c["saldo"] or c["monto"] or 0) for c in descubiertas)
                    motivo = "cuota_mes_no_cubierta"
            else:
                # sin cuota de ese mes
                cubierto = not hay_deuda
                monto_mes = 0.0 if cubierto else monto_tipico
                motivo = "sin_cuota_mes_sin_deuda" if cubierto else "sin_cuota_mes_deuda_viva"
            meses_info.append(
                {"mes": mes, "cubierto": cubierto, "monto": round(monto_mes, 2), "motivo": motivo}
            )

        n_cubiertos = sum(1 for m in meses_info if m["cubierto"])
        n_descubiertos = sum(1 for m in meses_info if not m["cubierto"])
        if n_cubiertos > 0:
            # Solo cuentan los meses pagados/cubiertos (negativo)
            delta_n = -n_cubiertos
            delta_m = -sum(float(m["monto"]) for m in meses_info if m["cubierto"])
            detalle = [
                {**m, "aporte": -1 if m["cubierto"] else 0}
                for m in meses_info
            ]
        else:
            # Ningun mes cubierto: +1 por cada mes no cubierto
            delta_n = n_descubiertos
            delta_m = sum(float(m["monto"]) for m in meses_info if not m["cubierto"])
            detalle = [
                {**m, "aporte": 1 if not m["cubierto"] else 0}
                for m in meses_info
            ]

        out[ced] = {
            "neto_cuotas": float(delta_n),
            "neto_monto": round(delta_m, 2),
            "detalle": detalle,  # type: ignore[dict-item]
        }
    return out  # type: ignore[return-value]


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
            "Si algun mes cubierto: D=-(meses cubiertos); "
            "si ninguno: D=+(meses no cubiertos). E con el mismo signo."
        ),
        "items": updates[:200],
        "items_total": len(updates),
    }
