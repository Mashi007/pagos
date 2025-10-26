import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

# Imports para Excel
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4

# Imports para reportes PDF
from reportlab.pdfgen import canvas
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.constants import EstadoPrestamo
from app.models.cliente import Cliente
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


class ReporteCartera(BaseModel):
    """Schema para reporte de cartera"""

    fecha_corte: date
    cartera_total: Decimal
    capital_pendiente: Decimal
    intereses_pendientes: Decimal
    mora_total: Decimal
    cantidad_prestamos_activos: int
    cantidad_prestamos_mora: int
    distribucion_por_monto: list[dict]
    distribucion_por_mora: list[dict]


class ReportePagos(BaseModel):
    """Schema para reporte de pagos"""

    fecha_inicio: date
    fecha_fin: date
    total_pagos: Decimal
    cantidad_pagos: int
    pagos_por_metodo: list[dict]
    pagos_por_dia: list[dict]


@router.get("/cartera", response_model=ReporteCartera)
def reporte_cartera(
    fecha_corte: Optional[date] = Query(None, description="Fecha de corte"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera reporte de cartera al día de corte."""
    try:
        if not fecha_corte:
            fecha_corte = date.today()

        # Cartera total
        cartera_total = db.query(func.sum(Prestamo.monto_total)).filter(
            Prestamo.estado.in_([EstadoPrestamo.ACTIVO, EstadoPrestamo.EN_MORA])
        ).scalar() or Decimal("0")

        # Capital pendiente
        capital_pendiente = db.query(func.sum(Prestamo.saldo_pendiente)).filter(
            Prestamo.estado.in_([EstadoPrestamo.ACTIVO, EstadoPrestamo.EN_MORA])
        ).scalar() or Decimal("0")

        # Intereses pendientes
        intereses_pendientes = cartera_total - capital_pendiente

        # Mora total
        mora_total = db.query(func.sum(Prestamo.monto_mora)).filter(
            Prestamo.estado == EstadoPrestamo.EN_MORA
        ).scalar() or Decimal("0")

        # Cantidad de préstamos
        cantidad_prestamos_activos = (
            db.query(Prestamo).filter(Prestamo.estado == EstadoPrestamo.ACTIVO).count()
        )

        cantidad_prestamos_mora = (
            db.query(Prestamo).filter(Prestamo.estado == EstadoPrestamo.EN_MORA).count()
        )

        # Distribución por monto
        distribucion_por_monto = (
            db.query(
                func.count(Prestamo.id).label("cantidad"),
                func.sum(Prestamo.monto_total).label("monto"),
            )
            .filter(
                Prestamo.estado.in_([EstadoPrestamo.ACTIVO, EstadoPrestamo.EN_MORA])
            )
            .group_by(
                func.case(
                    (Prestamo.monto_total <= 1000, "Hasta $1,000"),
                    (Prestamo.monto_total <= 5000, "$1,001 - $5,000"),
                    (Prestamo.monto_total <= 10000, "$5,001 - $10,000"),
                    else_="Más de $10,000",
                )
            )
            .all()
        )

        # Distribución por mora
        rangos_mora = [
            {"min": 1, "max": 30, "label": "1-30 días"},
            {"min": 31, "max": 60, "label": "31-60 días"},
            {"min": 61, "max": 90, "label": "61-90 días"},
            {"min": 91, "max": 999999, "label": "Más de 90 días"},
        ]

        distribucion_por_mora = []
        for rango in rangos_mora:
            cantidad = (
                db.query(Prestamo)
                .filter(
                    Prestamo.estado == EstadoPrestamo.EN_MORA,
                    Prestamo.dias_mora >= rango["min"],
                    Prestamo.dias_mora <= rango["max"],
                )
                .count()
            )

            monto_mora = db.query(func.sum(Prestamo.monto_mora)).filter(
                Prestamo.estado == EstadoPrestamo.EN_MORA,
                Prestamo.dias_mora >= rango["min"],
                Prestamo.dias_mora <= rango["max"],
            ).scalar() or Decimal("0")

            distribucion_por_mora.append(
                {
                    "rango": rango["label"],
                    "cantidad": cantidad,
                    "monto_total": monto_mora,
                }
            )

        return ReporteCartera(
            fecha_corte=fecha_corte,
            cartera_total=cartera_total,
            capital_pendiente=capital_pendiente,
            intereses_pendientes=intereses_pendientes,
            mora_total=mora_total,
            cantidad_prestamos_activos=cantidad_prestamos_activos,
            cantidad_prestamos_mora=cantidad_prestamos_mora,
            distribucion_por_monto=[
                {"rango": item[0], "cantidad": item[1], "monto": item[2]}
                for item in distribucion_por_monto
            ],
            distribucion_por_mora=distribucion_por_mora,
        )

    except Exception as e:
        logger.error(f"Error generando reporte de cartera: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/pagos", response_model=ReportePagos)
def reporte_pagos(
    fecha_inicio: date = Query(..., description="Fecha de inicio"),
    fecha_fin: date = Query(..., description="Fecha de fin"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera reporte de pagos en un rango de fechas."""
    try:
        # Total de pagos
        total_pagos = db.query(func.sum(Pago.monto)).filter(
            Pago.fecha_pago >= fecha_inicio,
            Pago.fecha_pago <= fecha_fin,
        ).scalar() or Decimal("0")

        cantidad_pagos = (
            db.query(Pago)
            .filter(
                Pago.fecha_pago >= fecha_inicio,
                Pago.fecha_pago <= fecha_fin,
            )
            .count()
        )

        # Pagos por método
        pagos_por_metodo = (
            db.query(
                Pago.metodo_pago,
                func.count(Pago.id).label("cantidad"),
                func.sum(Pago.monto).label("monto"),
            )
            .filter(
                Pago.fecha_pago >= fecha_inicio,
                Pago.fecha_pago <= fecha_fin,
            )
            .group_by(Pago.metodo_pago)
            .all()
        )

        # Pagos por día
        pagos_por_dia = (
            db.query(
                func.date(Pago.fecha_pago).label("fecha"),
                func.count(Pago.id).label("cantidad"),
                func.sum(Pago.monto).label("monto"),
            )
            .filter(
                Pago.fecha_pago >= fecha_inicio,
                Pago.fecha_pago <= fecha_fin,
            )
            .group_by(func.date(Pago.fecha_pago))
            .all()
        )

        return ReportePagos(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            total_pagos=total_pagos,
            cantidad_pagos=cantidad_pagos,
            pagos_por_metodo=[
                {"metodo": item[0], "cantidad": item[1], "monto": item[2]}
                for item in pagos_por_metodo
            ],
            pagos_por_dia=[
                {"fecha": item[0], "cantidad": item[1], "monto": item[2]}
                for item in pagos_por_dia
            ],
        )

    except Exception as e:
        logger.error(f"Error generando reporte de pagos: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/exportar/cartera")
def exportar_reporte_cartera(
    formato: str = Query("excel", description="Formato: excel o pdf"),
    fecha_corte: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exporta reporte de cartera en Excel o PDF."""
    try:
        # Obtener datos del reporte
        reporte = reporte_cartera(fecha_corte, db, current_user)

        if formato.lower() == "excel":
            # Crear archivo Excel
            from openpyxl import Workbook

            wb = Workbook()
            ws = wb.active
            ws.title = "Reporte Cartera"

            # Encabezados
            ws["A1"] = "REPORTE DE CARTERA"
            ws["A2"] = f"Fecha de Corte: {reporte.fecha_corte}"

            # Datos principales
            ws["A4"] = "Cartera Total:"
            ws["B4"] = f"${reporte.cartera_total:,.2f}"

            ws["A5"] = "Capital Pendiente:"
            ws["B5"] = f"${reporte.capital_pendiente:,.2f}"

            ws["A6"] = "Intereses Pendientes:"
            ws["B6"] = f"${reporte.intereses_pendientes:,.2f}"

            ws["A7"] = "Mora Total:"
            ws["B7"] = f"${reporte.mora_total:,.2f}"

            # Guardar en memoria
            from io import BytesIO

            output = BytesIO()
            wb.save(output)
            output.seek(0)

            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename=reporte_cartera_{reporte.fecha_corte}.xlsx"
                },
            )

        elif formato.lower() == "pdf":
            # Crear archivo PDF
            from io import BytesIO

            output = BytesIO()
            c = canvas.Canvas(output, pagesize=A4)

            # Título
            c.setFont("Helvetica-Bold", 16)
            c.drawString(100, 750, "REPORTE DE CARTERA")

            c.setFont("Helvetica", 12)
            c.drawString(100, 720, f"Fecha de Corte: {reporte.fecha_corte}")

            # Datos
            y = 680
            c.drawString(100, y, f"Cartera Total: ${reporte.cartera_total:,.2f}")
            y -= 20
            c.drawString(
                100, y, f"Capital Pendiente: ${reporte.capital_pendiente:,.2f}"
            )
            y -= 20
            c.drawString(
                100, y, f"Intereses Pendientes: ${reporte.intereses_pendientes:,.2f}"
            )
            y -= 20
            c.drawString(100, y, f"Mora Total: ${reporte.mora_total:,.2f}")

            c.save()
            output.seek(0)

            return StreamingResponse(
                output,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=reporte_cartera_{reporte.fecha_corte}.pdf"
                },
            )

        else:
            raise HTTPException(
                status_code=400, detail="Formato no soportado. Use 'excel' o 'pdf'"
            )

    except Exception as e:
        logger.error(f"Error exportando reporte: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/dashboard/resumen")
def resumen_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene resumen para dashboard."""
    try:
        # Estadísticas básicas
        total_clientes = db.query(Cliente).count()
        total_prestamos = db.query(Prestamo).count()
        total_pagos = db.query(Pago).count()

        # Cartera activa
        cartera_activa = db.query(func.sum(Prestamo.saldo_pendiente)).filter(
            Prestamo.estado.in_([EstadoPrestamo.ACTIVO, EstadoPrestamo.EN_MORA])
        ).scalar() or Decimal("0")

        # Mora
        prestamos_mora = (
            db.query(Prestamo).filter(Prestamo.estado == EstadoPrestamo.EN_MORA).count()
        )

        # Pagos del mes
        fecha_inicio_mes = date.today().replace(day=1)
        pagos_mes = db.query(func.sum(Pago.monto)).filter(
            Pago.fecha_pago >= fecha_inicio_mes
        ).scalar() or Decimal("0")

        return {
            "total_clientes": total_clientes,
            "total_prestamos": total_prestamos,
            "total_pagos": total_pagos,
            "cartera_activa": cartera_activa,
            "prestamos_mora": prestamos_mora,
            "pagos_mes": pagos_mes,
            "fecha_actualizacion": datetime.now(),
        }

    except Exception as e:
        logger.error(f"Error obteniendo resumen: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )
