"""
Reportes de morosidad (pago vencido).
"""
import calendar
import io
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo

from app.api.v1.endpoints.reportes_utils import _safe_float, _parse_fecha, _periodos_desde_filtros

router = APIRouter(dependencies=[Depends(get_current_user)])

RANGOS_ATRASO = [
    {"key": "1_dia", "label": "1 día atrasado", "min_dias": 1, "max_dias": 14},
    {"key": "15_dias", "label": "15 días atrasado", "min_dias": 15, "max_dias": 29},
    {"key": "30_dias", "label": "30 días atrasado", "min_dias": 30, "max_dias": 59},
    {"key": "2_meses", "label": "2 meses atrasado", "min_dias": 60, "max_dias": 89},
    {"key": "90_dias", "label": "90 días o más (moroso)", "min_dias": 90, "max_dias": 99999},
]


@router.get("/morosidad/clientes")
def get_morosidad_clientes(
    db: Session = Depends(get_db),
    fecha_corte: Optional[str] = Query(None),
):
    """Lista de clientes con cuotas en morosidad (90+ días impagas)."""
    fc = _parse_fecha(fecha_corte)
    umbral = fc - timedelta(days=89)
    q = (
        select(
            Cliente.id.label("cliente_id"),
            Cliente.nombres.label("nombre"),
            Cliente.cedula.label("cedula"),
            func.count(Cuota.id).label("cantidad_cuotas"),
            func.coalesce(func.sum(Cuota.monto), 0).label("total_usd"),
        )
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento < umbral,
        )
        .group_by(Cliente.id, Cliente.nombres, Cliente.cedula)
        .order_by(func.coalesce(func.sum(Cuota.monto), 0).desc())
    )
    rows = db.execute(q).fetchall()
    return {
        "fecha_corte": fc.isoformat(),
        "items": [
            {
                "nombre": r.nombre or "",
                "cedula": r.cedula or "",
                "cantidad_cuotas_morosidad": int(r.cantidad_cuotas or 0),
                "total_usd_morosidad": round(_safe_float(r.total_usd), 2),
            }
            for r in rows
        ],
    }


@router.get("/exportar/morosidad-clientes")
def exportar_morosidad_clientes(
    db: Session = Depends(get_db),
    fecha_corte: Optional[str] = Query(None),
):
    """Exporta Excel: Nombre, Cédula, Cantidad cuotas en morosidad, Total USD."""
    import openpyxl
    data = get_morosidad_clientes(db=db, fecha_corte=fecha_corte)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Morosidad"
    ws.append(["Nombre", "Cédula", "Cantidad de cuotas en morosidad", "Total en dólares en morosidad"])
    for r in data["items"]:
        ws.append([
            r.get("nombre", ""),
            r.get("cedula", ""),
            r.get("cantidad_cuotas_morosidad", 0),
            r.get("total_usd_morosidad", 0),
        ])
    buf = io.BytesIO()
    wb.save(buf)
    content = buf.getvalue()
    hoy_str = data["fecha_corte"]
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=reporte_morosidad_{hoy_str}.xlsx"},
    )


