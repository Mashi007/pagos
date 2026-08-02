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
    Por prestamo: cuotas impagas con fecha_vencimiento == fecha (dia puntual).
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
            Cuota.fecha_vencimiento == fecha,
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
    Compara dos fechas puntuales (no un rango continuo).

    Fecha 1 = fecha_desde, Fecha 2 = fecha_hasta:
    en cada una se cuentan solo cuotas impagas con vencimiento ese dia.

    Filtro 1-15: incluye el prestamo si la cantidad en fecha 1 o en fecha 2
    cae en [min, max].
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
    for pid in sorted(ids, key=lambda i: (snap1.get(i) or snap2.get(i) or {}).get("cedula", ""),):
        a = snap1.get(pid)
        b = snap2.get(pid)
        base = a or b or {}
        c1 = int(a["cuotas"]) if a else 0
        m1 = float(a["monto"]) if a else 0.0
        c2 = int(b["cuotas"]) if b else 0
        m2 = float(b["monto"]) if b else 0.0
        in_f1 = min_n <= c1 <= max_n
        in_f2 = min_n <= c2 <= max_n
        if not (in_f1 or in_f2):
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
    from openpyxl.styles import Font

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Cuentas por cobrar"
    f1 = data.get("fecha_1") or data.get("fecha_desde", "")
    f2 = data.get("fecha_2") or data.get("fecha_hasta", "")
    ws.append(["Cuentas por cobrar"])
    ws.append(
        [
            f"Fecha 1: {f1}  |  Fecha 2: {f2}  |  "
            f"Filtro cuotas impagas: {data.get('cuotas_impagas_min')}-{data.get('cuotas_impagas_max')}"
        ]
    )
    ws.append(
        [
            f"Prestamos: {data.get('cantidad_prestamos', 0)}  |  "
            f"F1 cuotas/monto: {data.get('total_cuotas_f1', 0)} / ${data.get('total_monto_f1', 0):,.2f}  |  "
            f"F2 cuotas/monto: {data.get('total_cuotas_f2', 0)} / ${data.get('total_monto_f2', 0):,.2f}"
        ]
    )
    ws.append([])
    ws.append(
        [
            "Cedula",
            "Cliente",
            f"Cuotas {f1}",
            f"Monto {f1} ($)",
            f"Cuotas {f2}",
            f"Monto {f2} ($)",
        ]
    )
    for cell in ws[ws.max_row]:
        cell.font = Font(bold=True)
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
        ws.cell(row=row_num, column=4).number_format = "$#,##0.00"
        ws.cell(row=row_num, column=6).number_format = "$#,##0.00"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _generar_pdf_cuentas_por_cobrar(data: dict) -> bytes:
    """PDF en 2 columnas para ahorrar espacio."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        NextPageTemplate,
        PageTemplate,
        Paragraph,
        Spacer,
        FrameBreak,
        Table,
        TableStyle,
    )

    buf = io.BytesIO()
    f1 = data.get("fecha_1") or data.get("fecha_desde", "")
    f2 = data.get("fecha_2") or data.get("fecha_hasta", "")
    page_w, page_h = letter
    margin = 0.45 * inch
    gap = 0.2 * inch
    col_w = (page_w - 2 * margin - gap) / 2.0
    frame_h = page_h - 1.35 * inch

    doc = BaseDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
    )

    def _header(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(margin, page_h - 0.4 * inch, "Cuentas por cobrar")
        canvas.setFont("Helvetica", 8)
        canvas.drawString(
            margin,
            page_h - 0.58 * inch,
            f"Fecha 1: {f1}   |   Fecha 2: {f2}   |   "
            f"Filtro impagas: {data.get('cuotas_impagas_min')}-{data.get('cuotas_impagas_max')}   |   "
            f"Prestamos: {data.get('cantidad_prestamos', 0)}",
        )
        canvas.drawString(
            margin,
            page_h - 0.72 * inch,
            f"F1: {data.get('total_cuotas_f1', 0)} cuotas / ${data.get('total_monto_f1', 0):,.2f}   |   "
            f"F2: {data.get('total_cuotas_f2', 0)} cuotas / ${data.get('total_monto_f2', 0):,.2f}",
        )
        canvas.restoreState()

    frame_left = Frame(margin, margin, col_w, frame_h, id="col1")
    frame_right = Frame(margin + col_w + gap, margin, col_w, frame_h, id="col2")
    doc.addPageTemplates(
        [
            PageTemplate(id="TwoCol", frames=[frame_left, frame_right], onPage=_header),
        ]
    )

    styles = getSampleStyleSheet()
    cell = ParagraphStyle(
        "celda",
        parent=styles["Normal"],
        fontSize=7,
        leading=9,
    )
    items = list(data.get("items") or [])
    if not items:
        items = [
            {
                "cedula": "-",
                "nombres": "Sin resultados",
                "cuotas_f1": 0,
                "monto_f1": 0,
                "cuotas_f2": 0,
                "monto_f2": 0,
            }
        ]

    mid = (len(items) + 1) // 2
    left_items = items[:mid]
    right_items = items[mid:]

    def _col_table(chunk):
        rows = [["Cedula", f"C {f1[-5:]}", f"$ {f1[-5:]}", f"C {f2[-5:]}", f"$ {f2[-5:]}"]]
        for it in chunk:
            rows.append(
                [
                    Paragraph(str(it.get("cedula", "")), cell),
                    str(it.get("cuotas_f1", 0)),
                    f"{it.get('monto_f1', 0):,.2f}",
                    str(it.get("cuotas_f2", 0)),
                    f"{it.get('monto_f2', 0):,.2f}",
                ]
            )
        tbl = Table(rows, colWidths=[col_w * 0.32, col_w * 0.14, col_w * 0.20, col_w * 0.14, col_w * 0.20])
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f6f6")]),
                ]
            )
        )
        return tbl

    story = [NextPageTemplate("TwoCol"), _col_table(left_items), FrameBreak(), _col_table(right_items)]
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