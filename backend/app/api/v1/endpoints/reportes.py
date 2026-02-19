"""
Endpoints de reportes. Datos reales desde BD.
Dashboard resumen, cartera, pagos, morosidad, financiero, asesores, productos.
Exportación Excel y PDF para cada tipo según corresponda.
"""
import calendar
import io
from datetime import date, datetime, timezone, timedelta
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func, select, and_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.pago import Pago
from app.models.prestamo import Prestamo

router = APIRouter(dependencies=[Depends(get_current_user)])


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _parse_fecha(s: Optional[str]) -> date:
    if not s:
        return date.today()
    try:
        return date.fromisoformat(s)
    except ValueError:
        return date.today()


# ---------- Dashboard resumen ----------
@router.get("/dashboard/resumen")
def get_resumen_dashboard(db: Session = Depends(get_db)):
    """
    Resumen para el dashboard de reportes: total_clientes, total_prestamos, total_pagos,
    cartera_activa, prestamos_mora, pagos_mes, fecha_actualizacion. Datos reales desde BD.
    """
    hoy = date.today()
    now_utc = datetime.now(timezone.utc)
    inicio_mes = hoy.replace(day=1)

    # KPIs solo incluyen clientes ACTIVOS
    total_clientes = db.scalar(
        select(func.count()).select_from(Cliente).where(Cliente.estado == "ACTIVO")
    ) or 0
    total_prestamos = db.scalar(
        select(func.count())
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(Cliente.estado == "ACTIVO", Prestamo.estado == "APROBADO")
    ) or 0
    total_pagos = db.scalar(
        select(func.count())
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.isnot(None),
        )
    ) or 0
    cartera_activa = db.scalar(
        select(func.coalesce(func.sum(Cuota.monto), 0))
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.is_(None),
        )
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
            Cuota.fecha_vencimiento < hoy,
        )
        .distinct()
    )
    prestamos_mora = db.scalar(select(func.count()).select_from(subq_mora.subquery())) or 0
    # Monto total cobrado este mes (cuotas con fecha_pago en el mes actual)
    pagos_mes = _safe_float(
        db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                Cliente.estado == "ACTIVO",
                Prestamo.estado == "APROBADO",
                Cuota.fecha_pago.isnot(None),
                func.date(Cuota.fecha_pago) >= inicio_mes,
                func.date(Cuota.fecha_pago) <= hoy,
            )
        )
        or 0
    )

    return {
        "total_clientes": total_clientes,
        "total_prestamos": total_prestamos,
        "total_pagos": total_pagos,
        "cartera_activa": _safe_float(cartera_activa),
        "prestamos_mora": prestamos_mora,
        "pagos_mes": pagos_mes,
        "fecha_actualizacion": now_utc.isoformat(),
    }


# ---------- Reporte pendientes por cliente (PDF) ----------
def _generar_pdf_pendientes_cliente(cedula: str, nombre: str, cuotas: List[dict], total_pendiente: float) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("Cuotas pendientes por cliente", styles["Title"]))
    story.append(Paragraph(f"Cédula: {cedula}", styles["Normal"]))
    story.append(Paragraph(f"Cliente: {nombre or '—'}", styles["Normal"]))
    story.append(Paragraph(f"Total pendiente: {total_pendiente:.2f}", styles["Normal"]))
    story.append(Spacer(1, 12))
    if not cuotas:
        story.append(Paragraph("No hay cuotas pendientes.", styles["Normal"]))
    else:
        rows = [["Préstamo", "Nº Cuota", "Vencimiento", "Monto", "Estado"]]
        for c in cuotas:
            rows.append([
                str(c.get("prestamo_id", "")),
                str(c.get("numero_cuota", "")),
                c.get("fecha_vencimiento", ""),
                str(c.get("monto", 0)),
                c.get("estado", ""),
            ])
        t = Table(rows)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), "#e0e0e0"), ("GRID", (0, 0), (-1, -1), 0.5, "#ccc")]))
        story.append(t)
    doc.build(story)
    return buf.getvalue()


@router.get("/cliente/{cedula}/pendientes.pdf")
def get_pendientes_cliente_pdf(cedula: str, db: Session = Depends(get_db)):
    """Genera PDF con cuotas pendientes del cliente por cédula."""
    from fastapi import HTTPException
    row = db.execute(select(Cliente).where(Cliente.cedula == cedula.strip())).first()
    if not row:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    cliente = row[0]
    nombre = getattr(cliente, "nombres", None) or ""
    prestamos = db.execute(
        select(Prestamo).where(Prestamo.cliente_id == cliente.id)
    ).scalars().all()
    prestamo_ids = [p.id for p in prestamos]
    cuotas_list = []
    total_pendiente = 0.0
    if prestamo_ids:
        cuotas_rows = db.execute(
            select(Cuota)
            .where(Cuota.prestamo_id.in_(prestamo_ids), Cuota.fecha_pago.is_(None))
            .order_by(Cuota.prestamo_id, Cuota.numero_cuota)
        ).scalars().all()
        for c in cuotas_rows:
            m = float(c.monto) if c.monto is not None else 0
            total_pendiente += m
            cuotas_list.append({
                "prestamo_id": c.prestamo_id,
                "numero_cuota": c.numero_cuota,
                "fecha_vencimiento": c.fecha_vencimiento.isoformat() if c.fecha_vencimiento else "",
                "monto": m,
                "estado": c.estado or "PENDIENTE",
            })
    content = _generar_pdf_pendientes_cliente(cedula, nombre, cuotas_list, total_pendiente)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=pendientes_{cedula}.pdf"},
    )


