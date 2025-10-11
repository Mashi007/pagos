# backend/app/api/v1/endpoints/reportes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, date, timedelta
from typing import Optional
from decimal import Decimal
import io

from app.db.session import get_db
from app.models.prestamo import Prestamo, EstadoPrestamo
from app.models.pago import Pago
from app.models.cliente import Cliente
from app.schemas.reportes import (
    ReporteCartera,
    ReporteMorosidad,
    ReporteCobranza,
    FiltrosReporte
)

router = APIRouter()


@router.get("/cartera", response_model=ReporteCartera)
def reporte_cartera(
    fecha_corte: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Genera reporte de cartera al día de corte.
    """
    if not fecha_corte:
        fecha_corte = date.today()
    
    # Cartera total
    cartera_total = db.query(
        func.sum(Prestamo.monto_total)
    ).filter(
        Prestamo.estado.in_([EstadoPrestamo.ACTIVO, EstadoPrestamo.EN_MORA])
    ).scalar() or Decimal('0')
    
    # Capital pendiente
    capital_pendiente = db.query(
        func.sum(Prestamo.saldo_pendiente)
    ).filter(
        Prestamo.estado.in_([EstadoPrestamo.ACTIVO, EstadoPrestamo.EN_MORA])
    ).scalar() or Decimal('0')
    
    # Préstamos activos
    total_activos = db.query(Prestamo).filter(
        Prestamo.estado == EstadoPrestamo.ACTIVO
    ).count()
    
    # Préstamos en mora
    total_mora = db.query(Prestamo).filter(
        Prestamo.estado == EstadoPrestamo.EN_MORA
    ).count()
    
    # Tasa de morosidad
    tasa_morosidad = (total_mora / total_activos * 100) if total_activos > 0 else 0
    
    # Distribución por rango de montos
    distribucion = db.query(
        func.count(Prestamo.id).label('cantidad'),
        func.sum(Prestamo.monto_total).label('monto')
    ).filter(
        Prestamo.estado.in_([EstadoPrestamo.ACTIVO, EstadoPrestamo.EN_MORA])
    ).group_by(
        func.case(
            (Prestamo.monto_total <= 1000, 'Hasta $1,000'),
            (Prestamo.monto_total <= 5000, '$1,001 - $5,000'),
            (Prestamo.monto_total <= 10000, '$5,001 - $10,000'),
            else_='Más de $10,000'
        )
    ).all()
    
    return ReporteCartera(
        fecha_corte=fecha_corte,
        cartera_total=cartera_total,
        capital_pendiente=capital_pendiente,
        intereses_pendientes=cartera_total - capital_pendiente,
        total_prestamos_activos=total_activos,
        total_prestamos_mora=total_mora,
        tasa_morosidad=round(tasa_morosidad, 2),
        distribucion_montos=[
            {"rango": d[0], "cantidad": d[1], "monto": d[2]}
            for d in distribucion
        ]
    )


@router.get("/morosidad", response_model=ReporteMorosidad)
def reporte_morosidad(
    dias_mora_minimo: int = 1,
    db: Session = Depends(get_db)
):
    """
    Genera reporte detallado de morosidad.
    """
    hoy = date.today()
    
    # Préstamos en mora por rango de días
    rangos_mora = [
        {"nombre": "1-30 días", "min": 1, "max": 30},
        {"nombre": "31-60 días", "min": 31, "max": 60},
        {"nombre": "61-90 días", "min": 61, "max": 90},
        {"nombre": "Más de 90 días", "min": 91, "max": 999999}
    ]
    
    detalle_rangos = []
    
    for rango in rangos_mora:
        prestamos = db.query(Prestamo).filter(
            Prestamo.estado == EstadoPrestamo.EN_MORA,
            Prestamo.dias_mora >= rango["min"],
            Prestamo.dias_mora <= rango["max"]
        ).all()
        
        cantidad = len(prestamos)
        monto_mora = sum(p.saldo_pendiente for p in prestamos)
        
        detalle_rangos.append({
            "rango": rango["nombre"],
            "cantidad": cantidad,
            "monto_total": monto_mora
        })
    
    # Total general
    total_mora = db.query(Prestamo).filter(
        Prestamo.estado == EstadoPrestamo.EN_MORA
    ).count()
    
    monto_total_mora = db.query(
        func.sum(Prestamo.saldo_pendiente)
    ).filter(
        Prestamo.estado == EstadoPrestamo.EN_MORA
    ).scalar() or Decimal('0')
    
    return ReporteMorosidad(
        fecha_reporte=hoy,
        total_prestamos_mora=total_mora,
        monto_total_mora=monto_total_mora,
        detalle_por_rango=detalle_rangos
    )


@router.get("/cobranza", response_model=ReporteCobranza)
def reporte_cobranza(
    fecha_inicio: date,
    fecha_fin: date,
    db: Session = Depends(get_db)
):
    """
    Genera reporte de gestión de cobranza.
    """
    # Pagos recibidos en el período
    pagos = db.query(Pago).filter(
        Pago.fecha_pago >= fecha_inicio,
        Pago.fecha_pago <= fecha_fin
    ).all()
    
    total_recaudado = sum(p.monto for p in pagos)
    cantidad_pagos = len(pagos)
    
    # Pagos por concepto
    por_concepto = db.query(
        Pago.concepto,
        func.count(Pago.id).label('cantidad'),
        func.sum(Pago.monto).label('monto')
    ).filter(
        Pago.fecha_pago >= fecha_inicio,
        Pago.fecha_pago <= fecha_fin
    ).group_by(Pago.concepto).all()
    
    # Eficiencia de cobranza
    total_esperado = db.query(
        func.sum(Prestamo.cuota)
    ).filter(
        Prestamo.estado.in_([EstadoPrestamo.ACTIVO, EstadoPrestamo.EN_MORA])
    ).scalar() or Decimal('0')
    
    eficiencia = (total_recaudado / total_esperado * 100) if total_esperado > 0 else 0
    
    return ReporteCobranza(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        total_recaudado=total_recaudado,
        cantidad_pagos=cantidad_pagos,
        promedio_pago=total_recaudado / cantidad_pagos if cantidad_pagos > 0 else Decimal('0'),
        detalle_por_concepto=[
            {"concepto": c[0], "cantidad": c[1], "monto": c[2]}
            for c in por_concepto
        ],
        eficiencia_cobranza=round(eficiencia, 2)
    )


@router.get("/exportar/excel")
async def exportar_excel(
    tipo_reporte: str,
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Exporta reportes a Excel.
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="openpyxl no está instalado. Ejecuta: pip install openpyxl"
        )
    
    wb = openpyxl.Workbook()
    ws = wb.active
    
    # Estilo de encabezados
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    
    if tipo_reporte == "cartera":
        ws.title = "Reporte de Cartera"
        ws.append(["Reporte de Cartera", "", "", ""])
        ws.append(["Fecha:", date.today().strftime("%d/%m/%Y"), "", ""])
        ws.append([])
        
        headers = ["ID", "Cliente", "Monto Total", "Saldo Pendiente", "Estado", "Días Mora"]
        ws.append(headers)
        
        # Aplicar estilo a encabezados
        for cell in ws[4]:
            cell.fill = header_fill
            cell.font = header_font
        
        prestamos = db.query(Prestamo).filter(
            Prestamo.estado.in_([EstadoPrestamo.ACTIVO, EstadoPrestamo.EN_MORA])
        ).all()
        
        for p in prestamos:
            ws.append([
                p.id,
                f"{p.cliente.nombres} {p.cliente.apellidos}",
                float(p.monto_total),
                float(p.saldo_pendiente),
                p.estado.value,
                p.dias_mora or 0
            ])
    
    elif tipo_reporte == "pagos":
        ws.title = "Reporte de Pagos"
        ws.append(["Reporte de Pagos", "", "", ""])
        ws.append(["Período:", f"{fecha_inicio} - {fecha_fin}", "", ""])
        ws.append([])
        
        headers = ["Fecha", "Préstamo ID", "Cliente", "Monto", "Concepto", "Referencia"]
        ws.append(headers)
        
        for cell in ws[4]:
            cell.fill = header_fill
            cell.font = header_font
        
        pagos = db.query(Pago).filter(
            Pago.fecha_pago >= fecha_inicio,
            Pago.fecha_pago <= fecha_fin
        ).all()
        
        for p in pagos:
            ws.append([
                p.fecha_pago.strftime("%d/%m/%Y"),
                p.prestamo_id,
                f"{p.prestamo.cliente.nombres} {p.prestamo.cliente.apellidos}",
                float(p.monto),
                p.concepto,
                p.referencia_bancaria or ""
            ])
    
    # Ajustar ancho de columnas
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Guardar en memoria
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"reporte_{tipo_reporte}_{date.today().strftime('%Y%m%d')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/clientes-top")
def clientes_top(
    limite: int = 10,
    db: Session = Depends(get_db)
):
    """
    Obtiene los top clientes por monto prestado.
    """
    resultado = db.query(
        Cliente,
        func.count(Prestamo.id).label('total_prestamos'),
        func.sum(Prestamo.monto_total).label('monto_total')
    ).join(Prestamo).group_by(Cliente.id).order_by(
        func.sum(Prestamo.monto_total).desc()
    ).limit(limite).all()
    
    return [
        {
            "cliente_id": r[0].id,
            "nombre": f"{r[0].nombres} {r[0].apellidos}",
            "total_prestamos": r[1],
            "monto_total": float(r[2])
        }
        for r in resultado
    ]
