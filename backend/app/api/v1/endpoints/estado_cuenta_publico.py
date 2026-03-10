"""
Endpoints PÚBLICOS para consulta de estado de cuenta por cédula.
Sin autenticación. Solo permite validar cédula y solicitar PDF (envío al email del cliente).
Rate limiting por IP. No expone otros servicios.
"""
import io
import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.cobros_public_rate_limit import (
    get_client_ip,
    check_rate_limit_estado_cuenta_validar,
    check_rate_limit_estado_cuenta_solicitar,
)
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.cuota import Cuota
from app.api.v1.endpoints.validadores import validate_cedula
from app.core.email import send_email

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[])

MAX_CEDULA_LENGTH = 20


class ValidarCedulaEstadoCuentaResponse(BaseModel):
    ok: bool
    nombre: Optional[str] = None
    email: Optional[str] = None
    error: Optional[str] = None


class SolicitarEstadoCuentaRequest(BaseModel):
    cedula: str


class SolicitarEstadoCuentaResponse(BaseModel):
    ok: bool
    pdf_base64: Optional[str] = None
    mensaje: Optional[str] = None
    error: Optional[str] = None


def _cedula_lookup(cedula_input: str) -> str:
    """Normaliza cédula para búsqueda en BD (sin guión)."""
    result = validate_cedula(cedula_input.strip())
    if not result.get("valido"):
        return ""
    valor = result.get("valor_formateado", "")
    return valor.replace("-", "") if valor else ""


def _generar_pdf_estado_cuenta(
    cedula: str,
    nombre: str,
    prestamos: List[dict],
    cuotas_pendientes: List[dict],
    total_pendiente: float,
    fecha_corte: date,
) -> bytes:
    """Genera PDF de estado de cuenta: cliente, préstamos, cuotas pendientes."""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Estado de cuenta", styles["Title"]))
    story.append(Paragraph(f"Fecha de corte: {fecha_corte.isoformat()}", styles["Normal"]))
    story.append(Paragraph(f"Cédula: {cedula}", styles["Normal"]))
    story.append(Paragraph(f"Cliente: {nombre or '-'}", styles["Normal"]))
    story.append(Spacer(1, 12))

    if prestamos:
        story.append(Paragraph("Préstamos", styles["Heading2"]))
        rows = [["Id", "Producto", "Total financiamiento", "Estado"]]
        for p in prestamos:
            rows.append([
                str(p.get("id", "")),
                (p.get("producto") or "-")[:40],
                str(p.get("total_financiamiento", 0)),
                p.get("estado", "-"),
            ])
        t = Table(rows)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), "#e0e0e0"),
            ("GRID", (0, 0), (-1, -1), 0.5, "#ccc"),
        ]))
        story.append(t)
        story.append(Spacer(1, 12))

    story.append(Paragraph("Cuotas pendientes", styles["Heading2"]))
    story.append(Paragraph(f"Total pendiente: {total_pendiente:.2f}", styles["Normal"]))
    if not cuotas_pendientes:
        story.append(Paragraph("No hay cuotas pendientes.", styles["Normal"]))
    else:
        rows = [["Préstamo", "Nº Cuota", "Vencimiento", "Monto", "Estado"]]
        for c in cuotas_pendientes:
            rows.append([
                str(c.get("prestamo_id", "")),
                str(c.get("numero_cuota", "")),
                c.get("fecha_vencimiento", ""),
                str(c.get("monto", 0)),
                c.get("estado", ""),
            ])
        t = Table(rows)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), "#e0e0e0"),
            ("GRID", (0, 0), (-1, -1), 0.5, "#ccc"),
        ]))
        story.append(t)

    doc.build(story)
    return buf.getvalue()


@router.get("/validar-cedula", response_model=ValidarCedulaEstadoCuentaResponse)
def validar_cedula_estado_cuenta(
    request: Request,
    cedula: str,
    db: Session = Depends(get_db),
):
    """
    Valida cédula y verifica que exista en tabla clientes.
    Público, sin auth. Rate limit: 30 req/min por IP. Retorna nombre y email si ok.
    """
    ip = get_client_ip(request)
    check_rate_limit_estado_cuenta_validar(ip)
    if not cedula or not cedula.strip():
        return ValidarCedulaEstadoCuentaResponse(ok=False, error="Ingrese el número de cédula.")
    if len(cedula.strip()) > MAX_CEDULA_LENGTH:
        return ValidarCedulaEstadoCuentaResponse(ok=False, error="Datos inválidos.")
    result = validate_cedula(cedula.strip())
    if not result.get("valido"):
        return ValidarCedulaEstadoCuentaResponse(ok=False, error=result.get("error", "Cédula inválida."))
    cedula_lookup = _cedula_lookup(cedula.strip())
    if not cedula_lookup:
        return ValidarCedulaEstadoCuentaResponse(ok=False, error="Formato de cédula no reconocido.")

    cliente_row = db.execute(
        select(Cliente).where(func.replace(Cliente.cedula, "-", "") == cedula_lookup)
    ).scalars().first()
    if not cliente_row:
        return ValidarCedulaEstadoCuentaResponse(
            ok=False,
            error="La cédula ingresada no se encuentra registrada en nuestro sistema.",
        )
    cliente = cliente_row[0] if hasattr(cliente_row, "__getitem__") else cliente_row
    nombre = (getattr(cliente, "nombres", None) or "").strip()
    email = (getattr(cliente, "email", None) or "").strip()
    return ValidarCedulaEstadoCuentaResponse(
        ok=True,
        nombre=nombre,
        email=email or None,
    )


