"""
Reportes de cartera.
"""
import calendar
import io
from datetime import date, timedelta
from typing import List, Optional, Set

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import and_, case, func, select, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.models.cuota_pago import CuotaPago

from app.api.v1.endpoints.reportes_utils import _safe_float, _parse_fecha, _periodos_desde_filtros
from app.utils.cedula_almacenamiento import expr_cedula_normalizada_para_comparar

router = APIRouter(dependencies=[Depends(get_current_user)])


def _datos_cartera(db: Session, fecha_corte: date) -> dict:
    """Obtiene datos para reporte de cartera a una fecha de corte (solo clientes ACTIVOS)."""
    cuotas_pendientes = (
        select(func.coalesce(func.sum(Cuota.monto), 0))
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.is_(None),
        )
    )
    cartera_total = _safe_float(db.scalar(cuotas_pendientes) or 0)

    prestamos_activos = db.scalar(
        select(func.count())
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(Cliente.estado == "ACTIVO", Prestamo.estado == "APROBADO")
    ) or 0

    subq_mora = (
        select(Cuota.prestamo_id)
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento + text("INTERVAL '4 months 1 day'") <= fecha_corte,
        )
        .distinct()
    )
    prestamos_mora = db.scalar(select(func.count()).select_from(subq_mora.subquery())) or 0

    mora_total = _safe_float(
        db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                Cliente.estado == "ACTIVO",
                Prestamo.estado == "APROBADO",
                Cuota.fecha_pago.is_(None),
                Cuota.fecha_vencimiento + text("INTERVAL '4 months 1 day'") <= fecha_corte,
            )
        )
        or 0
    )

    distribucion_por_monto = [
        {"rango": "0 - 5.000", "cantidad": 0, "monto": 0},
        {"rango": "5.001 - 15.000", "cantidad": 0, "monto": 0},
        {"rango": "15.001 - 50.000", "cantidad": 0, "monto": 0},
        {"rango": "> 50.000", "cantidad": 0, "monto": 0},
    ]
    saldos = db.execute(
        select(Cuota.prestamo_id, func.sum(Cuota.monto).label("saldo"))
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.is_(None),
        )
        .group_by(Cuota.prestamo_id)
    ).all()
    for pid, saldo in saldos:
        s = _safe_float(saldo)
        if s <= 5000:
            distribucion_por_monto[0]["cantidad"] += 1
            distribucion_por_monto[0]["monto"] += s
        elif s <= 15000:
            distribucion_por_monto[1]["cantidad"] += 1
            distribucion_por_monto[1]["monto"] += s
        elif s <= 50000:
            distribucion_por_monto[2]["cantidad"] += 1
            distribucion_por_monto[2]["monto"] += s
        else:
            distribucion_por_monto[3]["cantidad"] += 1
            distribucion_por_monto[3]["monto"] += s

    distribucion_por_mora: List[dict] = []
    for label, dias_min, dias_max in [
        ("1-30 días", 1, 30),
        ("31-60 días", 31, 60),
        ("61-89 días", 61, 89),
        ("4+ meses (moroso)", 121, 9999),
    ]:
        delta_min = fecha_corte - timedelta(days=dias_max)
        delta_max = fecha_corte - timedelta(days=dias_min)
        q = (
            select(func.count(Cuota.id), func.coalesce(func.sum(Cuota.monto), 0))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                Cliente.estado == "ACTIVO",
                Prestamo.estado == "APROBADO",
                Cuota.fecha_pago.is_(None),
                Cuota.fecha_vencimiento <= delta_max,
                Cuota.fecha_vencimiento >= delta_min,
            )
        )
        row = db.execute(q).one_or_none()
        cnt = (row[0] or 0) if row else 0
        monto = _safe_float(row[1] or 0) if row else 0
        distribucion_por_mora.append({"rango": label, "cantidad": cnt, "monto_total": monto})

    return {
        "fecha_corte": fecha_corte.isoformat(),
        "cartera_total": cartera_total,
        "capital_pendiente": cartera_total,
        "intereses_pendientes": 0,
        "mora_total": mora_total,
        "cantidad_prestamos_activos": prestamos_activos,
        "cantidad_prestamos_mora": prestamos_mora,
        "distribucion_por_monto": distribucion_por_monto,
        "distribucion_por_mora": distribucion_por_mora,
    }


def _cartera_por_periodos(db: Session, periodos: List[tuple]) -> dict:
    """Genera datos cartera para lista de (año, mes)."""
    resultado: dict = {"meses": []}
    for (ano, mes) in periodos:
        inicio = date(ano, mes, 1)
        _, ultimo = calendar.monthrange(ano, mes)
        fin = date(ano, mes, ultimo)

        rows = db.execute(
            select(
                func.extract("day", Cuota.fecha_vencimiento).label("dia"),
                func.coalesce(func.sum(Cuota.monto), 0).label("monto_cobrar"),
                func.count(Cuota.id).label("cantidad_cuotas"),
            )
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                Cliente.estado == "ACTIVO",
                Prestamo.estado == "APROBADO",
                Cuota.fecha_pago.is_(None),
                Cuota.fecha_vencimiento >= inicio,
                Cuota.fecha_vencimiento <= fin,
            )
            .group_by(func.extract("day", Cuota.fecha_vencimiento))
            .order_by(func.extract("day", Cuota.fecha_vencimiento))
        ).fetchall()

        por_dia: dict = {}
        for r in rows:
            d = int(r.dia) if r.dia is not None else 0
            por_dia[d] = {
                "cantidad_cuotas": r.cantidad_cuotas or 0,
                "monto_cobrar": round(_safe_float(r.monto_cobrar), 2),
            }

        items: List[dict] = []
        for d in range(1, ultimo + 1):
            data = por_dia.get(d, {"cantidad_cuotas": 0, "monto_cobrar": 0})
            items.append({
                "dia": d,
                "cantidad_cuotas": data["cantidad_cuotas"],
                "monto_cobrar": data["monto_cobrar"],
            })

        resultado["meses"].append({
            "mes": mes,
            "ano": ano,
            "label": f"{mes:02d}/{ano}",
            "items": items,
        })

    return resultado


