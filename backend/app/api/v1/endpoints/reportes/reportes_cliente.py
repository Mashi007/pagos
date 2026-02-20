"""
Reportes por cliente - PDF pendientes y amortización.
"""
import io
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo

router = APIRouter(dependencies=[Depends(get_current_user)])


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
    story.append(Paragraph(f"Cliente: {nombre or '-'}", styles["Normal"]))
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
    story.append(Paragraph(f"Cliente: {nombre or '-'}", styles["Normal"]))
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
                c.get("fecha_pago") or "-",
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
            fecha_pago_str = fp.isoformat() if fp else "-"
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