# ---------- PDF Tabla de amortización completa por cédula ----------
def _generar_pdf_amortizacion_cliente(cedula: str, nombre: str, cuotas: List[dict]) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("Tabla de amortización", styles["Title"]))
    story.append(Paragraph(f"Cédula: {cedula}", styles["Normal"]))
    story.append(Paragraph(f"Cliente: {nombre or '—'}", styles["Normal"]))
    story.append(Spacer(1, 12))
    if not cuotas:
        story.append(Paragraph("No hay cuotas para este cliente.", styles["Normal"]))
    else:
        rows = [["Préstamo", "Nº Cuota", "Vencimiento", "Fecha pago", "Monto", "Estado"]]
        for c in cuotas:
            rows.append([
                str(c.get("prestamo_id", "")),
                str(c.get("numero_cuota", "")),
                c.get("fecha_vencimiento", ""),
                c.get("fecha_pago") or "—",
                str(c.get("monto", 0)),
                c.get("estado", ""),
            ])
        t = Table(rows)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), "#e0e0e0"), ("GRID", (0, 0), (-1, -1), 0.5, "#ccc")]))
        story.append(t)
    doc.build(story)
    return buf.getvalue()


@router.get("/cliente/{cedula}/amortizacion.pdf")
def get_amortizacion_cliente_pdf(cedula: str, db: Session = Depends(get_db)):
    """Genera PDF con tabla de amortización completa (todas las cuotas) del cliente por cédula."""
    from fastapi import HTTPException
    row = db.execute(select(Cliente).where(Cliente.cedula == cedula.strip())).first()
    if not row:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    cliente = row[0]
    nombre = getattr(cliente, "nombres", None) or ""
    prestamos = db.execute(
        select(Prestamo).where(Prestamo.cliente_id == cliente.id)
    ).scalars().all()
    prestamo_ids = [p.id for p in prestamos]
    cuotas_list = []
    if prestamo_ids:
        cuotas_rows = db.execute(
            select(Cuota)
            .where(Cuota.prestamo_id.in_(prestamo_ids))
            .order_by(Cuota.prestamo_id, Cuota.numero_cuota)
        ).scalars().all()
        for c in cuotas_rows:
            m = float(c.monto) if c.monto is not None else 0
            fp = getattr(c, "fecha_pago", None)
            fecha_pago_str = fp.isoformat() if fp else "—"
            cuotas_list.append({
                "prestamo_id": c.prestamo_id,
                "numero_cuota": c.numero_cuota,
                "fecha_vencimiento": c.fecha_vencimiento.isoformat() if c.fecha_vencimiento else "",
                "fecha_pago": fecha_pago_str,
                "monto": m,
                "estado": c.estado or "PENDIENTE",
            })
    content = _generar_pdf_amortizacion_cliente(cedula, nombre, cuotas_list)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=amortizacion_{cedula}.pdf"},
    )


# ---------- Reporte Cartera ----------
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
            Cuota.fecha_vencimiento < fecha_corte,
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
                Cuota.fecha_vencimiento < fecha_corte,
            )
        )
        or 0
    )

    # Distribución por monto (rangos simples)
    rangos = [(0, 5000), (5001, 15000), (15001, 50000), (50001, 999999999)]
    distribucion_por_monto: List[dict] = []
    for low, high in rangos:
        subq = (
            select(Cuota.prestamo_id)
            .where(Cuota.fecha_pago.is_(None))
            .group_by(Cuota.prestamo_id)
            .having(and_(func.sum(Cuota.monto) >= low, func.sum(Cuota.monto) <= high))
        )
        # Contar préstamos con saldo en ese rango (aproximado por suma de cuotas)
        q = (
            select(func.count(func.distinct(Cuota.prestamo_id)), func.coalesce(func.sum(Cuota.monto), 0))
            .select_from(Cuota)
            .where(Cuota.fecha_pago.is_(None))
        )
        # Simplificado: un solo rango "Total" para no complicar la query
        pass
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

    # Distribución por mora (días)
    distribucion_por_mora: List[dict] = []
    for label, dias_min, dias_max in [
        ("0-30 días", 0, 30),
        ("31-60 días", 31, 60),
        ("61-90 días", 61, 90),
        ("> 90 días", 91, 9999),
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


@router.get("/cartera/por-mes")
def get_cartera_por_mes(
    db: Session = Depends(get_db),
    meses: int = Query(12, ge=1, le=24, description="Cantidad de meses hacia atrás"),
):
    """Cuentas por cobrar: una pestaña por mes. Por día: cuándo debe cobrar (fecha vencimiento, monto pendiente)."""
    hoy = date.today()
    resultado: dict = {"meses": []}

    for i in range(meses):
        año = hoy.year
        mes = hoy.month - i
        while mes <= 0:
            mes += 12
            año -= 1
        inicio = date(año, mes, 1)
        _, ultimo = calendar.monthrange(año, mes)
        fin = date(año, mes, ultimo)

        rows = db.execute(
            select(
                Cuota.fecha_vencimiento,
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
            .group_by(Cuota.fecha_vencimiento)
            .order_by(Cuota.fecha_vencimiento)
        ).fetchall()

        items = [
            {
                "fecha": r.fecha_vencimiento.isoformat() if r.fecha_vencimiento else None,
                "monto_cobrar": round(_safe_float(r.monto_cobrar), 2),
                "cantidad_cuotas": r.cantidad_cuotas or 0,
            }
            for r in rows
        ]

        resultado["meses"].append({
            "mes": mes,
            "año": año,
            "label": f"{mes:02d}/{año}",
            "items": items,
        })

    return resultado


@router.get("/cartera")
def get_reporte_cartera(
    db: Session = Depends(get_db),
    fecha_corte: Optional[str] = Query(None, description="Fecha de corte YYYY-MM-DD"),
):
    """Reporte de cartera en JSON. Datos reales desde BD."""
    fc = _parse_fecha(fecha_corte)
    return _datos_cartera(db, fc)


def _generar_excel_cartera(data: dict) -> bytes:
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


@router.get("/exportar/cartera")
def exportar_cartera(
    db: Session = Depends(get_db),
    formato: str = Query("excel", pattern="^(excel|pdf)$"),
    fecha_corte: Optional[str] = Query(None),
):
    """Exporta reporte de cartera en Excel o PDF. Datos reales desde BD."""
    fc = _parse_fecha(fecha_corte)
    data = _datos_cartera(db, fc)
    if formato == "excel":
        content = _generar_excel_cartera(data)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=reporte_cartera_{fc.isoformat()}.xlsx"},
        )
    content = _generar_pdf_cartera(data)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=reporte_cartera_{fc.isoformat()}.pdf"},
    )