@router.get("/cartera/por-mes")
def get_cartera_por_mes(
    db: Session = Depends(get_db),
    meses: int = Query(12, ge=1, le=24, description="Cantidad de meses hacia atrás"),
    anos: Optional[str] = Query(None, description="Años separados por coma, ej: 2023,2024"),
    meses_list: Optional[str] = Query(None, description="Meses 1-12 separados por coma, ej: 1,2,3"),
):
    """Cuentas por cobrar: una pestaña por mes (MM/YYYY). Por día del mes: cuotas por cobrar ese día."""
    periodos = _periodos_desde_filtros(anos, meses_list, meses)
    return _cartera_por_periodos(db, periodos)


@router.get("/cartera")
def get_reporte_cartera(
    db: Session = Depends(get_db),
    fecha_corte: Optional[str] = Query(None, description="Fecha de corte YYYY-MM-DD"),
):
    """Reporte de cartera en JSON. Datos reales desde BD."""
    fc = _parse_fecha(fecha_corte)
    return _datos_cartera(db, fc)


def _generar_excel_cartera_por_mes(data_por_mes: dict) -> bytes:
    """Genera Excel con una pestaña por mes (MM/YYYY)."""
    import openpyxl

    wb = openpyxl.Workbook()
    meses_data = data_por_mes.get("meses", [])
    meses_es = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    for idx, mes_data in enumerate(meses_data):
        mes = mes_data.get("mes", 1)
        ano = mes_data.get("ano", date.today().year)
        mes_nombre = meses_es.get(mes, "")
        label = mes_data.get("label", f"{mes:02d}/{ano}")
        sheet_name = f"{mes_nombre} {ano}"[:31]

        if idx == 0:
            ws = wb.active
            ws.title = sheet_name
        else:
            ws = wb.create_sheet(title=sheet_name)

        ws.append(["Reporte de Cartera", label])
        ws.append(["Cuotas por cobrar por día del mes"])
        ws.append([])
        ws.append(["Día", "Cuotas por cobrar", "Monto ($)"])

        for item in mes_data.get("items", []):
            row_num = ws.max_row + 1
            ws.append([
                item.get("dia", 0),
                item.get("cantidad_cuotas", 0),
                item.get("monto_cobrar", 0)
            ])
            cell = ws.cell(row=row_num, column=3)
            cell.number_format = '$#,##0.00'

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _generar_excel_cartera(data: dict) -> bytes:
    """Excel clásico de cartera (resumen + distribuciones)."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Cartera"
    ws.append(["Reporte de Cartera", data.get("fecha_corte", "")])
    ws.append([])
    ws.append(["Indicador", "Valor"])
    ws.append(["Cartera total", data.get("cartera_total", 0)])
    ws.append(["Capital pendiente", data.get("capital_pendiente", 0)])
    ws.append(["Mora total", data.get("mora_total", 0)])
    ws.append(["Préstamos activos", data.get("cantidad_prestamos_activos", 0)])
    ws.append(["Préstamos en mora", data.get("cantidad_prestamos_mora", 0)])
    ws.append([])
    ws.append(["Distribución por monto"])
    ws.append(["Rango", "Cantidad", "Monto"])
    for r in data.get("distribucion_por_monto", []):
        ws.append([r.get("rango", ""), r.get("cantidad", 0), r.get("monto", 0)])
    ws2 = wb.create_sheet("Mora")
    ws2.append(["Rango", "Cantidad", "Monto total"])
    for r in data.get("distribucion_por_mora", []):
        ws2.append([r.get("rango", ""), r.get("cantidad", 0), r.get("monto_total", 0)])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _generar_pdf_cartera(data: dict) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("Reporte de Cartera", styles["Title"]))
    story.append(Paragraph(f"Fecha de corte: {data.get('fecha_corte', '')}", styles["Normal"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Resumen", styles["Heading2"]))
    resumen = [
        ["Cartera total", str(data.get("cartera_total", 0))],
        ["Capital pendiente", str(data.get("capital_pendiente", 0))],
        ["Mora total", str(data.get("mora_total", 0))],
        ["Préstamos activos", str(data.get("cantidad_prestamos_activos", 0))],
        ["Préstamos en mora", str(data.get("cantidad_prestamos_mora", 0))],
    ]
    t = Table(resumen)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), "#e0e0e0"), ("GRID", (0, 0), (-1, -1), 0.5, "#ccc")]))
    story.append(t)
    story.append(Spacer(1, 12))
    story.append(Paragraph("Distribución por monto", styles["Heading2"]))
    rows = [["Rango", "Cantidad", "Monto"]]
    for r in data.get("distribucion_por_monto", []):
        rows.append([r.get("rango", ""), str(r.get("cantidad", 0)), str(r.get("monto", 0))])
    t2 = Table(rows)
    t2.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), "#e0e0e0"), ("GRID", (0, 0), (-1, -1), 0.5, "#ccc")]))
    story.append(t2)
    doc.build(story)
    return buf.getvalue()




def _agg_impagas_en_fecha(
    db: Session,
    fecha: date,
    cedulas_norm: Optional[Set[str]] = None,
) -> dict:
    """
    Snapshot a la fecha: cuotas impagas con fecha_vencimiento <= fecha.
    Impaga = no cubierta al 100% (tol 0.01); excluye CANCELADA.
    Solo prestamos APROBADO (excluye LIQUIDADO, DESISTIMIENTO y demas estados).
    Si cedulas_norm: solo esas cedulas (universo Aseguradora u otro).
    """
    if cedulas_norm is not None and len(cedulas_norm) == 0:
        return {}
    total_pagado_n = func.coalesce(Cuota.total_pagado, 0)
    impaga = and_(
        total_pagado_n < (Cuota.monto - 0.01),
        Cuota.estado.is_distinct_from("CANCELADA"),
    )
    saldo_cuota = func.greatest(Cuota.monto - total_pagado_n, 0)
    prestamo_aprobado = func.upper(func.trim(Prestamo.estado)) == "APROBADO"
    where_parts = [
        Cliente.estado == "ACTIVO",
        prestamo_aprobado,
        impaga,
        Cuota.fecha_vencimiento <= fecha,
    ]
    if cedulas_norm is not None:
        where_parts.append(
            expr_cedula_normalizada_para_comparar(Prestamo.cedula).in_(list(cedulas_norm))
        )
    rows = db.execute(
        select(
            Prestamo.id.label("prestamo_id"),
            Prestamo.cedula,
            Prestamo.nombres,
            func.count(Cuota.id).label("cuotas"),
            func.coalesce(func.sum(saldo_cuota), 0).label("monto"),
        )
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(*where_parts)
        .group_by(Prestamo.id, Prestamo.cedula, Prestamo.nombres)
    ).fetchall()
    out: dict = {}
    for r in rows:
        out[int(r.prestamo_id)] = {
            "prestamo_id": int(r.prestamo_id),
            "cedula": (r.cedula or "").strip(),
            "nombres": (r.nombres or "").strip(),
            "cuotas": int(r.cuotas or 0),
            "monto": round(_safe_float(r.monto), 2),
        }
    return out



def _agg_impagas_en_fecha_historico(
    db: Session,
    fecha: date,
    cedulas_norm: Optional[Set[str]] = None,
) -> dict:
    """
    Corte historico real a `fecha` (Aseguradora).

    Pagado a la fecha = suma de cuota_pagos cuyo pago.fecha_pago <= fecha
    (excluye ANULADO*/DUPLICADO). Si no hay articulos pero cuota.fecha_pago <= fecha,
    se considera pagada al 100%.

    Impaga: vencimiento <= fecha, no CANCELADA, pagado_asof < monto - 0.01.
    Saldo = max(monto - pagado_asof, 0).
    """
    if cedulas_norm is not None and len(cedulas_norm) == 0:
        return {}

    # Limite exclusivo: todos los timestamps del dia `fecha`
    limite = fecha + timedelta(days=1)
    estado_pago = func.upper(func.trim(func.coalesce(Pago.estado, "")))
    pago_operativo = and_(
        ~estado_pago.like("ANULADO%"),
        estado_pago.is_distinct_from("DUPLICADO"),
    )
    pagado_subq = (
        select(
            CuotaPago.cuota_id.label("cuota_id"),
            func.coalesce(func.sum(CuotaPago.monto_aplicado), 0).label("pagado_asof"),
        )
        .select_from(CuotaPago)
        .join(Pago, Pago.id == CuotaPago.pago_id)
        .where(
            Pago.fecha_pago < limite,
            pago_operativo,
        )
        .group_by(CuotaPago.cuota_id)
        .subquery()
    )

    pagado_join = func.coalesce(pagado_subq.c.pagado_asof, 0)
    # Legacy: cuota marcada pagada en/antes de la fecha sin filas en cuota_pagos
    pagado_asof = case(
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
    impaga = and_(
        pagado_asof < (Cuota.monto - 0.01),
        Cuota.estado.is_distinct_from("CANCELADA"),
    )
    saldo_cuota = func.greatest(Cuota.monto - pagado_asof, 0)
    prestamo_aprobado = func.upper(func.trim(Prestamo.estado)) == "APROBADO"
    where_parts = [
        Cliente.estado == "ACTIVO",
        prestamo_aprobado,
        impaga,
        Cuota.fecha_vencimiento <= fecha,
    ]
    if cedulas_norm is not None:
        where_parts.append(
            expr_cedula_normalizada_para_comparar(Prestamo.cedula).in_(list(cedulas_norm))
        )

    rows = db.execute(
        select(
            Prestamo.id.label("prestamo_id"),
            Prestamo.cedula,
            Prestamo.nombres,
            func.count(Cuota.id).label("cuotas"),
            func.coalesce(func.sum(saldo_cuota), 0).label("monto"),
        )
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .outerjoin(pagado_subq, pagado_subq.c.cuota_id == Cuota.id)
        .where(*where_parts)
        .group_by(Prestamo.id, Prestamo.cedula, Prestamo.nombres)
    ).fetchall()

    out: dict = {}
    for r in rows:
        out[int(r.prestamo_id)] = {
            "prestamo_id": int(r.prestamo_id),
            "cedula": (r.cedula or "").strip(),
            "nombres": (r.nombres or "").strip(),
            "cuotas": int(r.cuotas or 0),
            "monto": round(_safe_float(r.monto), 2),
        }
    return out


def _ultimo_dia_mes(anio: int, mes: int) -> date:
    return date(anio, mes, calendar.monthrange(anio, mes)[1])


def _pct_variacion(actual: float, base: float) -> Optional[float]:
    """Variacion intermensual %. None = no comparable (base ~0 y actual > 0)."""
    if abs(base) < 0.005:
        if abs(actual) < 0.005:
            return 0.0
        return None
    return round(((actual - base) / abs(base)) * 100.0, 2)


def _serie_mensual_impagas(
    db: Session,
    n_meses: int = 6,
    ref: Optional[date] = None,
    cuotas_impagas_min: int = 1,
    cuotas_impagas_max: int = 15,
    cedulas_norm: Optional[Set[str]] = None,
) -> List[dict]:
    """
    Totales de cartera impaga (APROBADO) a cierre de cada mes.
    Ultimos n_meses hasta el mes de `ref` (hoy por defecto).
    Mes en curso: corte = min(ultimo dia del mes, ref).
    Mismo filtro min/max de cuotas impagas que el detalle (por conteo en ese mes).
    """
    hoy = ref or date.today()
    n = max(1, min(12, int(n_meses)))
    min_n = max(1, min(15, int(cuotas_impagas_min)))
    max_n = max(1, min(15, int(cuotas_impagas_max)))
    if min_n > max_n:
        min_n, max_n = max_n, min_n
    y, m = hoy.year, hoy.month
    periodos: List[tuple] = []
    for _ in range(n):
        periodos.append((y, m))
        m -= 1
        if m < 1:
            m = 12
            y -= 1
    periodos.reverse()

    out: List[dict] = []
    prev_monto: Optional[float] = None
    for anio, mes in periodos:
        corte = _ultimo_dia_mes(anio, mes)
        if corte > hoy:
            corte = hoy
        snap = _agg_impagas_en_fecha(db, corte, cedulas_norm=cedulas_norm)
        filtrados = [
            v
            for v in snap.values()
            if min_n <= int(v.get("cuotas") or 0) <= max_n
        ]
        n_prest = len(filtrados)
        n_cuotas = sum(int(v.get("cuotas") or 0) for v in filtrados)
        monto = round(sum(float(v.get("monto") or 0) for v in filtrados), 2)
        var_pct = None if prev_monto is None else _pct_variacion(monto, prev_monto)
        out.append(
            {
                "anio": anio,
                "mes": mes,
                "periodo": f"{anio}-{mes:02d}",
                "fecha_corte": corte.isoformat(),
                "prestamos": n_prest,
                "cuotas": n_cuotas,
                "monto": monto,
                "var_pct_vs_mes_anterior": var_pct,
                "cuotas_impagas_min": min_n,
                "cuotas_impagas_max": max_n,
            }
        )
        prev_monto = monto
    return out



def _datos_cuentas_por_cobrar(
    db: Session,
    fecha_desde: date,
    fecha_hasta: date,
    cuotas_impagas_min: int,
    cuotas_impagas_max: int,
    cedulas_norm: Optional[Set[str]] = None,
    titulo_informe: str = "Cuentas por cobrar",
    incluir_serie_mensual: bool = True,
    corte_historico: bool = False,
) -> dict:
    """
    Compara dos cortes en orden cronologico (fecha menor -> fecha mayor).

    En cada fecha: cuotas impagas con vencimiento <= esa fecha (saldo a la fecha).
    Filtro 1-15: se aplica al conteo de la fecha mayor (hasta).
    """
    min_n = max(1, min(15, int(cuotas_impagas_min)))
    max_n = max(1, min(15, int(cuotas_impagas_max)))
    if min_n > max_n:
        min_n, max_n = max_n, min_n

    agg_fn = (
        _agg_impagas_en_fecha_historico if corte_historico else _agg_impagas_en_fecha
    )
    snap1 = agg_fn(db, fecha_desde, cedulas_norm=cedulas_norm)
    snap2 = agg_fn(db, fecha_hasta, cedulas_norm=cedulas_norm)
    ids = set(snap1.keys()) | set(snap2.keys())

    items: List[dict] = []
    tot_c1 = tot_c2 = 0
    tot_m1 = tot_m2 = 0.0
    for pid in ids:
        a = snap1.get(pid)
        b = snap2.get(pid)
        base = a or b or {}
        c1 = int(a["cuotas"]) if a else 0
        m1 = float(a["monto"]) if a else 0.0
        c2 = int(b["cuotas"]) if b else 0
        m2 = float(b["monto"]) if b else 0.0
        # Filtro 1-15 aplica al saldo a la Fecha 2 (corte), no al dia exacto.
        if not (min_n <= c2 <= max_n):
            continue
        tot_c1 += c1
        tot_c2 += c2
        tot_m1 += m1
        tot_m2 += m2
        items.append(
            {
                "prestamo_id": pid,
                "cedula": base.get("cedula", ""),
                "nombres": base.get("nombres", ""),
                "cuotas_f1": c1,
                "monto_f1": round(m1, 2),
                "cuotas_f2": c2,
                "monto_f2": round(m2, 2),
            }
        )

    items.sort(key=lambda x: (x.get("cedula") or "", x.get("prestamo_id") or 0))
    # Panorama 6 meses (opcional; Aseguradora lo omite).
    serie_mensual: List[dict] = []
    if incluir_serie_mensual:
        serie_mensual = _serie_mensual_impagas(
            db,
            n_meses=6,
            ref=fecha_hasta,
            cuotas_impagas_min=min_n,
            cuotas_impagas_max=max_n,
            cedulas_norm=cedulas_norm,
        )
    return {
        "titulo_informe": titulo_informe,
        "fecha_desde": fecha_desde.isoformat(),
        "fecha_hasta": fecha_hasta.isoformat(),
        "fecha_1": fecha_desde.isoformat(),
        "fecha_2": fecha_hasta.isoformat(),
        "cuotas_impagas_min": min_n,
        "cuotas_impagas_max": max_n,
        "cantidad_prestamos": len(items),
        "total_cuotas_f1": tot_c1,
        "total_monto_f1": round(tot_m1, 2),
        "total_cuotas_f2": tot_c2,
        "total_monto_f2": round(tot_m2, 2),
        "serie_mensual": serie_mensual,
        "universo_cedulas": len(cedulas_norm) if cedulas_norm is not None else None,
        "corte_historico": bool(corte_historico),
        "items": items,
    }


def _generar_excel_cuentas_por_cobrar(data: dict) -> bytes:
    """Excel en filas (corrido hacia abajo)."""
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    titulo = (data.get("titulo_informe") or "Cuentas por cobrar").strip()
    ws.title = titulo[:31]
    f1 = data.get("fecha_1") or data.get("fecha_desde", "")
    f2 = data.get("fecha_2") or data.get("fecha_hasta", "")

    title_font = Font(name="Calibri", size=14, bold=True, color="1F4E79")
    meta_font = Font(name="Calibri", size=10, color="44546A")
    header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    header_fill_l = PatternFill("solid", fgColor="1F4E79")
    header_fill_r = PatternFill("solid", fgColor="2E75B6")
    thin = Border(
        left=Side(style="thin", color="D0D0D0"),
        right=Side(style="thin", color="D0D0D0"),
        top=Side(style="thin", color="D0D0D0"),
        bottom=Side(style="thin", color="D0D0D0"),
    )

    ws.append([titulo])
    ws["A1"].font = title_font
    univ = data.get("universo_cedulas")
    univ_part = f"   |   Universo hoja: {univ} cedulas" if univ is not None else ""
    hist_part = "   |   Corte historico (pagos por fecha_pago)" if data.get("corte_historico") else ""
    ws.append(
        [
            f"Desde (corte): {f1}   |   Hasta (corte): {f2}   |   "
            f"Filtro cuotas impagas: {data.get('cuotas_impagas_min')}-{data.get('cuotas_impagas_max')}"
            f"{univ_part}{hist_part}"
        ]
    )
    ws["A2"].font = meta_font
    ws.append(
        [
            f"Prestamos: {data.get('cantidad_prestamos', 0)}   |   "
            f"F1: {data.get('total_cuotas_f1', 0)} cuotas / ${data.get('total_monto_f1', 0):,.2f}   |   "
            f"F2: {data.get('total_cuotas_f2', 0)} cuotas / ${data.get('total_monto_f2', 0):,.2f}"
        ]
    )
    ws["A3"].font = meta_font
    ws.append([])
    headers = [
        "Cedula",
        "Cliente",
        f"Cuotas desde ({f1})",
        f"Monto desde ({f1})",
        f"Cuotas hasta ({f2})",
        f"Monto hasta ({f2})",
    ]
    ws.append(headers)
    for col, cell in enumerate(ws[5], start=1):
        cell.font = header_font
        cell.fill = header_fill_l if col <= 4 else header_fill_r
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
        cell.border = thin

    for item in data.get("items", []):
        row_num = ws.max_row + 1
        ws.append(
            [
                item.get("cedula", ""),
                item.get("nombres", ""),
                item.get("cuotas_f1", 0),
                item.get("monto_f1", 0),
                item.get("cuotas_f2", 0),
                item.get("monto_f2", 0),
            ]
        )
        for col in range(1, 7):
            ws.cell(row=row_num, column=col).border = thin
        ws.cell(row=row_num, column=4).number_format = '"$"#,##0.00'
        ws.cell(row=row_num, column=6).number_format = '"$"#,##0.00'
        ws.cell(row=row_num, column=3).alignment = Alignment(horizontal="center")
        ws.cell(row=row_num, column=5).alignment = Alignment(horizontal="center")

    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 32
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 16
    ws.column_dimensions["E"].width = 16
    ws.column_dimensions["F"].width = 16
    ws.freeze_panes = "A6"

    # Hoja: evolucion mensual (omitida si no hay serie, p. ej. Aseguradora)
    if data.get("serie_mensual"):
        ws2 = wb.create_sheet("Evolucion 6 meses")
        ws2.append(["Evolucion mensual - cuentas por cobrar (impagas a corte)"])
        ws2["A1"].font = title_font
        ws2.append(
            [
                "Ultimos 6 meses hasta el mes de la fecha hasta. "
                f"Filtro cuotas impagas: {data.get('cuotas_impagas_min')}-{data.get('cuotas_impagas_max')} "
                "(mismo que el detalle). Var % = cambio vs mes anterior."
            ]
        )
        ws2["A2"].font = meta_font
        ws2.append([])
        h2 = [
            "Periodo",
            "Fecha corte",
            "Prestamos",
            "Cuotas impagas",
            "Pendiente USD",
            "Var % vs mes ant.",
        ]
        ws2.append(h2)
        for col, cell in enumerate(ws2[4], start=1):
            cell.font = header_font
            cell.fill = header_fill_l
            cell.alignment = Alignment(horizontal="center", wrap_text=True)
            cell.border = thin
        for row in data.get("serie_mensual") or []:
            var = row.get("var_pct_vs_mes_anterior")
            if var is None:
                var_txt = "n/d"
            else:
                var_txt = f"{var:+.2f}%"
            rnum = ws2.max_row + 1
            ws2.append(
                [
                    row.get("periodo", ""),
                    row.get("fecha_corte", ""),
                    row.get("prestamos", 0),
                    row.get("cuotas", 0),
                    row.get("monto", 0),
                    var_txt,
                ]
            )
            for col in range(1, 7):
                ws2.cell(row=rnum, column=col).border = thin
            ws2.cell(row=rnum, column=5).number_format = '"$"#,##0.00'
            ws2.cell(row=rnum, column=3).alignment = Alignment(horizontal="center")
            ws2.cell(row=rnum, column=4).alignment = Alignment(horizontal="center")
            ws2.cell(row=rnum, column=6).alignment = Alignment(horizontal="center")
        ws2.column_dimensions["A"].width = 12
        ws2.column_dimensions["B"].width = 14
        ws2.column_dimensions["C"].width = 12
        ws2.column_dimensions["D"].width = 14
        ws2.column_dimensions["E"].width = 16
        ws2.column_dimensions["F"].width = 16

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _generar_pdf_cuentas_por_cobrar(data: dict) -> bytes:
    """PDF landscape profesional: encabezado, resumen de cortes y pagina X de Y."""
    from datetime import datetime
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
        KeepTogether,
    )

    buf = io.BytesIO()
    f1 = data.get("fecha_1") or data.get("fecha_desde", "")
    f2 = data.get("fecha_2") or data.get("fecha_hasta", "")
    items = list(data.get("items") or [])
    n_prestamos = int(data.get("cantidad_prestamos") or len(items))
    tot_c1 = int(data.get("total_cuotas_f1") or 0)
    tot_m1 = float(data.get("total_monto_f1") or 0)
    tot_c2 = int(data.get("total_cuotas_f2") or 0)
    tot_m2 = float(data.get("total_monto_f2") or 0)
    prestamos_f1 = sum(
        1 for it in items if int(it.get("cuotas_f1") or 0) > 0 or float(it.get("monto_f1") or 0) > 0
    )
    prestamos_f2 = sum(
        1 for it in items if int(it.get("cuotas_f2") or 0) > 0 or float(it.get("monto_f2") or 0) > 0
    )
    delta_m = round(tot_m2 - tot_m1, 2)
    filtro_min = data.get("cuotas_impagas_min")
    filtro_max = data.get("cuotas_impagas_max")
    generado = datetime.now().strftime("%Y-%m-%d %H:%M")

    page = landscape(letter)
    page_w, page_h = page
    top_m = 0.85 * inch
    bottom_m = 0.55 * inch
    side_m = 0.45 * inch

    doc = SimpleDocTemplate(
        buf,
        pagesize=page,
        leftMargin=side_m,
        rightMargin=side_m,
        topMargin=top_m,
        bottomMargin=bottom_m,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "cpc_title",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=colors.HexColor("#1F4E79"),
        spaceAfter=2,
        leading=17,
    )
    subtitle_style = ParagraphStyle(
        "cpc_sub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        textColor=colors.HexColor("#44546A"),
        leading=11,
        spaceAfter=6,
    )
    summary_label = ParagraphStyle(
        "cpc_sum_lbl",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        textColor=colors.HexColor("#44546A"),
        leading=9,
        alignment=1,
    )
    summary_value = ParagraphStyle(
        "cpc_sum_val",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=colors.HexColor("#1F4E79"),
        leading=12,
        alignment=1,
    )
    summary_hint = ParagraphStyle(
        "cpc_sum_hint",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        textColor=colors.HexColor("#667085"),
        leading=9,
        alignment=1,
    )
    cell_style = ParagraphStyle(
        "cpc_cell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9,
    )
    empty_style = ParagraphStyle(
        "cpc_empty",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=10,
        textColor=colors.HexColor("#C00000"),
        alignment=1,
        spaceBefore=20,
    )

    class _NumberedCanvas(pdf_canvas.Canvas):
        def __init__(self, *args, **kwargs):
            pdf_canvas.Canvas.__init__(self, *args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            page_count = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self._draw_chrome(page_count)
                pdf_canvas.Canvas.showPage(self)
            pdf_canvas.Canvas.save(self)

        def _draw_chrome(self, page_count: int) -> None:
            self.saveState()
            # Encabezado
            self.setFillColor(colors.HexColor("#1F4E79"))
            self.rect(0, page_h - 0.42 * inch, page_w, 0.42 * inch, fill=1, stroke=0)
            self.setFillColor(colors.white)
            self.setFont("Helvetica-Bold", 11)
            self.drawString(
                side_m,
                page_h - 0.27 * inch,
                (data.get("titulo_informe") or "CUENTAS POR COBRAR").upper()[:40],
            )
            self.setFont("Helvetica", 8)
            self.drawRightString(
                page_w - side_m,
                page_h - 0.27 * inch,
                f"Cortes {f1}  |  {f2}",
            )
            self.setStrokeColor(colors.HexColor("#2E75B6"))
            self.setLineWidth(2)
            self.line(0, page_h - 0.42 * inch, page_w, page_h - 0.42 * inch)

            # Pie
            self.setStrokeColor(colors.HexColor("#D0D5DD"))
            self.setLineWidth(0.6)
            self.line(side_m, 0.38 * inch, page_w - side_m, 0.38 * inch)
            self.setFillColor(colors.HexColor("#667085"))
            self.setFont("Helvetica", 7.5)
            self.drawString(side_m, 0.22 * inch, f"Generado: {generado}")
            self.drawCentredString(
                page_w / 2.0,
                0.22 * inch,
                f"Pagina {self._pageNumber} de {page_count}",
            )
            self.drawRightString(
                page_w - side_m,
                0.22 * inch,
                "Confidencial - uso interno",
            )
            self.restoreState()

    story = []
    story.append(
        Paragraph(
            data.get("titulo_informe") or "Informe comparativo de cartera impaga",
            title_style,
        )
    )
    univ = data.get("universo_cedulas")
    univ_txt = (
        f" &nbsp;&nbsp;|&nbsp;&nbsp; <b>Universo hoja:</b> {univ} cedulas"
        if univ is not None
        else ""
    )
    hist_txt = (
        " &nbsp;&nbsp;|&nbsp;&nbsp; <b>Corte historico</b> (pagos por fecha_pago)"
        if data.get("corte_historico")
        else ""
    )
    story.append(
        Paragraph(
            f"Corte menor (antes): <b>{f1}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Corte mayor (hoy / hasta): <b>{f2}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Filtro cuotas impagas en fecha mayor: <b>{filtro_min}-{filtro_max}</b>"
            f"{univ_txt}{hist_txt}",
            subtitle_style,
        )
    )

    # Resumen profesional (4 tarjetas)
    usable_w = page_w - 2 * side_m
    card_w = usable_w / 4.0
    summary_data = [
        [
            [
                Paragraph("PRESTAMOS EN INFORME", summary_label),
                Paragraph(f"{n_prestamos:,}", summary_value),
                Paragraph("Filtrados por impagas en fecha mayor", summary_hint),
            ],
            [
                Paragraph(f"ANTES · {f1}", summary_label),
                Paragraph(f"${tot_m1:,.2f}", summary_value),
                Paragraph(
                    f"{prestamos_f1:,} prestamos · {tot_c1:,} cuotas pend.",
                    summary_hint,
                ),
            ],
            [
                Paragraph(f"HOY · {f2}", summary_label),
                Paragraph(f"${tot_m2:,.2f}", summary_value),
                Paragraph(
                    f"{prestamos_f2:,} prestamos · {tot_c2:,} cuotas pend.",
                    summary_hint,
                ),
            ],
            [
                Paragraph("VARIACION MONTO", summary_label),
                Paragraph(
                    f"{'+' if delta_m > 0 else ''}{delta_m:,.2f}",
                    summary_value,
                ),
                Paragraph("Pendiente hoy menos pendiente antes", summary_hint),
            ],
        ]
    ]
    # Flatten for Table: each cell is a nested mini-table or flowables list
    summary_row = []
    for cell_flowables in summary_data[0]:
        inner = Table(
            [[flow] for flow in cell_flowables],
            colWidths=[card_w - 8],
        )
        inner.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        summary_row.append(inner)

    sum_tbl = Table([summary_row], colWidths=[card_w] * 4)
    sum_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#EEF2F7")),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#E8F1FB")),
                ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#E8F8F0")),
                ("BACKGROUND", (3, 0), (3, 0), colors.HexColor("#FFF4E5")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#1F4E79")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D5DD")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(KeepTogether([sum_tbl]))
    story.append(Spacer(1, 10))

    # Indicadores mes a mes (ultimos 6 meses)
    serie = list(data.get("serie_mensual") or [])
    if serie:
        mes_title = ParagraphStyle(
            "cpc_mes_title",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=colors.HexColor("#1F4E79"),
            spaceAfter=4,
        )
        story.append(
            Paragraph(
                f"Evolucion mensual (ultimos 6 meses) — filtro impagas {filtro_min}-{filtro_max}",
                mes_title,
            )
        )
        story.append(
            Paragraph(
                "Cada fila: saldo impago con vencimiento &lt;= cierre de mes "
                "(mes actual: hasta hoy). Var % = intermensual vs mes anterior.",
                summary_hint,
            )
        )
        story.append(Spacer(1, 4))
        mes_header = [
            Paragraph("<b>Periodo</b>", cell_style),
            Paragraph("<b>Corte</b>", cell_style),
            Paragraph("<b>Prestamos</b>", cell_style),
            Paragraph("<b>Cuotas</b>", cell_style),
            Paragraph("<b>Pendiente USD</b>", cell_style),
            Paragraph("<b>Var % mes</b>", cell_style),
        ]
        mes_rows = [mes_header]
        for row in serie:
            var = row.get("var_pct_vs_mes_anterior")
            if var is None:
                var_txt = "n/d"
            elif var > 0:
                var_txt = f"<font color='#B42318'><b>+{var:.2f}%</b></font>"
            elif var < 0:
                var_txt = f"<font color='#027A48'><b>{var:.2f}%</b></font>"
            else:
                var_txt = "0.00%"
            mes_rows.append(
                [
                    str(row.get("periodo", "")),
                    str(row.get("fecha_corte", "")),
                    f"{int(row.get('prestamos') or 0):,}",
                    f"{int(row.get('cuotas') or 0):,}",
                    f"${float(row.get('monto') or 0):,.2f}",
                    Paragraph(var_txt, cell_style),
                ]
            )
        mes_w = [
            usable_w * 0.12,
            usable_w * 0.16,
            usable_w * 0.14,
            usable_w * 0.14,
            usable_w * 0.24,
            usable_w * 0.20,
        ]
        mes_tbl = Table(mes_rows, colWidths=mes_w, repeatRows=1)
        mes_tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("ALIGN", (2, 1), (3, -1), "CENTER"),
                    ("ALIGN", (4, 1), (4, -1), "RIGHT"),
                    ("ALIGN", (5, 1), (5, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#BFBFBF")),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#F2F2F2")],
                    ),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    (
                        "BACKGROUND",
                        (0, -1),
                        (-1, -1),
                        colors.HexColor("#EEF2F7"),
                    ),
                ]
            )
        )
        story.append(KeepTogether([mes_tbl]))
        story.append(Spacer(1, 10))

    if not items:
        story.append(
            Paragraph(
                "Sin resultados para las fechas y el filtro de cuotas impagas seleccionados.",
                empty_style,
            )
        )
        doc.build(story, canvasmaker=_NumberedCanvas)
        return buf.getvalue()

    col_widths = [
        usable_w * 0.13,
        usable_w * 0.27,
        usable_w * 0.12,
        usable_w * 0.14,
        usable_w * 0.12,
        usable_w * 0.14,
    ]
    header = [
        Paragraph("<b>Cedula</b>", cell_style),
        Paragraph("<b>Cliente</b>", cell_style),
        Paragraph(f"<b>Cuotas<br/>antes {f1}</b>", cell_style),
        Paragraph(f"<b>Pendiente<br/>antes {f1}</b>", cell_style),
        Paragraph(f"<b>Cuotas<br/>hoy {f2}</b>", cell_style),
        Paragraph(f"<b>Pendiente<br/>hoy {f2}</b>", cell_style),
    ]
    rows = [header]
    for it in items:
        nombre = (it.get("nombres") or "")[:42]
        rows.append(
            [
                Paragraph(str(it.get("cedula", "")), cell_style),
                Paragraph(nombre, cell_style),
                str(it.get("cuotas_f1", 0)),
                f"${it.get('monto_f1', 0):,.2f}",
                str(it.get("cuotas_f2", 0)),
                f"${it.get('monto_f2', 0):,.2f}",
            ]
        )

    # Fila de totales al final de la tabla
    rows.append(
        [
            Paragraph("<b>TOTAL</b>", cell_style),
            Paragraph(f"<b>{n_prestamos:,} prestamos</b>", cell_style),
            Paragraph(f"<b>{tot_c1:,}</b>", cell_style),
            Paragraph(f"<b>${tot_m1:,.2f}</b>", cell_style),
            Paragraph(f"<b>{tot_c2:,}</b>", cell_style),
            Paragraph(f"<b>${tot_m2:,.2f}</b>", cell_style),
        ]
    )

    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    last = len(rows) - 1
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (3, 0), colors.HexColor("#1F4E79")),
                ("BACKGROUND", (4, 0), (5, 0), colors.HexColor("#2E75B6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("ALIGN", (2, 1), (2, -1), "CENTER"),
                ("ALIGN", (4, 1), (4, -1), "CENTER"),
                ("ALIGN", (3, 1), (3, -1), "RIGHT"),
                ("ALIGN", (5, 1), (5, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#BFBFBF")),
                ("ROWBACKGROUNDS", (0, 1), (-1, last - 1), [colors.white, colors.HexColor("#F2F2F2")]),
                ("BACKGROUND", (0, last), (-1, last), colors.HexColor("#EEF2F7")),
                ("LINEABOVE", (0, last), (-1, last), 1.0, colors.HexColor("#1F4E79")),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LINEBEFORE", (4, 0), (4, -1), 1.2, colors.HexColor("#1F4E79")),
            ]
        )
    )
    story.append(tbl)
    doc.build(story, canvasmaker=_NumberedCanvas)
    return buf.getvalue()



@router.get("/exportar/cartera")
def exportar_cartera(
    db: Session = Depends(get_db),
    formato: str = Query("excel", pattern="^(excel|pdf)$"),
    fecha_corte: Optional[str] = Query(None),
    fecha_desde: Optional[str] = Query(None, description="YYYY-MM-DD vencimiento desde"),
    fecha_hasta: Optional[str] = Query(None, description="YYYY-MM-DD vencimiento hasta"),
    cuotas_impagas_min: int = Query(1, ge=1, le=15, description="Minimo de cuotas impagas en el rango"),
    cuotas_impagas_max: int = Query(15, ge=1, le=15, description="Maximo de cuotas impagas en el rango"),
    meses: int = Query(12, ge=1, le=24, description="Legacy Excel por mes"),
    anos: Optional[str] = Query(None, description="Legacy anos"),
    meses_list: Optional[str] = Query(None, description="Legacy meses 1-12"),
):
    """
    Exporta Cuentas por cobrar.
    Con fecha_desde/fecha_hasta: detalle por prestamo filtrado por vencimiento e impagas (1-15).
    Sin esas fechas (legacy): Excel por mes / PDF resumen clasico.
    """
    if fecha_desde and fecha_hasta:
        fd = _parse_fecha(fecha_desde)
        fh = _parse_fecha(fecha_hasta)
        # Siempre menor -> mayor: columna izquierda = corte menor, derecha = mayor.
        if fd > fh:
            fd, fh = fh, fd
        data = _datos_cuentas_por_cobrar(db, fd, fh, cuotas_impagas_min, cuotas_impagas_max)
        stamp = f"{fd.isoformat()}_{fh.isoformat()}"
        if formato == "excel":
            content = _generar_excel_cuentas_por_cobrar(data)
            return Response(
                content=content,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename=cuentas_por_cobrar_{stamp}.xlsx"
                },
            )
        content = _generar_pdf_cuentas_por_cobrar(data)
        return Response(
            content=content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=cuentas_por_cobrar_{stamp}.pdf"
            },
        )

    fc = _parse_fecha(fecha_corte)
    if formato == "excel":
        data_por_mes = _cartera_por_periodos(db, _periodos_desde_filtros(anos, meses_list, meses))
        content = _generar_excel_cartera_por_mes(data_por_mes)
        hoy_str = date.today().isoformat()
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=reporte_cartera_{hoy_str}.xlsx"},
        )
    data = _datos_cartera(db, fc)
    content = _generar_pdf_cartera(data)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=reporte_cartera_{fc.isoformat()}.pdf"},
    )


@router.post("/aseguradora/sync")
def sync_aseguradora_universo(db: Session = Depends(get_db)):
    """Sincroniza cedulas desde el Google Sheet Aseguradora (solo columna Cedula)."""
    from fastapi import HTTPException
    from app.services.aseguradora_sheet_sync import sync_aseguradora_cedulas_desde_sheet

    try:
        return sync_aseguradora_cedulas_desde_sheet(db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/aseguradora/meta")
def meta_aseguradora_universo(db: Session = Depends(get_db)):
    from app.services.aseguradora_sheet_sync import meta_universo_aseguradora

    return meta_universo_aseguradora(db)


@router.get("/exportar/aseguradora")
def exportar_aseguradora(
    db: Session = Depends(get_db),
    formato: str = Query("excel", pattern="^(excel|pdf)$"),
    fecha_desde: Optional[str] = Query(None, description="YYYY-MM-DD corte menor"),
    fecha_hasta: Optional[str] = Query(None, description="YYYY-MM-DD corte mayor"),
    cuotas_impagas_min: int = Query(1, ge=1, le=15),
    cuotas_impagas_max: int = Query(15, ge=1, le=15),
    sync: bool = Query(True, description="Releer cedulas del Google Sheet antes de exportar"),
):
    """
    Misma logica que Cuentas por cobrar, limitada a cedulas del Sheet Aseguradora.
    """
    from fastapi import HTTPException
    from app.services.aseguradora_sheet_sync import (
        claves_universo_aseguradora,
        sync_aseguradora_cedulas_desde_sheet,
    )

    if not fecha_desde or not fecha_hasta:
        raise HTTPException(status_code=400, detail="Indique fecha_desde y fecha_hasta.")
    if sync:
        try:
            sync_aseguradora_cedulas_desde_sheet(db)
        except Exception as e:
            # Si ya hay universo cacheado, continuar; si no, fallar.
            claves = claves_universo_aseguradora(db)
            if not claves:
                raise HTTPException(
                    status_code=400,
                    detail=f"No se pudo sincronizar la hoja Aseguradora y no hay cedulas en cache: {e}",
                ) from e
    claves = claves_universo_aseguradora(db)
    if not claves:
        raise HTTPException(
            status_code=400,
            detail="Universo Aseguradora vacio. Sincronice la hoja (POST /reportes/aseguradora/sync).",
        )
    fd = _parse_fecha(fecha_desde)
    fh = _parse_fecha(fecha_hasta)
    if fd > fh:
        fd, fh = fh, fd
    data = _datos_cuentas_por_cobrar(
        db,
        fd,
        fh,
        cuotas_impagas_min,
        cuotas_impagas_max,
        cedulas_norm=claves,
        titulo_informe="Aseguradora",
        incluir_serie_mensual=False,
        corte_historico=True,
    )
    stamp = f"{fd.isoformat()}_{fh.isoformat()}"
    if formato == "excel":
        content = _generar_excel_cuentas_por_cobrar(data)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=aseguradora_{stamp}.xlsx"
            },
        )
    content = _generar_pdf_cuentas_por_cobrar(data)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=aseguradora_{stamp}.pdf"},
    )