@router.get("/morosidad")
def get_reporte_morosidad(
    db: Session = Depends(get_db),
    fecha_corte: Optional[str] = Query(None),
):
    """Reporte de pago vencido. Moroso = 90+ días de atraso."""
    fc = _parse_fecha(fecha_corte)
    subq_mora = (
        select(Cuota.prestamo_id)
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento < fc,
        )
        .distinct()
    )
    total_prestamos_mora = db.scalar(select(func.count()).select_from(subq_mora.subquery())) or 0
    prestamos_ids = [r[0] for r in db.execute(subq_mora).fetchall()]
    total_clientes_mora = 0
    if prestamos_ids:
        total_clientes_mora = db.scalar(
            select(func.count(func.distinct(Prestamo.cliente_id))).select_from(Prestamo).where(Prestamo.id.in_(prestamos_ids))
        ) or 0
    monto_total_mora = _safe_float(
        db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                Cliente.estado == "ACTIVO",
                Prestamo.estado == "APROBADO",
                Cuota.fecha_pago.is_(None),
                Cuota.fecha_vencimiento < fc,
            )
        )
        or 0
    )
    cuotas_mora = db.execute(
        select(Cuota.prestamo_id, Cuota.fecha_vencimiento)
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento < fc,
        )
    ).fetchall()
    dias_list = [(fc - r.fecha_vencimiento).days for r in cuotas_mora]
    promedio_dias_mora = sum(dias_list) / len(dias_list) if dias_list else 0
    distribucion_por_rango: List[dict] = []
    morosidad_por_analista: List[dict] = []
    analistas = db.execute(select(Prestamo.analista).where(Prestamo.id.in_(prestamos_ids)).distinct()).fetchall()
    for (analista,) in analistas:
        if not analista:
            continue
        ids_ana = db.execute(select(Prestamo.id).where(Prestamo.analista == analista, Prestamo.id.in_(prestamos_ids))).fetchall()
        ids_ana = [x[0] for x in ids_ana]
        monto_ana = _safe_float(db.scalar(select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento < fc, Cuota.prestamo_id.in_(ids_ana)))) or 0
        cuotas_ana = db.execute(
            select(Cuota.fecha_vencimiento).select_from(Cuota).where(
                Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento < fc, Cuota.prestamo_id.in_(ids_ana)
            )
        ).fetchall()
        dias_ana = [(fc - r.fecha_vencimiento).days for r in cuotas_ana]
        prom_dias_ana = sum(dias_ana) / len(dias_ana) if dias_ana else 0
        morosidad_por_analista.append({
            "analista": analista,
            "cantidad_prestamos": len(ids_ana),
            "cantidad_clientes": db.scalar(select(func.count(func.distinct(Prestamo.cliente_id))).select_from(Prestamo).where(Prestamo.id.in_(ids_ana))) or 0,
            "monto_total_mora": monto_ana,
            "promedio_dias_mora": prom_dias_ana,
        })
    detalle: List[dict] = []
    for pid in prestamos_ids[:200]:
        p = db.get(Prestamo, pid)
        if not p:
            continue
        monto_mora = _safe_float(db.scalar(select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(Cuota.prestamo_id == pid, Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento < fc)) or 0)
        cuotas_en_mora = db.scalar(select(func.count()).select_from(Cuota).where(Cuota.prestamo_id == pid, Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento < fc)) or 0
        primera = db.execute(select(func.min(Cuota.fecha_vencimiento)).select_from(Cuota).where(Cuota.prestamo_id == pid, Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento < fc)).scalar()
        max_dias = (fc - primera).days if primera else 0
        detalle.append({
            "prestamo_id": pid,
            "cedula": p.cedula or "",
            "nombres": p.nombres or "",
            "total_financiamiento": _safe_float(p.total_financiamiento),
            "analista": p.analista or "",
            "concesionario": p.concesionario or "",
            "cuotas_en_mora": cuotas_en_mora,
            "monto_total_mora": monto_mora,
            "max_dias_mora": max_dias,
            "primera_cuota_vencida": primera.isoformat() if primera else None,
        })
    return {
        "fecha_corte": fc.isoformat(),
        "total_prestamos_mora": total_prestamos_mora,
        "total_clientes_mora": total_clientes_mora,
        "monto_total_mora": monto_total_mora,
        "promedio_dias_mora": round(promedio_dias_mora, 2),
        "distribucion_por_rango": distribucion_por_rango,
        "morosidad_por_analista": morosidad_por_analista,
        "detalle_prestamos": detalle,
    }