# ---------- Reporte Pagos ----------
@router.get("/pagos")
def get_reporte_pagos(
    db: Session = Depends(get_db),
    fecha_inicio: str = Query(..., description="YYYY-MM-DD"),
    fecha_fin: str = Query(..., description="YYYY-MM-DD"),
):
    """Reporte de pagos en un rango de fechas. Datos reales desde BD."""
    fi = _parse_fecha(fecha_inicio)
    ff = _parse_fecha(fecha_fin)
    if fi > ff:
        fi, ff = ff, fi
    # Solo clientes ACTIVOS
    total_pagos = _safe_float(
        db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                Cliente.estado == "ACTIVO",
                Prestamo.estado == "APROBADO",
                Cuota.fecha_pago.isnot(None),
                func.date(Cuota.fecha_pago) >= fi,
                func.date(Cuota.fecha_pago) <= ff,
            )
        )
        or 0
    )
    cantidad_pagos = db.scalar(
        select(func.count())
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.isnot(None),
            func.date(Cuota.fecha_pago) >= fi,
            func.date(Cuota.fecha_pago) <= ff,
        )
    ) or 0
    pagos_por_dia = (
        db.execute(
            select(func.date(Cuota.fecha_pago).label("fecha"), func.count().label("cantidad"), func.sum(Cuota.monto).label("monto"))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                Cliente.estado == "ACTIVO",
                Prestamo.estado == "APROBADO",
                Cuota.fecha_pago.isnot(None),
                func.date(Cuota.fecha_pago) >= fi,
                func.date(Cuota.fecha_pago) <= ff,
            )
            .group_by(func.date(Cuota.fecha_pago))
            .order_by(func.date(Cuota.fecha_pago))
        )
    ).fetchall()
    return {
        "fecha_inicio": fi.isoformat(),
        "fecha_fin": ff.isoformat(),
        "total_pagos": total_pagos,
        "cantidad_pagos": cantidad_pagos,
        "pagos_por_metodo": [],
        "pagos_por_dia": [
            {"fecha": str(r.fecha), "cantidad": r.cantidad, "monto": _safe_float(r.monto)}
            for r in pagos_por_dia
        ],
    }


@router.get("/pagos/por-mes")
def get_pagos_por_mes(
    db: Session = Depends(get_db),
    meses: int = Query(12, ge=1, le=24, description="Cantidad de meses hacia atrás"),
):
    """Pagos agrupados por mes/año. Cada mes tiene lista de pagos: Fecha, id préstamo, cédula, nombre, monto, documento. Orden descendente por fecha."""
    hoy = date.today()
    resultado: dict = {"meses": []}

    for i in range(meses):
        año = hoy.year
        mes = hoy.month - i
        while mes <= 0:
            mes += 12
            año -= 1
        inicio = date(año, mes, 1)
        _, ultimo = calendar.monthrange(año, mes)
        fin = date(año, mes, ultimo)

        q = (
            select(
                Pago.id,
                Pago.fecha_pago,
                Pago.prestamo_id,
                Pago.cedula_cliente,
                Pago.monto_pagado,
                Pago.numero_documento,
                func.coalesce(Prestamo.nombres, Cliente.nombres).label("nombres"),
            )
            .select_from(Pago)
            .outerjoin(Prestamo, Pago.prestamo_id == Prestamo.id)
            .outerjoin(Cliente, Pago.cedula_cliente == Cliente.cedula)
            .where(
                func.date(Pago.fecha_pago) >= inicio,
                func.date(Pago.fecha_pago) <= fin,
            )
            .order_by(Pago.fecha_pago.desc())
        )
        rows = db.execute(q).fetchall()

        items = []
        for r in rows:
            fp = r.fecha_pago
            fecha_str = fp.date().isoformat() if hasattr(fp, "date") else (fp.isoformat()[:10] if fp else None)
            items.append({
                "pago_id": r.id,
                "fecha": fecha_str,
                "prestamo_id": r.prestamo_id,
                "cedula": r.cedula_cliente or "",
                "nombre": (r.nombres or "").strip(),
                "monto_pago": _safe_float(r.monto_pagado),
                "documento": r.numero_documento or "",
            })

        resultado["meses"].append({
            "mes": mes,
            "año": año,
            "label": f"{mes:02d}/{año}",
            "items": items,
        })

    return resultado


