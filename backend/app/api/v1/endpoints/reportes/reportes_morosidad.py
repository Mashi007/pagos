"""

Reportes de morosidad (pago vencido).

"""

import calendar

import logging

import io

from datetime import date

from typing import List, Optional



from fastapi import APIRouter, Depends, Query

from fastapi.responses import Response

from sqlalchemy import func, literal_column, select, text

from sqlalchemy.orm import Session, aliased



from app.core.database import get_db

from app.core.deps import get_current_user

from app.models.cliente import Cliente

from app.models.cuota import Cuota

from app.models.prestamo import Prestamo

from app.services.cuota_estado import SQL_PG_ESTADO_CUOTA_CASE_CORRELATED, hoy_negocio



from app.api.v1.endpoints.reportes_utils import _safe_float, _parse_fecha, _periodos_desde_filtros



router = APIRouter(dependencies=[Depends(get_current_user)])

logger = logging.getLogger(__name__)


# Export /exportar/morosidad-cedulas: regla no negociable — solo filas cuyo estado calculado sea este codigo.
# Ningun otro estado (VENCIDO, PENDIENTE, PARCIAL, etc.) entra en el Excel.
REPORTE_MOROSIDAD_SOLO_ESTADO = "MORA"


RANGOS_ATRASO = [

    {"key": "1_dia", "label": "1 dÃ­a atrasado", "min_dias": 1, "max_dias": 14},

    {"key": "15_dias", "label": "15 dÃ­as atrasado", "min_dias": 15, "max_dias": 29},

    {"key": "30_dias", "label": "30 dÃ­as atrasado", "min_dias": 30, "max_dias": 59},

    {"key": "2_meses", "label": "2 meses atrasado", "min_dias": 60, "max_dias": 89},

    {"key": "4_meses", "label": "4+ meses (moroso)", "min_dias": 121, "max_dias": 99999},

]





@router.get("/morosidad/clientes")

def get_morosidad_clientes(

    db: Session = Depends(get_db),

    fecha_corte: Optional[str] = Query(None),

):

    """Lista de clientes con cuotas en morosidad (4 meses calendario + 1 dia, impagas)."""

    fc = _parse_fecha(fecha_corte)

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

            Cuota.fecha_vencimiento + text("INTERVAL '4 months 1 day'") <= fc,

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

    """Exporta Excel: Nombre, CÃ©dula, Cantidad cuotas en morosidad, Total USD."""

    import openpyxl

    data = get_morosidad_clientes(db=db, fecha_corte=fecha_corte)

    wb = openpyxl.Workbook()

    ws = wb.active

    ws.title = "Morosidad"

    ws.append(["Nombre", "CÃ©dula", "Cantidad de cuotas en morosidad", "Total en dÃ³lares en morosidad"])

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

    """Reporte de pago vencido. Moroso = 4 meses calendario + 1 dia de atraso."""

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

            Cuota.fecha_vencimiento + text("INTERVAL '4 months 1 day'") <= fc,

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

                Cuota.fecha_vencimiento + text("INTERVAL '4 months 1 day'") <= fc,

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

            Cuota.fecha_vencimiento + text("INTERVAL '4 months 1 day'") <= fc,

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

        monto_ana = _safe_float(db.scalar(select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento + text("INTERVAL '4 months 1 day'") <= fc, Cuota.prestamo_id.in_(ids_ana)))) or 0

        cuotas_ana = db.execute(

            select(Cuota.fecha_vencimiento).select_from(Cuota).where(

                Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento + text("INTERVAL '4 months 1 day'") <= fc, Cuota.prestamo_id.in_(ids_ana)

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

    meses: int = Query(12, ge=1, le=24, description="Cantidad de meses hacia atrÃ¡s"),

    anos: Optional[str] = Query(None),

    meses_list: Optional[str] = Query(None),

):

    """Morosidad por mes: una pestaÃ±a por mes. Cuotas vencidas sin pagar a fin de cada mes, agrupadas por cÃ©dula."""

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

                Cuota.fecha_vencimiento + text("INTERVAL '4 months 1 day'") <= fc,

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

                        Cuota.fecha_vencimiento + text("INTERVAL '4 months 1 day'") <= fc,

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

                Cuota.fecha_vencimiento + text("INTERVAL '4 months 1 day'") <= fc,

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

                    Cuota.fecha_vencimiento + text("INTERVAL '4 months 1 day'") <= fc,

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

    """Informe pago vencido por rangos de dÃ­as."""

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

            Cuota.fecha_vencimiento + text("INTERVAL '4 months 1 day'") <= fc,

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

                    Cuota.fecha_vencimiento + text("INTERVAL '4 months 1 day'") <= fc,

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

    """Genera Excel con una pestaÃ±a por mes."""

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

        ws.append(["Total prÃ©stamos con pago vencido", mes_data.get("total_prestamos_mora", 0)])

        ws.append(["Total clientes con pago vencido", mes_data.get("total_clientes_mora", 0)])

        ws.append(["Monto total en dÃ³lares", mes_data.get("monto_total_mora", 0)])

        ws.append(["Promedio dÃ­as de atraso", round(_safe_float(mes_data.get("promedio_dias_mora", 0)), 1)])

        ws.append([])

        ws.append(["Pago vencido por cÃ©dula"])

        ws.append(["CÃ©dula", "Nombre", "Cant. prÃ©stamos", "Cant. clientes", "Monto en dÃ³lares", "Prom. dÃ­as"])

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

        ["Total prÃ©stamos con pago vencido", str(data.get("total_prestamos_mora", 0))],

        ["Total clientes con pago vencido", str(data.get("total_clientes_mora", 0))],

        ["Monto total en dÃ³lares", str(data.get("monto_total_mora", 0))],

        ["Promedio dÃ­as de atraso", str(round(_safe_float(data.get("promedio_dias_mora", 0)), 1))],

    ]

    t = Table(resumen)

    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), "#e0e0e0"), ("GRID", (0, 0), (-1, -1), 0.5, "#ccc")]))

    story.append(t)

    mora_analista = data.get("morosidad_por_analista", [])

    if mora_analista:

        story.append(Spacer(1, 12))

        story.append(Paragraph("Pago vencido por analista", styles["Heading2"]))

        rows = [["Analista", "PrÃ©stamos", "Clientes", "Monto en dÃ³lares", "Prom. dÃ­as"]]

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

    """Exporta reporte de morosidad. Excel: una pestaÃ±a por mes. PDF: fecha de corte Ãºnica."""

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