@router.get("/morosidad/por-mes")
def get_morosidad_por_mes(
    db: Session = Depends(get_db),
    meses: int = Query(12, ge=1, le=24, description="Cantidad de meses hacia atrás"),
    anos: Optional[str] = Query(None),
    meses_list: Optional[str] = Query(None),
):
    """Morosidad por mes: una pestaña por mes. Cuotas vencidas sin pagar a fin de cada mes, agrupadas por cédula."""
    resultado: dict = {"meses": []}
    periodos = _periodos_desde_filtros(anos, meses_list, meses)

    for (ano, mes) in periodos:
        _, ultimo = calendar.monthrange(ano, mes)
        fc = date(ano, mes, ultimo)

        subq_mora = (
            select(Cuota.prestamo_id)
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                Cliente.estado == "ACTIVO",
                Prestamo.estado == "APROBADO",
                Cuota.fecha_pago.is_(None),
                Cuota.fecha_vencimiento < fc,
            )
            .distinct()
        )
        prestamos_ids = [r[0] for r in db.execute(subq_mora).fetchall()]
        total_prestamos_mora = len(prestamos_ids)
        total_clientes_mora = 0
        monto_total_mora = 0.0
        if prestamos_ids:
            total_clientes_mora = db.scalar(
                select(func.count(func.distinct(Prestamo.cliente_id))).select_from(Prestamo).where(Prestamo.id.in_(prestamos_ids))
            ) or 0
            monto_total_mora = _safe_float(
                db.scalar(
                    select(func.coalesce(func.sum(Cuota.monto), 0))
                    .select_from(Cuota)
                    .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                    .join(Cliente, Prestamo.cliente_id == Cliente.id)
                    .where(
                        Cliente.estado == "ACTIVO",
                        Prestamo.estado == "APROBADO",
                        Cuota.fecha_pago.is_(None),
                        Cuota.fecha_vencimiento < fc,
                    )
                )
            ) or 0

        cuotas_mora = db.execute(
            select(Cuota.prestamo_id, Cuota.fecha_vencimiento)
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                Cliente.estado == "ACTIVO",
                Prestamo.estado == "APROBADO",
                Cuota.fecha_pago.is_(None),
                Cuota.fecha_vencimiento < fc,
            )
        ).fetchall()
        dias_list = [(fc - r.fecha_vencimiento).days for r in cuotas_mora]
        promedio_dias_mora = sum(dias_list) / len(dias_list) if dias_list else 0

        morosidad_por_cedula: List[dict] = []
        if prestamos_ids:
            monto_por_prestamo_rows = db.execute(
                select(Cuota.prestamo_id, func.coalesce(func.sum(Cuota.monto), 0).label("monto"))
                .select_from(Cuota)
                .where(
                    Cuota.prestamo_id.in_(prestamos_ids),
                    Cuota.fecha_pago.is_(None),
                    Cuota.fecha_vencimiento < fc,
                )
                .group_by(Cuota.prestamo_id)
            ).fetchall()
            monto_por_prestamo = {r.prestamo_id: _safe_float(r.monto) for r in monto_por_prestamo_rows}
            prestamos_data = db.execute(
                select(Prestamo.id, Prestamo.cedula, Prestamo.nombres)
                .where(Prestamo.id.in_(prestamos_ids), Prestamo.cedula.isnot(None), Prestamo.cedula != "")
            ).fetchall()
            pid_to_cedula: dict = {}
            cedula_agg: dict = {}
            for pid, cedula, nombres in prestamos_data:
                cedula = cedula or ""
                pid_to_cedula[pid] = cedula
                if cedula not in cedula_agg:
                    cedula_agg[cedula] = {"nombres": nombres or "", "prestamos": set(), "dias": []}
                cedula_agg[cedula]["prestamos"].add(pid)
            for r in cuotas_mora:
                cedula = pid_to_cedula.get(r.prestamo_id)
                if cedula and cedula in cedula_agg:
                    cedula_agg[cedula]["dias"].append((fc - r.fecha_vencimiento).days)
            for cedula, data in cedula_agg.items():
                monto_total = sum(monto_por_prestamo.get(pid, 0) for pid in data["prestamos"])
                prom_dias = sum(data["dias"]) / len(data["dias"]) if data["dias"] else 0
                morosidad_por_cedula.append({
                    "cedula": cedula,
                    "nombres": data["nombres"],
                    "cantidad_prestamos": len(data["prestamos"]),
                    "cantidad_clientes": 1,
                    "monto_total_mora": round(monto_total, 2),
                    "promedio_dias_mora": round(prom_dias, 1),
                })
            morosidad_por_cedula.sort(key=lambda x: -x["monto_total_mora"])

        resultado["meses"].append({
            "mes": mes,
            "ano": ano,
            "label": f"{mes:02d}/{ano}",
            "fecha_corte": fc.isoformat(),
            "total_prestamos_mora": total_prestamos_mora,
            "total_clientes_mora": total_clientes_mora,
            "monto_total_mora": monto_total_mora,
            "promedio_dias_mora": round(promedio_dias_mora, 1),
            "morosidad_por_cedula": morosidad_por_cedula,
        })

    return resultado