def _generar_excel_pagos(data: dict) -> bytes:
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Pagos"
    ws.append(["Reporte de Pagos", data.get("fecha_inicio", ""), "a", data.get("fecha_fin", "")])
    ws.append([])
    ws.append(["Total pagos", data.get("total_pagos", 0)])
    ws.append(["Cantidad de pagos", data.get("cantidad_pagos", 0)])
    ws.append([])
    ws.append(["Fecha", "Cantidad", "Monto"])
    for r in data.get("pagos_por_dia", []):
        ws.append([r.get("fecha", ""), r.get("cantidad", 0), r.get("monto", 0)])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _generar_pdf_pagos(data: dict) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("Reporte de Pagos", styles["Title"]))
    story.append(Paragraph(f"Período: {data.get('fecha_inicio', '')} a {data.get('fecha_fin', '')}", styles["Normal"]))
    story.append(Spacer(1, 12))
    resumen = [
        ["Total pagos (monto)", str(data.get("total_pagos", 0))],
        ["Cantidad de pagos", str(data.get("cantidad_pagos", 0))],
    ]
    t = Table(resumen)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), "#e0e0e0"), ("GRID", (0, 0), (-1, -1), 0.5, "#ccc")]))
    story.append(t)
    pagos_por_dia = data.get("pagos_por_dia", [])
    if pagos_por_dia:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Pagos por día", styles["Heading2"]))
        rows = [["Fecha", "Cantidad", "Monto"]]
        for r in pagos_por_dia:
            rows.append([r.get("fecha", ""), str(r.get("cantidad", 0)), str(r.get("monto", 0))])
        t2 = Table(rows)
        t2.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), "#e0e0e0"), ("GRID", (0, 0), (-1, -1), 0.5, "#ccc")]))
        story.append(t2)
    doc.build(story)
    return buf.getvalue()


@router.get("/exportar/pagos")
def exportar_pagos(
    db: Session = Depends(get_db),
    formato: str = Query("excel", pattern="^(excel|pdf)$"),
    fecha_inicio: str = Query(...),
    fecha_fin: str = Query(...),
):
    """Exporta reporte de pagos en Excel o PDF."""
    fi = _parse_fecha(fecha_inicio)
    ff = _parse_fecha(fecha_fin)
    if fi > ff:
        fi, ff = ff, fi
    data = get_reporte_pagos(db=db, fecha_inicio=fi.isoformat(), fecha_fin=ff.isoformat())
    if formato == "pdf":
        content = _generar_pdf_pagos(data)
        return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=reporte_pagos_{fi.isoformat()}_{ff.isoformat()}.pdf"})
    content = _generar_excel_pagos(data)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=reporte_pagos_{fi.isoformat()}_{ff.isoformat()}.xlsx"},
    )


# ---------- Reporte Morosidad ----------
@router.get("/morosidad")
def get_reporte_morosidad(
    db: Session = Depends(get_db),
    fecha_corte: Optional[str] = Query(None),
):
    """Reporte de pago vencido. Datos reales desde BD (solo clientes ACTIVOS).
    Concepto: Pago vencido = fecha_vencimiento < fc y fecha_pago IS NULL. Moroso = 61+ días de atraso."""
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
        morosidad_por_analista.append({
            "analista": analista,
            "cantidad_prestamos": len(ids_ana),
            "cantidad_clientes": db.scalar(select(func.count(func.distinct(Prestamo.cliente_id))).select_from(Prestamo).where(Prestamo.id.in_(ids_ana))) or 0,
            "monto_total_mora": monto_ana,
            "promedio_dias_mora": promedio_dias_mora,
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


# Rangos de días atrasados para informe pago vencido en pestañas
RANGOS_ATRASO = [
    {"key": "1_dia", "label": "1 día atrasado", "min_dias": 1, "max_dias": 14},
    {"key": "15_dias", "label": "15 días atrasado", "min_dias": 15, "max_dias": 29},
    {"key": "30_dias", "label": "30 días atrasado", "min_dias": 30, "max_dias": 59},
    {"key": "2_meses", "label": "2 meses atrasado", "min_dias": 60, "max_dias": 60},
    {"key": "61_dias", "label": "Más de 61 días", "min_dias": 61, "max_dias": 99999},
]


@router.get("/morosidad/por-rangos")
def get_morosidad_por_rangos(
    db: Session = Depends(get_db),
    fecha_corte: Optional[str] = Query(None),
):
    """Informe pago vencido por rangos de días. Datos para viñetas: cédula, nombres, total financiamiento,
    pagos totales, saldo, último pago (fecha), próximo pago (fecha). Una pestaña por rango."""
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

            def _fecha_iso(d):
                if d is None:
                    return None
                if hasattr(d, "date"):
                    d = d.date() if callable(getattr(d, "date", None)) else d
                return d.isoformat()[:10] if hasattr(d, "isoformat") else str(d)[:10]

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


def _generar_excel_morosidad(data: dict) -> bytes:
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Morosidad"
    ws.append(["Reporte de Morosidad", data.get("fecha_corte", "")])
    ws.append([])
    ws.append(["Total préstamos en mora", data.get("total_prestamos_mora", 0)])
    ws.append(["Total clientes en mora", data.get("total_clientes_mora", 0)])
    ws.append(["Monto total mora", data.get("monto_total_mora", 0)])
    ws.append(["Promedio días mora", data.get("promedio_dias_mora", 0)])
    ws.append([])
    ws.append(["Morosidad por analista"])
    ws.append(["Analista", "Cant. préstamos", "Cant. clientes", "Monto mora", "Prom. días"])
    for r in data.get("morosidad_por_analista", []):
        ws.append([r.get("analista", ""), r.get("cantidad_prestamos", 0), r.get("cantidad_clientes", 0), r.get("monto_total_mora", 0), r.get("promedio_dias_mora", 0)])
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
    story.append(Paragraph("Reporte de Morosidad (Pago vencido)", styles["Title"]))
    story.append(Paragraph(f"Fecha de corte: {data.get('fecha_corte', '')}", styles["Normal"]))
    story.append(Spacer(1, 12))
    resumen = [
        ["Total préstamos en mora", str(data.get("total_prestamos_mora", 0))],
        ["Total clientes en mora", str(data.get("total_clientes_mora", 0))],
        ["Monto total mora", str(data.get("monto_total_mora", 0))],
        ["Promedio días mora", str(data.get("promedio_dias_mora", 0))],
    ]
    t = Table(resumen)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), "#e0e0e0"), ("GRID", (0, 0), (-1, -1), 0.5, "#ccc")]))
    story.append(t)
    mora_analista = data.get("morosidad_por_analista", [])
    if mora_analista:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Morosidad por analista", styles["Heading2"]))
        rows = [["Analista", "Préstamos", "Clientes", "Monto mora", "Prom. días"]]
        for r in mora_analista:
            rows.append([r.get("analista", ""), str(r.get("cantidad_prestamos", 0)), str(r.get("cantidad_clientes", 0)), str(r.get("monto_total_mora", 0)), str(r.get("promedio_dias_mora", 0))])
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
):
    """Exporta reporte de morosidad en Excel o PDF."""
    data = get_reporte_morosidad(db=db, fecha_corte=fecha_corte)
    if formato == "pdf":
        content = _generar_pdf_morosidad(data)
        return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=reporte_morosidad_{data['fecha_corte']}.pdf"})
    content = _generar_excel_morosidad(data)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=reporte_morosidad_{data['fecha_corte']}.xlsx"},
    )