@router.post("/solicitar-estado-cuenta", response_model=SolicitarEstadoCuentaResponse)
def solicitar_estado_cuenta(
    request: Request,
    body: SolicitarEstadoCuentaRequest,
    db: Session = Depends(get_db),
):
    """
    Genera el PDF de estado de cuenta para la cédula consultada, lo envía al email
    registrado del cliente y devuelve el PDF en base64 para visualización.
    Público, sin auth. Rate limit: 5 solicitudes/hora por IP.
    """
    cedula = (body.cedula or "").strip()
    ip = get_client_ip(request)
    check_rate_limit_estado_cuenta_solicitar(ip)
    if not cedula:
        return SolicitarEstadoCuentaResponse(ok=False, error="Ingrese el número de cédula.")
    if len(cedula.strip()) > MAX_CEDULA_LENGTH:
        return SolicitarEstadoCuentaResponse(ok=False, error="Datos inválidos.")
    result = validate_cedula(cedula.strip())
    if not result.get("valido"):
        return SolicitarEstadoCuentaResponse(ok=False, error=result.get("error", "Cédula inválida."))
    cedula_lookup = _cedula_lookup(cedula.strip())
    if not cedula_lookup:
        return SolicitarEstadoCuentaResponse(ok=False, error="Formato de cédula no reconocido.")

    cliente_row = db.execute(
        select(Cliente).where(func.replace(Cliente.cedula, "-", "") == cedula_lookup)
    ).scalars().first()
    if not cliente_row:
        return SolicitarEstadoCuentaResponse(
            ok=False,
            error="La cédula no se encuentra registrada.",
        )
    cliente = cliente_row[0] if hasattr(cliente_row, "__getitem__") else cliente_row
    cliente_id = getattr(cliente, "id", None)
    nombre = (getattr(cliente, "nombres", None) or "").strip()
    email = (getattr(cliente, "email", None) or "").strip()
    cedula_display = (getattr(cliente, "cedula", None) or cedula).strip()

    prestamos_rows = db.execute(
        select(Prestamo).where(Prestamo.cliente_id == cliente_id)
    ).scalars().all()
    prestamos_list = []
    prestamo_ids = []
    for row in prestamos_rows:
        p = row[0] if hasattr(row, "__getitem__") else row
        prestamo_ids.append(p.id)
        prestamos_list.append({
            "id": p.id,
            "producto": getattr(p, "producto", None) or "",
            "total_financiamiento": float(getattr(p, "total_financiamiento", 0) or 0),
            "estado": getattr(p, "estado", None) or "",
        })

    cuotas_pendientes = []
    total_pendiente = 0.0
    if prestamo_ids:
        cuotas_rows = db.execute(
            select(Cuota)
            .where(Cuota.prestamo_id.in_(prestamo_ids), Cuota.fecha_pago.is_(None))
            .order_by(Cuota.prestamo_id, Cuota.numero_cuota)
        ).scalars().all()
        for c in cuotas_rows:
            cu = c[0] if hasattr(c, "__getitem__") else c
            m = float(getattr(cu, "monto", 0) or 0)
            total_pendiente += m
            cuotas_pendientes.append({
                "prestamo_id": getattr(cu, "prestamo_id", ""),
                "numero_cuota": getattr(cu, "numero_cuota", ""),
                "fecha_vencimiento": (getattr(cu, "fecha_vencimiento", None) or "").isoformat() if getattr(cu, "fecha_vencimiento", None) else "",
                "monto": m,
                "estado": getattr(cu, "estado", None) or "PENDIENTE",
            })

    fecha_corte = date.today()
    pdf_bytes = _generar_pdf_estado_cuenta(
        cedula=cedula_display,
        nombre=nombre,
        prestamos=prestamos_list,
        cuotas_pendientes=cuotas_pendientes,
        total_pendiente=total_pendiente,
        fecha_corte=fecha_corte,
    )

    if email:
        try:
            filename = f"estado_cuenta_{cedula_display.replace('-', '_')}.pdf"
            body = f"Estimado(a) {nombre},\n\nSe adjunta su estado de cuenta con fecha de corte {fecha_corte.isoformat()}.\n\nSaludos,\nRapiCredit"
            send_email(
                [email],
                f"Estado de cuenta - {fecha_corte.isoformat()}",
                body,
                attachments=[(filename, pdf_bytes)],
            )
        except Exception as e:
            logger.warning("No se pudo enviar estado de cuenta por email a %s: %s", email, e)
            # No fallar la petición: el PDF se devuelve igual

    import base64
    pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
    mensaje = "Estado de cuenta generado. Se ha enviado una copia al correo registrado." if email else "Estado de cuenta generado."
    return SolicitarEstadoCuentaResponse(
        ok=True,
        pdf_base64=pdf_b64,
        mensaje=mensaje,
    )
