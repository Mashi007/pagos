"""
Actualiza columnas Cuotas y Monto (col C) de una hoja Google por cedula.

Regla (idempotente):
  Escribe el corte absoluto de BD a fecha_hasta:
    Cuotas = count(impagas con vencimiento <= fecha_hasta)
    Monto  = saldo impagas a fecha_hasta

No se aplica un delta sobre el valor actual de la hoja: re-ejecutar el mismo
corte (p. ej. al regenerar Impagas) no infla Cuotas/Monto.
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

_DEFAULT_SHEET_ID = "1Xu8RINcL1abpnjppeDIYhmb1wL60zmYYhJU2voP27d8"


def _sheet_id() -> str:
    return (
        getattr(settings, "CUOTAS_HOJA_PERIODO_SHEET_ID", None) or _DEFAULT_SHEET_ID
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


def _deltas_por_cedula(
    db: Session,
    fecha_desde: date,
    fecha_hasta: date,
    cedulas: Set[str],
) -> Dict[str, Dict[str, int]]:
    if not cedulas:
        return {}
    if fecha_desde > fecha_hasta:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde

    dia_antes = fecha_desde - timedelta(days=1)
    sub_hasta = _pagado_subq(fecha_hasta + timedelta(days=1))
    sub_antes = _pagado_subq(fecha_desde)

    pagado_hasta = _pagado_asof_expr(func.coalesce(sub_hasta.c.pagado_asof, 0), fecha_hasta)
    pagado_antes = _pagado_asof_expr(func.coalesce(sub_antes.c.pagado_asof, 0), dia_antes)

    impaga_hasta = and_(
        pagado_hasta < (Cuota.monto - 0.01),
        Cuota.estado.is_distinct_from("CANCELADA"),
    )
    impaga_antes = and_(
        pagado_antes < (Cuota.monto - 0.01),
        Cuota.estado.is_distinct_from("CANCELADA"),
    )
    pagada_hasta = pagado_hasta >= (Cuota.monto - 0.01)

    estado_prestamo = func.upper(func.trim(Prestamo.estado))
    ced_expr = expr_cedula_normalizada_para_comparar(Prestamo.cedula)
    claves = list(cedulas)

    rows_imp = db.execute(
        select(ced_expr.label("ced"), func.count(Cuota.id))
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .outerjoin(sub_hasta, sub_hasta.c.cuota_id == Cuota.id)
        .where(
            Cliente.estado == "ACTIVO",
            estado_prestamo.in_(("APROBADO", "LIQUIDADO")),
            ced_expr.in_(claves),
            impaga_hasta,
            Cuota.fecha_vencimiento >= fecha_desde,
            Cuota.fecha_vencimiento <= fecha_hasta,
        )
        .group_by(ced_expr)
    ).all()

    rows_cerr = db.execute(
        select(ced_expr.label("ced"), func.count(Cuota.id))
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .outerjoin(sub_hasta, sub_hasta.c.cuota_id == Cuota.id)
        .outerjoin(sub_antes, sub_antes.c.cuota_id == Cuota.id)
        .where(
            Cliente.estado == "ACTIVO",
            estado_prestamo.in_(("APROBADO", "LIQUIDADO")),
            ced_expr.in_(claves),
            Cuota.fecha_vencimiento < fecha_desde,
            Cuota.estado.is_distinct_from("CANCELADA"),
            impaga_antes,
            pagada_hasta,
        )
        .group_by(ced_expr)
    ).all()

    out: Dict[str, Dict[str, int]] = {
        c: {"impagas_periodo": 0, "cerradas_previas": 0} for c in cedulas
    }
    for ced, n in rows_imp:
        k = texto_cedula_comparable_bd(ced or "")
        if k in out:
            out[k]["impagas_periodo"] = int(n or 0)
    for ced, n in rows_cerr:
        k = texto_cedula_comparable_bd(ced or "")
        if k in out:
            out[k]["cerradas_previas"] = int(n or 0)
    return out



def _impagas_corte_por_cedula(
    db: Session,
    fecha_hasta: date,
    cedulas: Set[str],
) -> Dict[str, Dict[str, float]]:
    if not cedulas:
        return {}
    sub_hasta = _pagado_subq(fecha_hasta + timedelta(days=1))
    pagado_hasta = _pagado_asof_expr(func.coalesce(sub_hasta.c.pagado_asof, 0), fecha_hasta)
    impaga_hasta = and_(
        pagado_hasta < (Cuota.monto - 0.01),
        Cuota.estado.is_distinct_from("CANCELADA"),
    )
    saldo = func.greatest(Cuota.monto - pagado_hasta, 0)
    estado_prestamo = func.upper(func.trim(Prestamo.estado))
    ced_expr = expr_cedula_normalizada_para_comparar(Prestamo.cedula)
    rows = db.execute(
        select(
            ced_expr.label("ced"),
            func.count(Cuota.id).label("cuotas"),
            func.coalesce(func.sum(saldo), 0).label("monto"),
        )
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .outerjoin(sub_hasta, sub_hasta.c.cuota_id == Cuota.id)
        .where(
            Cliente.estado == "ACTIVO",
            estado_prestamo.in_(("APROBADO", "LIQUIDADO")),
            ced_expr.in_(list(cedulas)),
            impaga_hasta,
            Cuota.fecha_vencimiento <= fecha_hasta,
        )
        .group_by(ced_expr)
    ).all()
    out: Dict[str, Dict[str, float]] = {
        c: {"cuotas_bd": 0.0, "monto_bd": 0.0} for c in cedulas
    }
    for ced, n, m in rows:
        k = texto_cedula_comparable_bd(ced or "")
        if k in out:
            out[k]["cuotas_bd"] = float(n or 0)
            out[k]["monto_bd"] = round(float(m or 0), 2)
    return out


def _parse_monto_cell(raw: Any) -> Optional[float]:
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        return round(float(raw), 2)
    s = str(raw).strip().replace(",", "").replace("$", "")
    if not s:
        return None
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def _monto_alineado(nuevo_cuotas: int, cuotas_bd: float, monto_bd: float) -> float:
    """Compat: si nuevo == cuotas_bd devuelve monto_bd; si no, prorratea."""
    n_bd = int(cuotas_bd or 0)
    m_bd = float(monto_bd or 0)
    if nuevo_cuotas <= 0:
        return 0.0
    if n_bd > 0 and m_bd > 0:
        return round(nuevo_cuotas * (m_bd / n_bd), 2)
    return round(m_bd, 2)


def _valores_sync_desde_corte(cort: Dict[str, float]) -> Tuple[int, float]:
    """
    Valores a escribir en la hoja a partir del corte BD (idempotente).

    Re-aplicar el mismo corte sobre una hoja ya sincronizada no debe cambiar
    Cuotas ni Monto.
    """
    cuotas = max(0, int(cort.get("cuotas_bd") or 0))
    monto = round(float(cort.get("monto_bd") or 0), 2)
    if cuotas <= 0:
        return 0, 0.0
    return cuotas, monto


def _parse_cuotas_cell(raw: Any) -> Optional[int]:
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    s = str(raw).strip().replace(",", ".")
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _col_index_to_a1(col_1based: int) -> str:
    n = col_1based
    letters = []
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters.append(chr(65 + rem))
    return "".join(reversed(letters))


def actualizar_cuotas_hoja_por_periodo(
    db: Session,
    fecha_desde: date,
    fecha_hasta: date,
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

    sid = (spreadsheet_id or _sheet_id()).strip()
    if not sid:
        raise RuntimeError("CUOTAS_HOJA_PERIODO_SHEET_ID / spreadsheet_id no configurado.")

    creds = _get_sheets_credentials()
    if creds is None:
        raise RuntimeError(
            "Sin credenciales Google (Sheets). Configure Informe de pagos / cuenta de servicio."
        )
    service = _build_sheets_service(creds)

    tab_cfg = (
        tab_name
        if tab_name is not None
        else (getattr(settings, "CUOTAS_HOJA_PERIODO_TAB_NAME", None) or "")
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
    idx_cuo = _pick_col(headers, "cuotas", "cuota", "cuotas impagas", "impagas")
    idx_mon = _pick_col(
        headers, "monto", "monto impagas", "valor", "importe", "saldo", "dinero"
    )
    if idx_mon is None:
        idx_mon = 2  # columna C
    if idx_ced is None:
        raise RuntimeError(f"No se encontro columna Cedula en headers={headers!r}")
    if idx_cuo is None:
        raise RuntimeError(f"No se encontro columna Cuotas en headers={headers!r}")
    if idx_mon == idx_cuo:
        idx_mon = 2 if idx_cuo != 2 else 3

    max_idx = max(idx_ced, idx_cuo, idx_mon)
    filas: List[Dict[str, Any]] = []
    claves: Set[str] = set()
    for row_i, row in enumerate(values[1:], start=2):
        row = list(row)
        while len(row) <= max_idx:
            row.append("")
        ced_raw = row[idx_ced]
        ced = texto_cedula_comparable_bd(str(ced_raw or "").strip())
        if not ced:
            continue
        base = _parse_cuotas_cell(row[idx_cuo])
        if base is None:
            continue
        monto_antes = _parse_monto_cell(row[idx_mon])
        claves.add(ced)
        filas.append(
            {
                "sheet_row": row_i,
                "cedula": ced,
                "cuotas_antes": int(base),
                "monto_antes": monto_antes,
            }
        )

    deltas = _deltas_por_cedula(db, fecha_desde, fecha_hasta, claves)
    cortes = _impagas_corte_por_cedula(db, fecha_hasta, claves)
    updates: List[Dict[str, Any]] = []
    data_cells: List[Dict[str, Any]] = []

    def _cell(col_idx: int, row_i: int, value: Any) -> Dict[str, Any]:
        col_letter = _col_index_to_a1(col_idx + 1)
        cell_range = f"{_escape_sheet_title_for_range(title)}!{col_letter}{row_i}"
        return {"range": cell_range, "values": [[value]]}

    for f in filas:
        d = deltas.get(f["cedula"], {"impagas_periodo": 0, "cerradas_previas": 0})
        cort = cortes.get(f["cedula"], {"cuotas_bd": 0.0, "monto_bd": 0.0})
        imp_p = int(d["impagas_periodo"])
        cerr = int(d["cerradas_previas"])
        # Corte absoluto BD a fecha_hasta (no delta sobre cuotas_antes).
        nuevo, monto_nuevo = _valores_sync_desde_corte(cort)
        monto_antes = f.get("monto_antes")
        cambio_cuotas = nuevo != int(f["cuotas_antes"])
        cambio_monto = (
            monto_antes is None or abs(float(monto_antes) - monto_nuevo) > 0.009
        )
        item = {
            **f,
            "impagas_periodo": imp_p,
            "cerradas_previas": cerr,
            "cuotas_despues": nuevo,
            "monto_despues": monto_nuevo,
            "cuotas_bd": int(cort["cuotas_bd"]),
            "monto_bd": float(cort["monto_bd"]),
            "cambio_cuotas": cambio_cuotas,
            "cambio_monto": cambio_monto,
            "cambio": cambio_cuotas or cambio_monto,
        }
        updates.append(item)
        if cambio_cuotas:
            data_cells.append(_cell(idx_cuo, f["sheet_row"], nuevo))
        if cambio_monto:
            data_cells.append(_cell(idx_mon, f["sheet_row"], monto_nuevo))

    written = 0
    if not dry_run and data_cells:
        body = {"valueInputOption": "RAW", "data": data_cells}
        _sheets_execute(
            service.spreadsheets().values().batchUpdate(spreadsheetId=sid, body=body)
        )
        written = len(data_cells)
        logger.info(
            "[cuotas_hoja_periodo] escritas=%s tab=%r periodo=%s..%s col_monto=%s",
            written,
            title,
            fecha_desde,
            fecha_hasta,
            _col_index_to_a1(idx_mon + 1),
        )

    cambiaron = sum(1 for u in updates if u["cambio"])
    return {
        "spreadsheet_id": sid,
        "tab": title,
        "fecha_desde": fecha_desde.isoformat(),
        "fecha_hasta": fecha_hasta.isoformat(),
        "dry_run": bool(dry_run),
        "filas_leidas": len(filas),
        "filas_cambiaron": cambiaron,
        "celdas_escritas": written,
        "columna_cedula": headers[idx_ced],
        "columna_cuotas": headers[idx_cuo],
        "columna_monto": (
            headers[idx_mon]
            if idx_mon < len(headers) and headers[idx_mon]
            else f"columna_{_col_index_to_a1(idx_mon + 1)}"
        ),
        "columna_monto_letra": _col_index_to_a1(idx_mon + 1),
        "formula": "cuotas_bd/monto_bd a fecha_hasta (idempotente); deltas solo informativos",
        "items": updates[:200],
        "items_total": len(updates),
    }