# ---------- Reporte Financiero ----------
@router.get("/financiero")
def get_reporte_financiero(
    db: Session = Depends(get_db),
    fecha_corte: Optional[str] = Query(None),
):
    """Reporte financiero. Datos reales desde BD (solo clientes ACTIVOS)."""
    fc = _parse_fecha(fecha_corte)
    conds_activo = [
        Cuota.prestamo_id == Prestamo.id,
        Prestamo.cliente_id == Cliente.id,
        Cliente.estado == "ACTIVO",
        Prestamo.estado == "APROBADO",
    ]
    total_ingresos = _safe_float(
        db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(*conds_activo, Cuota.fecha_pago.isnot(None)))
        )
        or 0
    )
    cantidad_pagos = db.scalar(
        select(func.count())
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(and_(*conds_activo, Cuota.fecha_pago.isnot(None)))
    ) or 0
    cartera_total = _safe_float(
        db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(*conds_activo, Cuota.fecha_pago.is_(None)))
        )
        or 0
    )
    morosidad_total = _safe_float(
        db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(*conds_activo, Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento < fc))
        )
        or 0
    )
    saldo_pendiente = cartera_total
    total_desembolsado = _safe_float(
        db.scalar(
            select(func.coalesce(func.sum(Prestamo.total_financiamiento), 0))
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(Cliente.estado == "ACTIVO", Prestamo.estado == "APROBADO")
        )
        or 0
    )
    porcentaje_cobrado = (total_ingresos / total_desembolsado * 100) if total_desembolsado else 0

    # Ingresos por mes: cuotas pagadas agrupadas por mes de fecha_pago
    q_ingresos = (
        select(
            func.to_char(func.date_trunc("month", Cuota.fecha_pago), "YYYY-MM").label("mes"),
            func.count().label("cantidad_pagos"),
            func.coalesce(func.sum(Cuota.monto), 0).label("monto_total"),
        )
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(and_(*conds_activo, Cuota.fecha_pago.isnot(None)))
        .group_by(func.date_trunc("month", Cuota.fecha_pago))
        .order_by(func.date_trunc("month", Cuota.fecha_pago))
    )
    rows_ing = db.execute(q_ingresos).all()
    ingresos_por_mes = [
        {"mes": r.mes, "cantidad_pagos": r.cantidad_pagos, "monto_total": round(_safe_float(r.monto_total), 2)}
        for r in rows_ing
    ]

    # Egresos programados: cuotas pendientes de pago agrupadas por mes de vencimiento
    q_egresos = (
        select(
            func.to_char(func.date_trunc("month", Cuota.fecha_vencimiento), "YYYY-MM").label("mes"),
            func.count().label("cantidad_cuotas"),
            func.coalesce(func.sum(Cuota.monto), 0).label("monto_programado"),
        )
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(and_(*conds_activo, Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento.isnot(None)))
        .group_by(func.date_trunc("month", Cuota.fecha_vencimiento))
        .order_by(func.date_trunc("month", Cuota.fecha_vencimiento))
    )
    rows_egr = db.execute(q_egresos).all()
    egresos_programados = [
        {"mes": r.mes, "cantidad_cuotas": r.cantidad_cuotas, "monto_programado": round(_safe_float(r.monto_programado), 2)}
        for r in rows_egr
    ]

    # Flujo de caja: ingresos - egresos por mes (meses que aparecen en ingresos o egresos)
    meses_set = {x["mes"] for x in ingresos_por_mes} | {x["mes"] for x in egresos_programados}
    ing_map = {x["mes"]: x["monto_total"] for x in ingresos_por_mes}
    egr_map = {x["mes"]: x["monto_programado"] for x in egresos_programados}
    flujo_caja = []
    for m in sorted(meses_set):
        ing = ing_map.get(m, 0)
        egr = egr_map.get(m, 0)
        flujo_caja.append({
            "mes": m,
            "ingresos": ing,
            "egresos_programados": egr,
            "flujo_neto": round(ing - egr, 2),
        })

    return {
        "fecha_corte": fc.isoformat(),
        "total_ingresos": total_ingresos,
        "cantidad_pagos": cantidad_pagos,
        "cartera_total": cartera_total,
        "cartera_pendiente": cartera_total,
        "morosidad_total": morosidad_total,
        "saldo_pendiente": saldo_pendiente,
        "porcentaje_cobrado": round(porcentaje_cobrado, 2),
        "ingresos_por_mes": ingresos_por_mes,
        "egresos_programados": egresos_programados,
        "flujo_caja": flujo_caja,
    }