@router.get("/morosidad/por-rangos")
def get_morosidad_por_rangos(
    db: Session = Depends(get_db),
    fecha_corte: Optional[str] = Query(None),
):
    """Informe pago vencido por rangos de días."""
    fc = _parse_fecha(fecha_corte)
    subq_mora = (
        select(Cuota.prestamo_id)
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento < fc,
        )
        .distinct()
    )
    prestamos_ids = [r[0] for r in db.execute(subq_mora).fetchall()]

    resultado: dict = {"fecha_corte": fc.isoformat(), "rangos": {}}

    def _fecha_iso(d):
        if d is None:
            return None
        if hasattr(d, "date"):
            d = d.date() if callable(getattr(d, "date", None)) else d
        return d.isoformat()[:10] if hasattr(d, "isoformat") else str(d)[:10]

    for rango in RANGOS_ATRASO:
        min_d, max_d = rango["min_dias"], rango["max_dias"]
        items: List[dict] = []

        for pid in prestamos_ids:
            p = db.get(Prestamo, pid)
            if not p:
                continue

            primera = db.execute(
                select(func.min(Cuota.fecha_vencimiento))
                .select_from(Cuota)
                .where(
                    Cuota.prestamo_id == pid,
                    Cuota.fecha_pago.is_(None),
                    Cuota.fecha_vencimiento < fc,
                )
            ).scalar()
            if not primera:
                continue
            dias_atraso = (fc - primera).days
            if dias_atraso < min_d or dias_atraso > max_d:
                continue

            saldo = _safe_float(
                db.scalar(
                    select(func.coalesce(func.sum(Cuota.monto), 0))
                    .select_from(Cuota)
                    .where(
                        Cuota.prestamo_id == pid,
                        Cuota.fecha_pago.is_(None),
                    )
                )
            ) or 0

            pagos_totales = _safe_float(
                db.scalar(
                    select(func.coalesce(func.sum(Cuota.total_pagado), 0))
                    .select_from(Cuota)
                    .where(Cuota.prestamo_id == pid)
                )
            ) or 0

            ultimo_pago = db.execute(
                select(func.max(Cuota.fecha_pago))
                .select_from(Cuota)
                .where(Cuota.prestamo_id == pid, Cuota.fecha_pago.isnot(None))
            ).scalar()

            proximo_pago = db.execute(
                select(func.min(Cuota.fecha_vencimiento))
                .select_from(Cuota)
                .where(Cuota.prestamo_id == pid, Cuota.fecha_pago.is_(None))
            ).scalar()

            items.append({
                "prestamo_id": pid,
                "cedula": p.cedula or "",
                "nombres": p.nombres or "",
                "total_financiamiento": _safe_float(p.total_financiamiento),
                "pagos_totales": pagos_totales,
                "saldo": saldo,
                "ultimo_pago_fecha": _fecha_iso(ultimo_pago),
                "proximo_pago_fecha": _fecha_iso(proximo_pago),
                "dias_atraso": dias_atraso,
            })

        resultado["rangos"][rango["key"]] = {
            "label": rango["label"],
            "items": items,
        }

    return resultado