@router.get("/exportar/morosidad-cedulas")
def exportar_morosidad_cedulas(db: Session = Depends(get_db)):
    """Exporta Excel por cedula: solo clientes con cuotas en estado MORA (exclusivo).

    Regla no negociable: ninguna cuota con otro estado entra en agregados ni en montos.
    Criterio: mismo CASE que amortizacion (`SQL_PG_ESTADO_CUOTA_CASE_CORRELATED`) = MORA.
    UI: etiqueta 'Mora (4 meses+)'. Corte: hoy America/Caracas.
    """
    import time

    import openpyxl

    t0 = time.perf_counter()

    # Alias `c` debe coincidir con el SQL embebido (referencias c.id, c.monto_cuota, ...).
    c = aliased(Cuota, name="c")
    _solo = REPORTE_MOROSIDAD_SOLO_ESTADO
    estado_es_mora = text(
        f"(TRIM(BOTH FROM ({SQL_PG_ESTADO_CUOTA_CASE_CORRELATED}))) = '{_solo}'"
    )
    modalidad_por_cliente = literal_column(
        "string_agg(DISTINCT prestamos.modalidad_pago, ', ' "
        "ORDER BY prestamos.modalidad_pago)"
    ).label("modalidad")

    rows_resumen = db.execute(
        select(
            Cliente.id.label("cliente_id"),
            Cliente.cedula.label("cedula"),
            modalidad_por_cliente,
            func.count(c.id).label("total_cuotas"),
            func.coalesce(func.sum(c.monto), 0).label("total_monto"),
        )
        .select_from(c)
        .join(Prestamo, c.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            estado_es_mora,
        )
        .group_by(Cliente.id, Cliente.cedula)
        .order_by(Cliente.cedula.asc())
    ).fetchall()

    fc = hoy_negocio()
    hoy_str = fc.isoformat()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Solo estado MORA"
    ws.append(
        [
            "C\u00e9dula",
            "Modalidad",
            f"Cantidad cuotas (solo {_solo})",
            f"Total USD (solo {_solo})",
        ]
    )

    total_cuotas_general = 0
    total_monto_general = 0.0
    for r in rows_resumen:
        cuotas = int(r.total_cuotas or 0)
        monto = round(_safe_float(r.total_monto), 2)
        total_cuotas_general += cuotas
        total_monto_general += monto
        ws.append(
            [
                r.cedula or "",
                r.modalidad or "",
                cuotas,
                monto,
            ]
        )

    ws.append(
        [
            "TOTAL",
            "",
            total_cuotas_general,
            round(total_monto_general, 2),
        ]
    )

    buf = io.BytesIO()
    wb.save(buf)
    content = buf.getvalue()
    ms = (time.perf_counter() - t0) * 1000
    logger.info(
        "exportar_morosidad_cedulas solo_estado=%s filas_clientes=%s total_cuotas=%s ms=%.1f fecha_corte=%s",
        _solo,
        len(rows_resumen),
        total_cuotas_general,
        ms,
        hoy_str,
    )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=reporte_mora_cedulas_{hoy_str}.xlsx",
            "X-Reporte-Morosidad-Clientes": str(len(rows_resumen)),
            "X-Reporte-Morosidad-Fecha-Corte": hoy_str,
        },
    )