@router.get("/exportar/financiero")
def exportar_financiero(
    db: Session = Depends(get_db),
    formato: str = Query("excel", pattern="^(excel|pdf)$"),
    fecha_corte: Optional[str] = Query(None),
):
    """Exporta reporte financiero en Excel o PDF."""
    data = get_reporte_financiero(db=db, fecha_corte=fecha_corte)
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Financiero"
    ws.append(["Reporte Financiero", data.get("fecha_corte", "")])
    ws.append(["Total ingresos", data.get("total_ingresos", 0)])
    ws.append(["Cantidad pagos", data.get("cantidad_pagos", 0)])
    ws.append(["Cartera total", data.get("cartera_total", 0)])
    ws.append(["Morosidad total", data.get("morosidad_total", 0)])
    ws.append(["Porcentaje cobrado", data.get("porcentaje_cobrado", 0)])
    buf = io.BytesIO()
    wb.save(buf)
    content = buf.getvalue()
    if formato == "pdf":
        pdf_content = _generar_pdf_financiero(data)
        return Response(content=pdf_content, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=reporte_financiero_{data['fecha_corte']}.pdf"})
    return Response(content=content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename=reporte_financiero_{data['fecha_corte']}.xlsx"})


def _generar_pdf_financiero(data: dict) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("Reporte Financiero", styles["Title"]))
    story.append(Paragraph(f"Fecha de corte: {data.get('fecha_corte', '')}", styles["Normal"]))
    story.append(Spacer(1, 12))
    resumen = [
        ["Total ingresos", str(data.get("total_ingresos", 0))],
        ["Cantidad pagos", str(data.get("cantidad_pagos", 0))],
        ["Cartera total", str(data.get("cartera_total", 0))],
        ["Morosidad total", str(data.get("morosidad_total", 0))],
        ["Porcentaje cobrado (%)", str(data.get("porcentaje_cobrado", 0))],
    ]
    t = Table(resumen)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), "#e0e0e0"), ("GRID", (0, 0), (-1, -1), 0.5, "#ccc")]))
    story.append(t)
    flujo = data.get("flujo_caja", [])
    if flujo:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Flujo de caja", styles["Heading2"]))
        rows = [["Mes", "Ingresos", "Egresos programados", "Flujo neto"]]
        for r in flujo:
            rows.append([r.get("mes", ""), str(r.get("ingresos", 0)), str(r.get("egresos_programados", 0)), str(r.get("flujo_neto", 0))])
        t2 = Table(rows)
        t2.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), "#e0e0e0"), ("GRID", (0, 0), (-1, -1), 0.5, "#ccc")]))
        story.append(t2)
    doc.build(story)
    return buf.getvalue()


# ---------- Reporte Asesores ----------
@router.get("/asesores/por-mes")
def get_asesores_por_mes(
    db: Session = Depends(get_db),
    meses: int = Query(12, ge=1, le=24, description="Cantidad de meses hacia atrás"),
):
    """Asesores por mes: una pestaña por mes. Columnas: Nombre analista, Total morosidad, Total préstamos. Orden descendente por morosidad."""
    hoy = date.today()
    resultado: dict = {"meses": []}

    for i in range(meses):
        año = hoy.year
        mes = hoy.month - i
        while mes <= 0:
            mes += 12
            año -= 1
        inicio = date(año, mes, 1)
        _, ultimo = calendar.monthrange(año, mes)
        fin = date(año, mes, ultimo)
        fc = fin

        rows = db.execute(
            select(
                Prestamo.analista,
                func.coalesce(func.sum(Cuota.monto), 0).label("morosidad_total"),
                func.count(func.distinct(Cuota.prestamo_id)).label("total_prestamos"),
            )
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                Cliente.estado == "ACTIVO",
                Prestamo.estado == "APROBADO",
                Cuota.fecha_pago.is_(None),
                Cuota.fecha_vencimiento < fc,
            )
            .group_by(Prestamo.analista)
            .order_by(func.sum(Cuota.monto).desc())
        ).fetchall()

        items = [
            {
                "analista": r.analista or "Sin asignar",
                "morosidad_total": round(_safe_float(r.morosidad_total), 2),
                "total_prestamos": r.total_prestamos or 0,
            }
            for r in rows
        ]

        resultado["meses"].append({
            "mes": mes,
            "año": año,
            "label": f"{mes:02d}/{año}",
            "items": items,
        })

    return resultado


@router.get("/asesores")
def get_reporte_asesores(
    db: Session = Depends(get_db),
    fecha_corte: Optional[str] = Query(None),
):
    """Reporte por asesor/analista. Datos reales desde BD (solo clientes ACTIVOS)."""
    fc = _parse_fecha(fecha_corte)
    analistas = db.execute(
        select(Prestamo.analista)
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(Cliente.estado == "ACTIVO", Prestamo.estado == "APROBADO")
        .distinct()
    ).fetchall()
    resumen_por_analista: List[dict] = []
    for (analista,) in analistas:
        if not analista:
            continue
        prestamos = db.execute(
            select(Prestamo.id)
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                Cliente.estado == "ACTIVO",
                Prestamo.analista == analista,
                Prestamo.estado == "APROBADO",
            )
        ).fetchall()
        ids = [x[0] for x in prestamos]
        total_prestamos = len(ids)
        total_clientes = db.scalar(select(func.count(func.distinct(Prestamo.cliente_id))).select_from(Prestamo).where(Prestamo.id.in_(ids))) or 0
        cartera_total = _safe_float(db.scalar(select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(Cuota.fecha_pago.is_(None), Cuota.prestamo_id.in_(ids)))) or 0
        morosidad_total = _safe_float(db.scalar(select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento < fc, Cuota.prestamo_id.in_(ids)))) or 0
        total_cobrado = _safe_float(db.scalar(select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(Cuota.fecha_pago.isnot(None), Cuota.prestamo_id.in_(ids)))) or 0
        porcentaje_cobrado = (total_cobrado / (total_cobrado + cartera_total) * 100) if (total_cobrado + cartera_total) else 0
        porcentaje_morosidad = (morosidad_total / cartera_total * 100) if cartera_total else 0
        resumen_por_analista.append({
            "analista": analista,
            "total_prestamos": total_prestamos,
            "total_clientes": total_clientes,
            "cartera_total": cartera_total,
            "morosidad_total": morosidad_total,
            "total_cobrado": total_cobrado,
            "porcentaje_cobrado": round(porcentaje_cobrado, 2),
            "porcentaje_morosidad": round(porcentaje_morosidad, 2),
        })
    return {
        "fecha_corte": fc.isoformat(),
        "resumen_por_analista": resumen_por_analista,
        "desempeno_mensual": [],
        "clientes_por_analista": [],
    }


@router.get("/exportar/asesores")
def exportar_asesores(
    db: Session = Depends(get_db),
    formato: str = Query("excel", pattern="^(excel|pdf)$"),
    fecha_corte: Optional[str] = Query(None),
):
    """Exporta reporte asesores en Excel o PDF."""
    data = get_reporte_asesores(db=db, fecha_corte=fecha_corte)
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Asesores"
    ws.append(["Analista", "Préstamos", "Clientes", "Cartera", "Morosidad", "Cobrado", "% Cobrado", "% Mora"])
    for r in data.get("resumen_por_analista", []):
        ws.append([r.get("analista", ""), r.get("total_prestamos", 0), r.get("total_clientes", 0), r.get("cartera_total", 0), r.get("morosidad_total", 0), r.get("total_cobrado", 0), r.get("porcentaje_cobrado", 0), r.get("porcentaje_morosidad", 0)])
    buf = io.BytesIO()
    wb.save(buf)
    content = buf.getvalue()
    if formato == "pdf":
        pdf_content = _generar_pdf_asesores(data)
        return Response(content=pdf_content, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=reporte_asesores_{data['fecha_corte']}.pdf"})
    return Response(content=content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename=reporte_asesores_{data['fecha_corte']}.xlsx"})


def _generar_pdf_asesores(data: dict) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("Reporte de Asesores", styles["Title"]))
    story.append(Paragraph(f"Fecha de corte: {data.get('fecha_corte', '')}", styles["Normal"]))
    story.append(Spacer(1, 12))
    rows = [["Analista", "Préstamos", "Clientes", "Cartera", "Morosidad", "Cobrado", "% Cobrado", "% Mora"]]
    for r in data.get("resumen_por_analista", []):
        rows.append([r.get("analista", ""), str(r.get("total_prestamos", 0)), str(r.get("total_clientes", 0)), str(r.get("cartera_total", 0)), str(r.get("morosidad_total", 0)), str(r.get("total_cobrado", 0)), str(r.get("porcentaje_cobrado", 0)), str(r.get("porcentaje_morosidad", 0))])
    t = Table(rows)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), "#e0e0e0"), ("GRID", (0, 0), (-1, -1), 0.5, "#ccc")]))
    story.append(t)
    doc.build(story)
    return buf.getvalue()


# ---------- Reporte Productos ----------
@router.get("/productos/por-mes")
def get_productos_por_mes(
    db: Session = Depends(get_db),
    meses: int = Query(12, ge=1, le=24, description="Cantidad de meses hacia atrás"),
):
    """Productos por mes: una pestaña por mes. Columnas: Modelo, Suma total ventas (70% valor prestado) por modelo."""
    hoy = date.today()
    resultado: dict = {"meses": []}
    fecha_ref = func.coalesce(func.date(Prestamo.fecha_aprobacion), func.date(Prestamo.fecha_registro))

    for i in range(meses):
        año = hoy.year
        mes = hoy.month - i
        while mes <= 0:
            mes += 12
            año -= 1
        inicio = date(año, mes, 1)
        _, ultimo = calendar.monthrange(año, mes)
        fin = date(año, mes, ultimo)

        rows = db.execute(
            select(
                Prestamo.modelo_vehiculo,
                func.coalesce(func.sum(Prestamo.total_financiamiento * 0.70), 0).label("suma_ventas"),
            )
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                Cliente.estado == "ACTIVO",
                Prestamo.estado == "APROBADO",
                fecha_ref >= inicio,
                fecha_ref <= fin,
            )
            .group_by(Prestamo.modelo_vehiculo)
            .order_by(func.sum(Prestamo.total_financiamiento).desc())
        ).fetchall()

        items = [
            {"modelo": r.modelo_vehiculo or "Sin modelo", "suma_ventas": round(_safe_float(r.suma_ventas), 2)}
            for r in rows
        ]

        resultado["meses"].append({
            "mes": mes,
            "año": año,
            "label": f"{mes:02d}/{año}",
            "items": items,
        })

    return resultado