def _generar_excel_morosidad_por_mes(data_por_mes: dict) -> bytes:
    """Genera Excel con una pestaña por mes."""
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

        ws.append(["Informe de Vencimiento de Pagos", label])
        ws.append([])
        ws.append(["Total préstamos con pago vencido", mes_data.get("total_prestamos_mora", 0)])
        ws.append(["Total clientes con pago vencido", mes_data.get("total_clientes_mora", 0)])
        ws.append(["Monto total en dólares", mes_data.get("monto_total_mora", 0)])
        ws.append(["Promedio días de atraso", round(_safe_float(mes_data.get("promedio_dias_mora", 0)), 1)])
        ws.append([])
        ws.append(["Pago vencido por cédula"])
        ws.append(["Cédula", "Nombre", "Cant. préstamos", "Cant. clientes", "Monto en dólares", "Prom. días"])
        for r in mes_data.get("morosidad_por_cedula", []):
            prom_dias = round(_safe_float(r.get("promedio_dias_mora", 0)), 1)
            ws.append([
                r.get("cedula", ""),
                r.get("nombres", ""),
                r.get("cantidad_prestamos", 0),
                r.get("cantidad_clientes", 0),
                r.get("monto_total_mora", 0),
                prom_dias
            ])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _generar_pdf_morosidad(data: dict) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("Informe de Vencimiento de Pagos", styles["Title"]))
    story.append(Paragraph(f"Fecha de corte: {data.get('fecha_corte', '')}", styles["Normal"]))
    story.append(Spacer(1, 12))
    resumen = [
        ["Total préstamos con pago vencido", str(data.get("total_prestamos_mora", 0))],
        ["Total clientes con pago vencido", str(data.get("total_clientes_mora", 0))],
        ["Monto total en dólares", str(data.get("monto_total_mora", 0))],
        ["Promedio días de atraso", str(round(_safe_float(data.get("promedio_dias_mora", 0)), 1))],
    ]
    t = Table(resumen)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), "#e0e0e0"), ("GRID", (0, 0), (-1, -1), 0.5, "#ccc")]))
    story.append(t)
    mora_analista = data.get("morosidad_por_analista", [])
    if mora_analista:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Pago vencido por analista", styles["Heading2"]))
        rows = [["Analista", "Préstamos", "Clientes", "Monto en dólares", "Prom. días"]]
        for r in mora_analista:
            prom_dias = round(_safe_float(r.get("promedio_dias_mora", 0)), 1)
            rows.append([r.get("analista", ""), str(r.get("cantidad_prestamos", 0)), str(r.get("cantidad_clientes", 0)), str(r.get("monto_total_mora", 0)), str(prom_dias)])
        t2 = Table(rows)
        t2.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), "#e0e0e0"), ("GRID", (0, 0), (-1, -1), 0.5, "#ccc")]))
        story.append(t2)
    doc.build(story)
    return buf.getvalue()


@router.get("/exportar/morosidad")
def exportar_morosidad(
    db: Session = Depends(get_db),
    formato: str = Query("excel", pattern="^(excel|pdf)$"),
    fecha_corte: Optional[str] = Query(None),
    meses: int = Query(12, ge=1, le=24, description="Para Excel: cantidad de meses"),
    anos: Optional[str] = Query(None),
    meses_list: Optional[str] = Query(None),
):
    """Exporta reporte de morosidad. Excel: una pestaña por mes. PDF: fecha de corte única."""
    if formato == "pdf":
        data = get_reporte_morosidad(db=db, fecha_corte=fecha_corte)
        content = _generar_pdf_morosidad(data)
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=informe_vencimiento_pagos_{data['fecha_corte']}.pdf"},
        )
    data_por_mes = get_morosidad_por_mes(db=db, meses=meses, anos=anos, meses_list=meses_list)
    content = _generar_excel_morosidad_por_mes(data_por_mes)
    hoy_str = date.today().isoformat()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=informe_vencimiento_pagos_{hoy_str}.xlsx"},
    )
