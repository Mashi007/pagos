import logging
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

# Imports para Excel
from pydantic import BaseModel
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

# Imports para reportes PDF
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.constants import EstadoPrestamo
from app.models.amortizacion import Cuota
from app.models.auditoria import Auditoria
from app.models.cliente import Cliente
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
def healthcheck_reportes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verificación rápida del módulo de Reportes y conexión a BD.

    Ejecuta consultas mínimas para confirmar conectividad y disponibilidad de datos
    necesarios para la generación de reportes de cartera y pagos.
    """
    try:
        logger.info("[reportes.health] Verificando conexión a BD y métricas básicas")

        total_prestamos = db.query(func.count(Prestamo.id)).scalar() or 0
        total_pagos = db.query(func.count(Pago.id)).scalar() or 0

        return {
            "status": "ok",
            "database": True,
            "metrics": {
                "total_prestamos": int(total_prestamos),
                "total_pagos": int(total_pagos),
            },
            "timestamp": datetime.now(),
        }
    except Exception as e:
        logger.error(f"[reportes.health] Error: {e}")
        raise HTTPException(status_code=500, detail="Error de conexión o consulta a la base de datos")


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
        logger.info("[reportes.cartera] Iniciando generación de reporte")
        if not fecha_corte:
            fecha_corte = date.today()

        # Cartera total: suma de total_financiamiento de préstamos APROBADOS
        cartera_total = db.query(func.sum(Prestamo.total_financiamiento)).filter(
            Prestamo.estado == "APROBADO"
        ).scalar() or Decimal("0")

        logger.info(f"[reportes.cartera] Cartera total: {cartera_total}")

        # Capital pendiente: suma de capital_pendiente de todas las cuotas no pagadas
        capital_pendiente = (
            db.query(func.sum(func.coalesce(Cuota.capital_pendiente, Decimal("0.00"))))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Cuota.estado != "PAGADO",
            )
            .scalar()
        ) or Decimal("0")

        logger.info(f"[reportes.cartera] Capital pendiente: {capital_pendiente}")

        # Intereses pendientes: suma de interes_pendiente de todas las cuotas no pagadas
        intereses_pendientes = (
            db.query(func.sum(func.coalesce(Cuota.interes_pendiente, Decimal("0.00"))))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Cuota.estado != "PAGADO",
            )
            .scalar()
        ) or Decimal("0")

        logger.info(f"[reportes.cartera] Intereses pendientes: {intereses_pendientes}")

        # Mora total: suma de monto_mora de todas las cuotas con mora
        mora_total = (
            db.query(func.sum(func.coalesce(Cuota.monto_mora, Decimal("0.00"))))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Cuota.monto_mora > Decimal("0.00"),
            )
            .scalar()
        ) or Decimal("0")

        logger.info(f"[reportes.cartera] Mora total: {mora_total}")

        # Cantidad de préstamos APROBADOS
        cantidad_prestamos_activos = db.query(Prestamo).filter(Prestamo.estado == "APROBADO").count()

        logger.info(f"[reportes.cartera] Préstamos activos: {cantidad_prestamos_activos}")

        # Préstamos con cuotas en mora
        cantidad_prestamos_mora = (
            db.query(func.count(func.distinct(Prestamo.id)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Cuota.monto_mora > Decimal("0.00"),
            )
            .scalar()
        ) or 0

        logger.info(f"[reportes.cartera] Préstamos en mora: {cantidad_prestamos_mora}")

        # Distribución por monto: usar total_financiamiento
        distribucion_por_monto_query = (
            db.query(
                case(
                    (Prestamo.total_financiamiento <= 1000, "Hasta $1,000"),
                    (Prestamo.total_financiamiento <= 5000, "$1,001 - $5,000"),
                    (Prestamo.total_financiamiento <= 10000, "$5,001 - $10,000"),
                    else_="Más de $10,000",
                ).label("rango"),
                func.count(Prestamo.id).label("cantidad"),
                func.sum(Prestamo.total_financiamiento).label("monto"),
            )
            .filter(Prestamo.estado == "APROBADO")
            .group_by("rango")
            .all()
        )

        distribucion_por_monto = [
            {
                "rango": item.rango,
                "cantidad": item.cantidad,
                "monto": float(item.monto) if item.monto else 0.0,
            }
            for item in distribucion_por_monto_query
        ]

        # Distribución por mora
        rangos_mora = [
            {"min": 1, "max": 30, "label": "1-30 días"},
            {"min": 31, "max": 60, "label": "31-60 días"},
            {"min": 61, "max": 90, "label": "61-90 días"},
            {"min": 91, "max": 999999, "label": "Más de 90 días"},
        ]

        distribucion_por_mora = []
        for rango in rangos_mora:
            # CORREGIDO: Prestamo no tiene dias_mora ni monto_mora, usar Cuota
            cantidad = (
                db.query(func.count(func.distinct(Prestamo.id)))
                .join(Cuota, Prestamo.id == Cuota.prestamo_id)
                .filter(
                    Prestamo.estado == EstadoPrestamo.EN_MORA,
                    Cuota.dias_mora >= rango["min"],
                    Cuota.dias_mora <= rango["max"],
                )
                .scalar()
            ) or 0

            monto_mora = (
                db.query(func.sum(Cuota.monto_mora))
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .filter(
                    Prestamo.estado == EstadoPrestamo.EN_MORA,
                    Cuota.dias_mora >= rango["min"],
                    Cuota.dias_mora <= rango["max"],
                )
                .scalar()
            ) or Decimal("0")

            distribucion_por_mora.append(
                {
                    "rango": rango["label"],
                    "cantidad": cantidad,
                    "monto_total": monto_mora,
                }
            )

        resultado = ReporteCartera(
            fecha_corte=fecha_corte,
            cartera_total=cartera_total,
            capital_pendiente=capital_pendiente,
            intereses_pendientes=intereses_pendientes,
            mora_total=mora_total,
            cantidad_prestamos_activos=cantidad_prestamos_activos,
            cantidad_prestamos_mora=cantidad_prestamos_mora,
            distribucion_por_monto=distribucion_por_monto,
            distribucion_por_mora=distribucion_por_mora,
        )
        logger.info("[reportes.cartera] Reporte generado correctamente")
        return resultado

    except Exception as e:
        logger.error(f"Error generando reporte de cartera: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get("/pagos", response_model=ReportePagos)
def reporte_pagos(
    fecha_inicio: date = Query(..., description="Fecha de inicio"),
    fecha_fin: date = Query(..., description="Fecha de fin"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera reporte de pagos en un rango de fechas."""
    try:
        logger.info(f"[reportes.pagos] Generando reporte pagos desde {fecha_inicio} hasta {fecha_fin}")
        # Total de pagos: usar monto_pagado
        total_pagos = db.query(func.sum(Pago.monto_pagado)).filter(
            Pago.fecha_pago >= fecha_inicio,
            Pago.fecha_pago <= fecha_fin,
        ).scalar() or Decimal("0")

        logger.info(f"[reportes.pagos] Total pagos: {total_pagos}")

        cantidad_pagos = (
            db.query(Pago)
            .filter(
                Pago.fecha_pago >= fecha_inicio,
                Pago.fecha_pago <= fecha_fin,
            )
            .count()
        )

        # Pagos por método: usar monto_pagado y agrupar por institucion_bancaria
        pagos_por_metodo = (
            db.query(
                func.coalesce(Pago.institucion_bancaria, "Sin especificar").label("metodo"),
                func.count(Pago.id).label("cantidad"),
                func.sum(Pago.monto_pagado).label("monto"),
            )
            .filter(
                Pago.fecha_pago >= fecha_inicio,
                Pago.fecha_pago <= fecha_fin,
            )
            .group_by("metodo")
            .all()
        )

        logger.info(f"[reportes.pagos] Pagos por método: {len(pagos_por_metodo)} métodos")

        # Pagos por día: usar monto_pagado
        pagos_por_dia = (
            db.query(
                func.date(Pago.fecha_pago).label("fecha"),
                func.count(Pago.id).label("cantidad"),
                func.sum(Pago.monto_pagado).label("monto"),
            )
            .filter(
                Pago.fecha_pago >= fecha_inicio,
                Pago.fecha_pago <= fecha_fin,
            )
            .group_by(func.date(Pago.fecha_pago))
            .all()
        )

        logger.info(f"[reportes.pagos] Pagos por día: {len(pagos_por_dia)} días")

        resultado = ReportePagos(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            total_pagos=total_pagos,
            cantidad_pagos=cantidad_pagos,
            pagos_por_metodo=[{"metodo": item[0], "cantidad": item[1], "monto": item[2]} for item in pagos_por_metodo],
            pagos_por_dia=[{"fecha": item[0], "cantidad": item[1], "monto": item[2]} for item in pagos_por_dia],
        )
        logger.info("[reportes.pagos] Reporte generado correctamente")
        return resultado

    except Exception as e:
        logger.error(f"Error generando reporte de pagos: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


def _obtener_distribucion_por_monto(db: Session) -> list:
    """Obtiene distribución de préstamos por rango de monto"""
    distribucion_por_monto_query = (
        db.query(
            case(
                (Prestamo.total_financiamiento <= 1000, "Hasta $1,000"),
                (Prestamo.total_financiamiento <= 5000, "$1,001 - $5,000"),
                (Prestamo.total_financiamiento <= 10000, "$5,001 - $10,000"),
                else_="Más de $10,000",
            ).label("rango"),
            func.count(Prestamo.id).label("cantidad"),
            func.sum(Prestamo.total_financiamiento).label("monto"),
        )
        .filter(Prestamo.estado == "APROBADO")
        .group_by("rango")
        .all()
    )

    return [
        {
            "rango": item.rango,
            "cantidad": item.cantidad,
            "monto": float(item.monto) if item.monto else 0.0,
        }
        for item in distribucion_por_monto_query
    ]


def _obtener_distribucion_por_mora(db: Session) -> list:
    """Obtiene distribución de préstamos por rango de días de mora"""
    rangos_mora = [
        {"min": 1, "max": 30, "label": "1-30 días"},
        {"min": 31, "max": 60, "label": "31-60 días"},
        {"min": 61, "max": 90, "label": "61-90 días"},
        {"min": 91, "max": 999999, "label": "Más de 90 días"},
    ]

    distribucion_por_mora = []
    for rango in rangos_mora:
        cantidad = (
            db.query(func.count(func.distinct(Prestamo.id)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Cuota.monto_mora > Decimal("0.00"),
                Cuota.dias_mora >= rango["min"],
                Cuota.dias_mora <= rango["max"],
            )
            .scalar()
        ) or 0

        monto_mora = (
            db.query(func.sum(Cuota.monto_mora))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Cuota.monto_mora > Decimal("0.00"),
                Cuota.dias_mora >= rango["min"],
                Cuota.dias_mora <= rango["max"],
            )
            .scalar()
        ) or Decimal("0")

        distribucion_por_mora.append(
            {
                "rango": rango["label"],
                "cantidad": cantidad,
                "monto_total": float(monto_mora),
            }
        )

    return distribucion_por_mora


def _obtener_estilos_excel():
    """Obtiene estilos reutilizables para Excel"""
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    return {
        "header_fill": PatternFill(start_color="366092", end_color="366092", fill_type="solid"),
        "header_font": Font(bold=True, color="FFFFFF", size=14),
        "title_font": Font(bold=True, size=16),
        "label_font": Font(bold=True),
        "border": Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        ),
    }