@router.get("/productos")
def get_reporte_productos(
    db: Session = Depends(get_db),
    fecha_corte: Optional[str] = Query(None),
):
    """Reporte por producto. Datos reales desde BD."""
    fc = _parse_fecha(fecha_corte)
    productos = db.execute(
        select(Prestamo.producto)
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(Cliente.estado == "ACTIVO", Prestamo.estado == "APROBADO")
        .distinct()
    ).fetchall()
    resumen_por_producto: List[dict] = []
    for (producto,) in productos:
        if not producto:
            continue
        prestamos = db.execute(
            select(Prestamo.id)
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                Cliente.estado == "ACTIVO",
                Prestamo.producto == producto,
                Prestamo.estado == "APROBADO",
            )
        ).fetchall()
        ids = [x[0] for x in prestamos]
        total_prestamos = len(ids)
        total_clientes = db.scalar(select(func.count(func.distinct(Prestamo.cliente_id))).select_from(Prestamo).where(Prestamo.id.in_(ids))) or 0
        cartera_total = _safe_float(db.scalar(select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(Cuota.fecha_pago.is_(None), Cuota.prestamo_id.in_(ids)))) or 0
        promedio_prestamo = _safe_float(db.scalar(select(func.avg(Prestamo.total_financiamiento)).select_from(Prestamo).where(Prestamo.id.in_(ids)))) or 0
        total_cobrado = _safe_float(db.scalar(select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(Cuota.fecha_pago.isnot(None), Cuota.prestamo_id.in_(ids)))) or 0
        morosidad_total = _safe_float(db.scalar(select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento < fc, Cuota.prestamo_id.in_(ids)))) or 0
        porcentaje_cobrado = (total_cobrado / (total_cobrado + cartera_total) * 100) if (total_cobrado + cartera_total) else 0
        resumen_por_producto.append({
            "producto": producto,
            "total_prestamos": total_prestamos,
            "total_clientes": total_clientes,
            "cartera_total": cartera_total,
            "promedio_prestamo": round(promedio_prestamo, 2),
            "total_cobrado": total_cobrado,
            "morosidad_total": morosidad_total,
            "porcentaje_cobrado": round(porcentaje_cobrado, 2),
        })
    productos_por_concesionario: List[dict] = []
    concesionarios = db.execute(
        select(Prestamo.concesionario)
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(Cliente.estado == "ACTIVO", Prestamo.estado == "APROBADO")
        .distinct()
    ).fetchall()
    for (conc,) in concesionarios:
        if not conc:
            continue
        for (producto,) in productos:
            if not producto:
                continue
            cnt = db.scalar(
                select(func.count())
                .select_from(Prestamo)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Cliente.estado == "ACTIVO",
                    Prestamo.concesionario == conc,
                    Prestamo.producto == producto,
                    Prestamo.estado == "APROBADO",
                )
            ) or 0
            if cnt:
                monto = _safe_float(
                    db.scalar(
                        select(func.sum(Prestamo.total_financiamiento))
                        .select_from(Prestamo)
                        .join(Cliente, Prestamo.cliente_id == Cliente.id)
                        .where(
                            Cliente.estado == "ACTIVO",
                            Prestamo.concesionario == conc,
                            Prestamo.producto == producto,
                            Prestamo.estado == "APROBADO",
                        )
                    )
                    or 0
                )
                productos_por_concesionario.append({"concesionario": conc, "producto": producto, "cantidad_prestamos": cnt, "monto_total": monto})
    return {
        "fecha_corte": fc.isoformat(),
        "resumen_por_producto": resumen_por_producto,
        "productos_por_concesionario": productos_por_concesionario,
        "tendencia_mensual": [],
    }


@router.get("/exportar/productos")
def exportar_productos(
    db: Session = Depends(get_db),
    formato: str = Query("excel", pattern="^(excel|pdf)$"),
    fecha_corte: Optional[str] = Query(None),
):
    """Exporta reporte productos en Excel o PDF."""
    data = get_reporte_productos(db=db, fecha_corte=fecha_corte)
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Productos"
    ws.append(["Producto", "Préstamos", "Clientes", "Cartera", "Promedio", "Cobrado", "Mora", "% Cobrado"])
    for r in data.get("resumen_por_producto", []):
        ws.append([r.get("producto", ""), r.get("total_prestamos", 0), r.get("total_clientes", 0), r.get("cartera_total", 0), r.get("promedio_prestamo", 0), r.get("total_cobrado", 0), r.get("morosidad_total", 0), r.get("porcentaje_cobrado", 0)])
    buf = io.BytesIO()
    wb.save(buf)
    content = buf.getvalue()
    if formato == "pdf":
        pdf_content = _generar_pdf_productos(data)
        return Response(content=pdf_content, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=reporte_productos_{data['fecha_corte']}.pdf"})
    return Response(content=content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename=reporte_productos_{data['fecha_corte']}.xlsx"})


def _generar_pdf_productos(data: dict) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("Reporte de Productos", styles["Title"]))
    story.append(Paragraph(f"Fecha de corte: {data.get('fecha_corte', '')}", styles["Normal"]))
    story.append(Spacer(1, 12))
    rows = [["Producto", "Préstamos", "Clientes", "Cartera", "Promedio", "Cobrado", "Mora", "% Cobrado"]]
    for r in data.get("resumen_por_producto", []):
        rows.append([r.get("producto", ""), str(r.get("total_prestamos", 0)), str(r.get("total_clientes", 0)), str(r.get("cartera_total", 0)), str(r.get("promedio_prestamo", 0)), str(r.get("total_cobrado", 0)), str(r.get("morosidad_total", 0)), str(r.get("porcentaje_cobrado", 0))])
    t = Table(rows)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), "#e0e0e0"), ("GRID", (0, 0), (-1, -1), 0.5, "#ccc")]))
    story.append(t)
    prod_conc = data.get("productos_por_concesionario", [])
    if prod_conc:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Productos por concesionario", styles["Heading2"]))
        rows2 = [["Concesionario", "Producto", "Cant. préstamos", "Monto total"]]
        for r in prod_conc:
            rows2.append([r.get("concesionario", ""), r.get("producto", ""), str(r.get("cantidad_prestamos", 0)), str(r.get("monto_total", 0))])
        t2 = Table(rows2)
        t2.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), "#e0e0e0"), ("GRID", (0, 0), (-1, -1), 0.5, "#ccc")]))
        story.append(t2)
    doc.build(story)
    return buf.getvalue()
