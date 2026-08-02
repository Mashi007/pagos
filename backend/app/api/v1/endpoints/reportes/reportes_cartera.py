"""
Reportes de cartera.
"""
import calendar
import io
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import and_, func, select, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo

from app.api.v1.endpoints.reportes_utils import _safe_float, _parse_fecha, _periodos_desde_filtros

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




def _agg_impagas_en_fecha(db: Session, fecha: date) -> dict:
    """
    Snapshot a la fecha: cuotas impagas con fecha_vencimiento <= fecha.
    Impaga = no cubierta al 100% (tol 0.01); excluye CANCELADA.
    """
    total_pagado_n = func.coalesce(Cuota.total_pagado, 0)
    impaga = and_(
        total_pagado_n < (Cuota.monto - 0.01),
        Cuota.estado.is_distinct_from("CANCELADA"),
    )
    saldo_cuota = func.greatest(Cuota.monto - total_pagado_n, 0)
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
        .where(
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            impaga,
            Cuota.fecha_vencimiento <= fecha,
        )
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


def _datos_cuentas_por_cobrar(
    db: Session,
    fecha_desde: date,
    fecha_hasta: date,
    cuotas_impagas_min: int,
    cuotas_impagas_max: int,
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

    snap1 = _agg_impagas_en_fecha(db, fecha_desde)
    snap2 = _agg_impagas_en_fecha(db, fecha_hasta)
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
    return {
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
        "items": items,
    }


def _generar_excel_cuentas_por_cobrar(data: dict) -> bytes:
    """Excel en filas (corrido hacia abajo)."""
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Cuentas por cobrar"
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

    ws.append(["Cuentas por cobrar"])
    ws["A1"].font = title_font
    ws.append(
        [
            f"Desde (corte): {f1}   |   Hasta (corte): {f2}   |   "
            f"Filtro cuotas impagas: {data.get('cuotas_impagas_min')}-{data.get('cuotas_impagas_max')}"
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
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _generar_pdf_cuentas_por_cobrar(data: dict) -> bytes:
    """PDF landscape: columnas F1 | F2 lado a lado, con paginado completo."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch, mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
        HRFlowable,
    )

    buf = io.BytesIO()
    f1 = data.get("fecha_1") or data.get("fecha_desde", "")
    f2 = data.get("fecha_2") or data.get("fecha_hasta", "")
    page = landscape(letter)
    doc = SimpleDocTemplate(
        buf,
        pagesize=page,
        leftMargin=0.4 * inch,
        rightMargin=0.4 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.4 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "cpc_title",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=colors.HexColor("#1F4E79"),
        spaceAfter=4,
    )
    meta_style = ParagraphStyle(
        "cpc_meta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        textColor=colors.HexColor("#44546A"),
        leading=11,
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

    story = []
    story.append(Paragraph("Cuentas por cobrar", title_style))
    story.append(
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1F4E79"), spaceAfter=6)
    )
    story.append(
        Paragraph(
            f"<b>Desde (corte):</b> {f1} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Hasta (corte):</b> {f2} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Filtro impagas:</b> {data.get('cuotas_impagas_min')}-{data.get('cuotas_impagas_max')} "
            f"&nbsp;&nbsp;|&nbsp;&nbsp; <b>Prestamos:</b> {data.get('cantidad_prestamos', 0)}",
            meta_style,
        )
    )
    story.append(
        Paragraph(
            f"<b>Totales F1:</b> {data.get('total_cuotas_f1', 0)} cuotas / "
            f"${data.get('total_monto_f1', 0):,.2f} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Totales F2:</b> {data.get('total_cuotas_f2', 0)} cuotas / "
            f"${data.get('total_monto_f2', 0):,.2f}",
            meta_style,
        )
    )
    story.append(Spacer(1, 8))

    items = list(data.get("items") or [])
    if not items:
        story.append(
            Paragraph(
                "Sin resultados para las fechas y el filtro de cuotas impagas seleccionados.",
                empty_style,
            )
        )
        doc.build(story)
        return buf.getvalue()

    # Dos bloques de columnas (F1 | F2) en una sola tabla ancha
    usable_w = page[0] - 0.8 * inch
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
        Paragraph(f"<b>Cuotas<br/>{f1}</b>", cell_style),
        Paragraph(f"<b>Monto<br/>{f1}</b>", cell_style),
        Paragraph(f"<b>Cuotas<br/>{f2}</b>", cell_style),
        Paragraph(f"<b>Monto<br/>{f2}</b>", cell_style),
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

    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
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
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                # Separador visual entre bloque F1 y F2
                ("LINEBEFORE", (4, 0), (4, -1), 1.2, colors.HexColor("#1F4E79")),
            ]
        )
    )
    story.append(tbl)
    doc.build(story)
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