def _crear_hoja_resumen_excel(ws, reporte, cantidad_prestamos_activos, cantidad_prestamos_mora, estilos):
    """Crea la hoja de resumen ejecutivo en Excel"""
    from openpyxl.styles import Alignment, Font

    ws.title = "Resumen Ejecutivo"

    ws.merge_cells("A1:B1")
    ws["A1"] = "REPORTE DE CARTERA"
    ws["A1"].font = estilos["title_font"]
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    ws["A2"] = f"Fecha de Corte: {reporte.fecha_corte}"
    ws["A2"].font = Font(size=12)
    ws["A3"] = f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    ws["A3"].font = Font(size=10, italic=True)

    row = 5
    datos_resumen = [
        ("Cartera Total:", reporte.cartera_total),
        ("Capital Pendiente:", reporte.capital_pendiente),
        ("Intereses Pendientes:", reporte.intereses_pendientes),
        ("Mora Total:", reporte.mora_total),
        ("Préstamos Activos:", cantidad_prestamos_activos),
        ("Préstamos en Mora:", cantidad_prestamos_mora),
    ]

    for label, value in datos_resumen:
        ws[f"A{row}"] = label
        ws[f"A{row}"].font = estilos["label_font"]
        if isinstance(value, Decimal):
            ws[f"B{row}"] = float(value)
            ws[f"B{row}"].number_format = '"$"#,##0.00'
        else:
            ws[f"B{row}"] = value
        ws[f"B{row}"].font = Font(bold=True)
        row += 1

    ws.column_dimensions["A"].width = 25
    ws.column_dimensions["B"].width = 20


def _crear_hoja_distribucion_monto_excel(ws, distribucion_por_monto, estilos):
    """Crea la hoja de distribución por monto en Excel"""
    from openpyxl.styles import Alignment, Font

    ws.title = "Distribución por Monto"

    headers = ["Rango de Monto", "Cantidad Préstamos", "Monto Total"]
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = estilos["header_font"]
        cell.fill = estilos["header_fill"]
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = estilos["border"]

    for row_idx, item in enumerate(distribucion_por_monto, 2):
        ws.cell(row=row_idx, column=1, value=item["rango"]).border = estilos["border"]
        ws.cell(row=row_idx, column=2, value=item["cantidad"]).border = estilos["border"]
        cell_monto = ws.cell(row=row_idx, column=3, value=float(item["monto"]))
        cell_monto.number_format = '"$"#,##0.00'
        cell_monto.border = estilos["border"]

    total_row = len(distribucion_por_monto) + 3
    ws.cell(row=total_row, column=1, value="TOTAL:").font = Font(bold=True)
    ws.cell(row=total_row, column=2, value=sum(item["cantidad"] for item in distribucion_por_monto)).font = Font(bold=True)
    total_cell = ws.cell(row=total_row, column=3, value=sum(item["monto"] for item in distribucion_por_monto))
    total_cell.number_format = '"$"#,##0.00'
    total_cell.font = Font(bold=True)

    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 20


def _crear_hoja_distribucion_mora_excel(ws, distribucion_por_mora, estilos):
    """Crea la hoja de distribución por mora en Excel"""
    from openpyxl.styles import Alignment, Font

    ws.title = "Distribución por Mora"

    headers_mora = ["Rango de Días", "Cantidad Préstamos", "Monto Total Mora"]
    for col_idx, header in enumerate(headers_mora, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = estilos["header_font"]
        cell.fill = estilos["header_fill"]
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = estilos["border"]

    for row_idx, item in enumerate(distribucion_por_mora, 2):
        ws.cell(row=row_idx, column=1, value=item["rango"]).border = estilos["border"]
        ws.cell(row=row_idx, column=2, value=item["cantidad"]).border = estilos["border"]
        cell_mora = ws.cell(row=row_idx, column=3, value=float(item["monto_total"]))
        cell_mora.number_format = '"$"#,##0.00'
        cell_mora.border = estilos["border"]

    total_row_mora = len(distribucion_por_mora) + 3
    ws.cell(row=total_row_mora, column=1, value="TOTAL:").font = Font(bold=True)
    ws.cell(row=total_row_mora, column=2, value=sum(item["cantidad"] for item in distribucion_por_mora)).font = Font(bold=True)
    total_cell_mora = ws.cell(row=total_row_mora, column=3, value=float(sum(item["monto_total"] for item in distribucion_por_mora)))
    total_cell_mora.number_format = '"$"#,##0.00'
    total_cell_mora.font = Font(bold=True)

    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 20


def _crear_hoja_prestamos_detallados_excel(ws, db: Session, estilos):
    """Crea la hoja de préstamos detallados en Excel"""
    from openpyxl.styles import Alignment, Font

    ws.title = "Préstamos Detallados"

    prestamos_detalle = (
        db.query(
            Prestamo.id,
            Prestamo.cedula,
            Prestamo.nombres,
            Prestamo.total_financiamiento,
            Prestamo.estado,
            Prestamo.modalidad_pago,
            Prestamo.numero_cuotas,
            Prestamo.usuario_proponente.label("analista"),
            func.sum(
                func.coalesce(Cuota.capital_pendiente, Decimal("0.00"))
                + func.coalesce(Cuota.interes_pendiente, Decimal("0.00"))
                + func.coalesce(Cuota.monto_mora, Decimal("0.00"))
            ).label("saldo_pendiente"),
            func.count(Cuota.id).label("cuotas_pendientes"),
        )
        .join(Cuota, Cuota.prestamo_id == Prestamo.id, isouter=True)
        .filter(Prestamo.estado == "APROBADO")
        .group_by(Prestamo.id)
        .order_by(Prestamo.id)
        .all()
    )

    headers_detalle = [
        "ID Préstamo",
        "Cédula",
        "Cliente",
        "Total Financiamiento",
        "Saldo Pendiente",
        "Cuotas Pendientes",
        "Modalidad",
        "Analista",
        "Estado",
    ]
    for col_idx, header in enumerate(headers_detalle, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = estilos["header_font"]
        cell.fill = estilos["header_fill"]
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = estilos["border"]

    for row_idx, prestamo in enumerate(prestamos_detalle, 2):
        ws.cell(row=row_idx, column=1, value=prestamo.id).border = estilos["border"]
        ws.cell(row=row_idx, column=2, value=prestamo.cedula).border = estilos["border"]
        ws.cell(row=row_idx, column=3, value=prestamo.nombres or "").border = estilos["border"]
        cell_total = ws.cell(row=row_idx, column=4, value=float(prestamo.total_financiamiento))
        cell_total.number_format = '"$"#,##0.00'
        cell_total.border = estilos["border"]
        cell_saldo = ws.cell(row=row_idx, column=5, value=float(prestamo.saldo_pendiente or Decimal("0")))
        cell_saldo.number_format = '"$"#,##0.00'
        cell_saldo.border = estilos["border"]
        ws.cell(row=row_idx, column=6, value=prestamo.cuotas_pendientes or 0).border = estilos["border"]
        ws.cell(row=row_idx, column=7, value=prestamo.modalidad_pago or "").border = estilos["border"]
        ws.cell(row=row_idx, column=8, value=prestamo.analista or "").border = estilos["border"]
        ws.cell(row=row_idx, column=9, value=prestamo.estado or "").border = estilos["border"]

    column_widths = [12, 15, 30, 18, 18, 15, 15, 25, 12]
    for idx, width in enumerate(column_widths, 1):
        ws.column_dimensions[chr(64 + idx)].width = width


def _generar_excel_completo(reporte, db: Session, cantidad_prestamos_activos, cantidad_prestamos_mora):
    """Genera el archivo Excel completo con todas las hojas"""
    from openpyxl import Workbook

    wb = Workbook()
    estilos = _obtener_estilos_excel()

    _crear_hoja_resumen_excel(wb.active, reporte, cantidad_prestamos_activos, cantidad_prestamos_mora, estilos)
    _crear_hoja_distribucion_monto_excel(wb.create_sheet("Distribución por Monto"), _obtener_distribucion_por_monto(db), estilos)
    _crear_hoja_distribucion_mora_excel(wb.create_sheet("Distribución por Mora"), _obtener_distribucion_por_mora(db), estilos)
    _crear_hoja_prestamos_detallados_excel(wb.create_sheet("Préstamos Detallados"), db, estilos)

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def _generar_pdf_completo(reporte):
    """Genera el archivo PDF completo"""
    output = BytesIO()
    c = canvas.Canvas(output, pagesize=A4)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "REPORTE DE CARTERA")

    c.setFont("Helvetica", 12)
    c.drawString(100, 720, f"Fecha de Corte: {reporte.fecha_corte}")

    y = 680
    c.drawString(100, y, f"Cartera Total: ${reporte.cartera_total:,.2f}")
    y -= 20
    c.drawString(100, y, f"Capital Pendiente: ${reporte.capital_pendiente:,.2f}")
    y -= 20
    c.drawString(100, y, f"Intereses Pendientes: ${reporte.intereses_pendientes:,.2f}")
    y -= 20
    c.drawString(100, y, f"Mora Total: ${reporte.mora_total:,.2f}")

    c.save()
    output.seek(0)
    return output


def _registrar_auditoria_exportacion(db: Session, current_user: User, formato: str, fecha_corte: date):
    """Registra la auditoría de la exportación"""
    try:
        audit = Auditoria(
            usuario_id=current_user.id,
            accion="EXPORT",
            entidad="REPORTES",
            entidad_id=None,
            detalles=f"Exportó cartera en {formato.upper()} (fecha_corte={fecha_corte})",
            exito=True,
        )
        db.add(audit)
        db.commit()
    except Exception as e:
        logger.warning(f"No se pudo registrar auditoría de exportación ({formato}): {e}")


@router.get("/exportar/cartera")
def exportar_reporte_cartera(
    formato: str = Query("excel", description="Formato: excel o pdf"),
    fecha_corte: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exporta reporte de cartera en Excel o PDF."""
    try:
        logger.info(f"[reportes.exportar] Exportando reporte cartera en formato {formato}")
        reporte = reporte_cartera(fecha_corte, db, current_user)

        cantidad_prestamos_activos = db.query(Prestamo).filter(Prestamo.estado == "APROBADO").count()
        cantidad_prestamos_mora = (
            db.query(func.count(func.distinct(Prestamo.id)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(Prestamo.estado == "APROBADO", Cuota.monto_mora > Decimal("0.00"))
            .scalar()
        ) or 0

        if formato.lower() == "excel":
            output = _generar_excel_completo(reporte, db, cantidad_prestamos_activos, cantidad_prestamos_mora)
            response = StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename=reporte_cartera_{reporte.fecha_corte}.xlsx"},
            )
            logger.info("[reportes.exportar] Excel generado correctamente")
            _registrar_auditoria_exportacion(db, current_user, "excel", reporte.fecha_corte)
            return response

        elif formato.lower() == "pdf":
            output = _generar_pdf_completo(reporte)
            response = StreamingResponse(
                output,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=reporte_cartera_{reporte.fecha_corte}.pdf"},
            )
            logger.info("[reportes.exportar] PDF generado correctamente")
            _registrar_auditoria_exportacion(db, current_user, "pdf", reporte.fecha_corte)
            return response

        else:
            raise HTTPException(status_code=400, detail="Formato no soportado. Use 'excel' o 'pdf'")

    except Exception as e:
        logger.error(f"Error exportando reporte: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

        if formato.lower() == "excel":
            # Crear archivo Excel con datos reales detallados
            from openpyxl import Workbook
            from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

            wb = Workbook()

            # ============================================
            # HOJA 1: RESUMEN EJECUTIVO
            # ============================================
            ws_resumen = wb.active
            ws_resumen.title = "Resumen Ejecutivo"

            # Estilos
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF", size=14)
            title_font = Font(bold=True, size=16)
            label_font = Font(bold=True)
            border = Border(
                left=Side(style="thin"),
                right=Side(style="thin"),
                top=Side(style="thin"),
                bottom=Side(style="thin"),
            )

            # Encabezado
            ws_resumen.merge_cells("A1:B1")
            ws_resumen["A1"] = "REPORTE DE CARTERA"
            ws_resumen["A1"].font = title_font
            ws_resumen["A1"].alignment = Alignment(horizontal="center", vertical="center")
            ws_resumen.row_dimensions[1].height = 30

            ws_resumen["A2"] = f"Fecha de Corte: {reporte.fecha_corte}"
            ws_resumen["A2"].font = Font(size=12)
            ws_resumen["A3"] = f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            ws_resumen["A3"].font = Font(size=10, italic=True)

            # Datos principales con formato
            row = 5
            datos_resumen = [
                ("Cartera Total:", reporte.cartera_total),
                ("Capital Pendiente:", reporte.capital_pendiente),
                ("Intereses Pendientes:", reporte.intereses_pendientes),
                ("Mora Total:", reporte.mora_total),
                ("Préstamos Activos:", cantidad_prestamos_activos),
                ("Préstamos en Mora:", cantidad_prestamos_mora),
            ]

            for label, value in datos_resumen:
                ws_resumen[f"A{row}"] = label
                ws_resumen[f"A{row}"].font = label_font
                if isinstance(value, Decimal):
                    ws_resumen[f"B{row}"] = float(value)
                    ws_resumen[f"B{row}"].number_format = '"$"#,##0.00'
                else:
                    ws_resumen[f"B{row}"] = value
                ws_resumen[f"B{row}"].font = Font(bold=True)
                row += 1

            # Ajustar anchos
            ws_resumen.column_dimensions["A"].width = 25
            ws_resumen.column_dimensions["B"].width = 20

            # ============================================
            # HOJA 2: DISTRIBUCIÓN POR MONTO
            # ============================================
            ws_monto = wb.create_sheet("Distribución por Monto")

            # Encabezados
            headers = ["Rango de Monto", "Cantidad Préstamos", "Monto Total"]
            for col_idx, header in enumerate(headers, 1):
                cell = ws_monto.cell(row=1, column=col_idx, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = border

            # Datos
            for row_idx, item in enumerate(distribucion_por_monto, 2):
                ws_monto.cell(row=row_idx, column=1, value=item["rango"]).border = border
                ws_monto.cell(row=row_idx, column=2, value=item["cantidad"]).border = border
                cell_monto = ws_monto.cell(row=row_idx, column=3, value=float(item["monto"]))
                cell_monto.number_format = '"$"#,##0.00'
                cell_monto.border = border

            # Totales
            total_row = len(distribucion_por_monto) + 3
            ws_monto.cell(row=total_row, column=1, value="TOTAL:").font = Font(bold=True)
            ws_monto.cell(
                row=total_row,
                column=2,
                value=sum(item["cantidad"] for item in distribucion_por_monto),
            ).font = Font(bold=True)
            total_cell = ws_monto.cell(
                row=total_row,
                column=3,
                value=sum(item["monto"] for item in distribucion_por_monto),
            )
            total_cell.number_format = '"$"#,##0.00'
            total_cell.font = Font(bold=True)

            # Ajustar anchos
            ws_monto.column_dimensions["A"].width = 20
            ws_monto.column_dimensions["B"].width = 20
            ws_monto.column_dimensions["C"].width = 20

            # ============================================
            # HOJA 3: DISTRIBUCIÓN POR MORA
            # ============================================
            ws_mora = wb.create_sheet("Distribución por Mora")

            # Encabezados
            headers_mora = ["Rango de Días", "Cantidad Préstamos", "Monto Total Mora"]
            for col_idx, header in enumerate(headers_mora, 1):
                cell = ws_mora.cell(row=1, column=col_idx, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = border

            # Datos
            for row_idx, item in enumerate(distribucion_por_mora, 2):
                ws_mora.cell(row=row_idx, column=1, value=item["rango"]).border = border
                ws_mora.cell(row=row_idx, column=2, value=item["cantidad"]).border = border
                cell_mora = ws_mora.cell(row=row_idx, column=3, value=float(item["monto_total"]))
                cell_mora.number_format = '"$"#,##0.00'
                cell_mora.border = border

            # Totales
            total_row_mora = len(distribucion_por_mora) + 3
            ws_mora.cell(row=total_row_mora, column=1, value="TOTAL:").font = Font(bold=True)
            ws_mora.cell(
                row=total_row_mora,
                column=2,
                value=sum(item["cantidad"] for item in distribucion_por_mora),
            ).font = Font(bold=True)
            total_cell_mora = ws_mora.cell(
                row=total_row_mora,
                column=3,
                value=float(sum(item["monto_total"] for item in distribucion_por_mora)),
            )
            total_cell_mora.number_format = '"$"#,##0.00'
            total_cell_mora.font = Font(bold=True)

            # Ajustar anchos
            ws_mora.column_dimensions["A"].width = 20
            ws_mora.column_dimensions["B"].width = 20
            ws_mora.column_dimensions["C"].width = 20

            # ============================================
            # HOJA 4: PRÉSTAMOS DETALLADOS (DATOS REALES)
            # ============================================
            ws_detalle = wb.create_sheet("Préstamos Detallados")

            # Obtener préstamos reales desde BD
            prestamos_detalle = (
                db.query(
                    Prestamo.id,
                    Prestamo.cedula,
                    Prestamo.nombres,
                    Prestamo.total_financiamiento,
                    Prestamo.estado,
                    Prestamo.modalidad_pago,
                    Prestamo.numero_cuotas,
                    Prestamo.usuario_proponente.label("analista"),
                    func.sum(
                        func.coalesce(Cuota.capital_pendiente, Decimal("0.00"))
                        + func.coalesce(Cuota.interes_pendiente, Decimal("0.00"))
                        + func.coalesce(Cuota.monto_mora, Decimal("0.00"))
                    ).label("saldo_pendiente"),
                    func.count(Cuota.id).label("cuotas_pendientes"),
                )
                .join(Cuota, Cuota.prestamo_id == Prestamo.id, isouter=True)
                .filter(Prestamo.estado == "APROBADO")
                .group_by(Prestamo.id)
                .order_by(Prestamo.id)
                .all()
            )

            logger.info(f"[reportes.exportar] Obteniendo {len(prestamos_detalle)} préstamos para detalle")

            # Encabezados
            headers_detalle = [
                "ID Préstamo",
                "Cédula",
                "Cliente",
                "Total Financiamiento",
                "Saldo Pendiente",
                "Cuotas Pendientes",
                "Modalidad",
                "Analista",
                "Estado",
            ]
            for col_idx, header in enumerate(headers_detalle, 1):
                cell = ws_detalle.cell(row=1, column=col_idx, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = border

            # Datos de préstamos
            for row_idx, prestamo in enumerate(prestamos_detalle, 2):
                ws_detalle.cell(row=row_idx, column=1, value=prestamo.id).border = border
                ws_detalle.cell(row=row_idx, column=2, value=prestamo.cedula).border = border
                ws_detalle.cell(row=row_idx, column=3, value=prestamo.nombres or "").border = border
                cell_total = ws_detalle.cell(row=row_idx, column=4, value=float(prestamo.total_financiamiento))
                cell_total.number_format = '"$"#,##0.00'
                cell_total.border = border
                cell_saldo = ws_detalle.cell(
                    row=row_idx,
                    column=5,
                    value=float(prestamo.saldo_pendiente or Decimal("0")),
                )
                cell_saldo.number_format = '"$"#,##0.00'
                cell_saldo.border = border
                ws_detalle.cell(row=row_idx, column=6, value=prestamo.cuotas_pendientes or 0).border = border
                ws_detalle.cell(row=row_idx, column=7, value=prestamo.modalidad_pago or "").border = border
                ws_detalle.cell(row=row_idx, column=8, value=prestamo.analista or "").border = border
                ws_detalle.cell(row=row_idx, column=9, value=prestamo.estado or "").border = border

            # Ajustar anchos
            column_widths = [12, 15, 30, 18, 18, 15, 15, 25, 12]
            for idx, width in enumerate(column_widths, 1):
                ws_detalle.column_dimensions[chr(64 + idx)].width = width

            # Guardar en memoria
            output = BytesIO()
            wb.save(output)
            output.seek(0)

            response = StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename=reporte_cartera_{reporte.fecha_corte}.xlsx"},
            )
            logger.info("[reportes.exportar] Excel generado correctamente")
            # Auditoría de exportación
            try:
                audit = Auditoria(
                    usuario_id=current_user.id,
                    accion="EXPORT",
                    entidad="REPORTES",
                    entidad_id=None,
                    detalles=f"Exportó cartera en Excel (fecha_corte={reporte.fecha_corte})",
                    exito=True,
                )
                db.add(audit)
                db.commit()
            except Exception as e:
                logger.warning(f"No se pudo registrar auditoría de exportación (Excel): {e}")
            return response

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
            c.drawString(100, y, f"Capital Pendiente: ${reporte.capital_pendiente:,.2f}")
            y -= 20
            c.drawString(100, y, f"Intereses Pendientes: ${reporte.intereses_pendientes:,.2f}")
            y -= 20
            c.drawString(100, y, f"Mora Total: ${reporte.mora_total:,.2f}")

            c.save()
            output.seek(0)

            response = StreamingResponse(
                output,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=reporte_cartera_{reporte.fecha_corte}.pdf"},
            )
            logger.info("[reportes.exportar] PDF generado correctamente")
            # Auditoría de exportación
            try:
                audit = Auditoria(
                    usuario_id=current_user.id,
                    accion="EXPORT",
                    entidad="REPORTES",
                    entidad_id=None,
                    detalles=f"Exportó cartera en PDF (fecha_corte={reporte.fecha_corte})",
                    exito=True,
                )
                db.add(audit)
                db.commit()
            except Exception as e:
                logger.warning(f"No se pudo registrar auditoría de exportación (PDF): {e}")
            return response

        else:
            raise HTTPException(status_code=400, detail="Formato no soportado. Use 'excel' o 'pdf'")

    except Exception as e:
        logger.error(f"Error exportando reporte: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


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

        # Cartera activa: calcular desde cuotas pendientes
        cartera_activa = (
            db.query(
                func.sum(
                    func.coalesce(Cuota.capital_pendiente, Decimal("0.00"))
                    + func.coalesce(Cuota.interes_pendiente, Decimal("0.00"))
                    + func.coalesce(Cuota.monto_mora, Decimal("0.00"))
                )
            )
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Cuota.estado != "PAGADO",
            )
            .scalar()
        ) or Decimal("0")

        logger.info(f"[reportes.resumen] Cartera activa: {cartera_activa}")

        # Mora: préstamos con cuotas en mora
        prestamos_mora = (
            db.query(func.count(func.distinct(Prestamo.id)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Cuota.monto_mora > Decimal("0.00"),
            )
            .scalar()
        ) or 0

        logger.info(f"[reportes.resumen] Préstamos en mora: {prestamos_mora}")

        # Pagos del mes: usar monto_pagado
        fecha_inicio_mes = date.today().replace(day=1)
        pagos_mes = db.query(func.sum(Pago.monto_pagado)).filter(Pago.fecha_pago >= fecha_inicio_mes).scalar() or Decimal("0")

        logger.info(f"[reportes.resumen] Pagos del mes: {pagos_mes}")

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
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


# ============================================
# REPORTE PDF: Pendientes por Cliente
# ============================================
@router.get("/cliente/{cedula}/pendientes.pdf")
def generar_pdf_pendientes_cliente(
    cedula: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Genera PDF con préstamos pendientes, cuotas, modelos y fechas vencidas para un cliente.
    Contiene: Préstamos, Cuotas, Modelo, Fechas Vencidas (Amortización completa)
    """
    try:
        hoy = date.today()

        # Obtener cliente
        cliente = db.query(Cliente).filter(Cliente.cedula == cedula).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        # Obtener todos los préstamos del cliente
        prestamos = db.query(Prestamo).filter(Prestamo.cedula == cedula).all()
        if not prestamos:
            raise HTTPException(status_code=404, detail="Cliente no tiene préstamos registrados")

        # Preparar datos para el PDF
        datos_prestamos = []

        for prestamo in prestamos:
            # Obtener cuotas del préstamo
            cuotas = db.query(Cuota).filter(Cuota.prestamo_id == prestamo.id).order_by(Cuota.numero_cuota).all()

            # Cuotas pendientes/vencidas
            cuotas_pendientes = [
                {
                    "numero": c.numero_cuota,
                    "fecha_vencimiento": (c.fecha_vencimiento.strftime("%d/%m/%Y") if c.fecha_vencimiento else "N/A"),
                    "monto_cuota": float(c.monto_cuota),
                    "total_pagado": float(c.total_pagado or Decimal("0.00")),
                    "capital_pendiente": float(c.capital_pendiente or Decimal("0.00")),
                    "interes_pendiente": float(c.interes_pendiente or Decimal("0.00")),
                    "monto_mora": float(c.monto_mora or Decimal("0.00")),
                    "estado": c.estado,
                    "vencida": (c.fecha_vencimiento < hoy if c.fecha_vencimiento else False),
                }
                for c in cuotas
                if c.estado != "PAGADO"
            ]

            # Obtener modelo de vehículo si existe
            modelo_vehiculo = "N/A"
            if hasattr(prestamo, "modelo_vehiculo_id") and prestamo.modelo_vehiculo_id:
                from app.models.modelo_vehiculo import ModeloVehiculo

                modelo = db.query(ModeloVehiculo).filter(ModeloVehiculo.id == prestamo.modelo_vehiculo_id).first()
                if modelo:
                    modelo_vehiculo = f"{modelo.marca} {modelo.modelo} {modelo.ano or ''}".strip()

            datos_prestamos.append(
                {
                    "prestamo_id": prestamo.id,
                    "total_financiamiento": float(prestamo.total_financiamiento or Decimal("0.00")),
                    "numero_cuotas": prestamo.numero_cuotas or 0,
                    "modalidad": prestamo.modalidad_pago or "N/A",
                    "estado": prestamo.estado or "N/A",
                    "modelo_vehiculo": modelo_vehiculo,
                    "cuotas_pendientes": cuotas_pendientes,
                }
            )

        # Generar PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5 * inch)
        story = []
        styles = getSampleStyleSheet()

        # Título
        title = Paragraph(
            f"<b>REPORTE DE PENDIENTES - {cliente.nombres or 'Cliente'}</b>",
            styles["Title"],
        )
        story.append(title)

        # Información del cliente
        info_cliente = Paragraph(
            f"<b>Cédula:</b> {cliente.cedula}<br/>"
            f"<b>Nombre:</b> {cliente.nombres or 'N/A'}<br/>"
            f"<b>Fecha de Generación:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            styles["Normal"],
        )
        story.append(info_cliente)
        story.append(Spacer(1, 0.3 * inch))

        # Por cada préstamo
        for datos_prestamo in datos_prestamos:
            # Encabezado del préstamo
            header_prestamo = Paragraph(
                f"<b>PRÉSTAMO ID #{datos_prestamo['prestamo_id']}</b> - "
                f"Total: ${datos_prestamo['total_financiamiento']:,.2f} - "
                f"Modelo: {datos_prestamo['modelo_vehiculo']}",
                styles["Heading2"],
            )
            story.append(header_prestamo)

            # Información del préstamo
            info_prestamo = Paragraph(
                f"Modalidad: {datos_prestamo['modalidad']} | "
                f"Cuotas Totales: {datos_prestamo['numero_cuotas']} | "
                f"Estado: {datos_prestamo['estado']}",
                styles["Normal"],
            )
            story.append(info_prestamo)
            story.append(Spacer(1, 0.2 * inch))

            # Tabla de cuotas pendientes
            if datos_prestamo["cuotas_pendientes"]:
                table_data = [
                    [
                        "Cuota",
                        "Fecha Venc.",
                        "Monto Cuota",
                        "Pagado",
                        "Capital Pend.",
                        "Interés Pend.",
                        "Mora",
                        "Estado",
                    ]
                ]

                for cuota in datos_prestamo["cuotas_pendientes"]:
                    fecha_venc = cuota["fecha_vencimiento"]
                    if cuota["vencida"]:
                        fecha_venc = f"<b><font color='red'>{fecha_venc} (VENCIDA)</font></b>"

                    table_data.append(
                        [
                            str(cuota["numero"]),
                            fecha_venc,
                            f"${cuota['monto_cuota']:,.2f}",
                            f"${cuota['total_pagado']:,.2f}",
                            f"${cuota['capital_pendiente']:,.2f}",
                            f"${cuota['interes_pendiente']:,.2f}",
                            f"${cuota['monto_mora']:,.2f}",
                            cuota["estado"],
                        ]
                    )

                # Crear tabla
                table = Table(
                    table_data,
                    colWidths=[
                        0.5 * inch,
                        1 * inch,
                        1 * inch,
                        1 * inch,
                        1 * inch,
                        1 * inch,
                        0.8 * inch,
                        1 * inch,
                    ],
                )
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#366092")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 8),
                            ("FONTSIZE", (0, 1), (-1, -1), 7),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            (
                                "ROWBACKGROUNDS",
                                (0, 1),
                                (-1, -1),
                                [colors.white, colors.lightgrey],
                            ),
                        ]
                    )
                )
                story.append(table)
            else:
                story.append(
                    Paragraph(
                        "<i>No hay cuotas pendientes para este préstamo</i>",
                        styles["Normal"],
                    )
                )

            story.append(Spacer(1, 0.3 * inch))

        # Construir PDF
        doc.build(story)
        buffer.seek(0)

        # Devolver como StreamingResponse
        filename = f"pendientes_{cedula}_{hoy.strftime('%Y%m%d')}.pdf"
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando PDF pendientes para cliente {cedula}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al generar PDF: {str(e)}")
