# backend/app/api/v1/endpoints/conciliacion.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
import csv
import io

from app.db.session import get_db
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.schemas.conciliacion import (
    ConciliacionCreate,
    ConciliacionResponse,
    MovimientoBancario,
    ResultadoConciliacion,
    EstadoConciliacion
)

router = APIRouter()


@router.post("/cargar-extracto", response_model=List[MovimientoBancario])
async def cargar_extracto_bancario(
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Carga un extracto bancario en formato CSV.
    
    Formato esperado del CSV:
    fecha,referencia,monto,descripcion
    """
    if not archivo.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Solo se aceptan archivos CSV"
        )
    
    contenido = await archivo.read()
    texto = contenido.decode('utf-8')
    
    movimientos = []
    lector = csv.DictReader(io.StringIO(texto))
    
    for fila in lector:
        try:
            movimiento = MovimientoBancario(
                fecha=datetime.strptime(fila['fecha'], '%Y-%m-%d').date(),
                referencia=fila['referencia'],
                monto=Decimal(fila['monto']),
                descripcion=fila.get('descripcion', '')
            )
            movimientos.append(movimiento)
        except (KeyError, ValueError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error en formato del archivo: {str(e)}"
            )
    
    return movimientos


@router.post("/conciliar", response_model=ResultadoConciliacion)
def conciliar_pagos(
    movimientos: List[MovimientoBancario],
    fecha_inicio: date,
    fecha_fin: date,
    db: Session = Depends(get_db)
):
    """
    Concilia movimientos bancarios con pagos registrados.
    """
    # Obtener pagos del período
    pagos = db.query(Pago).filter(
        Pago.fecha_pago >= fecha_inicio,
        Pago.fecha_pago <= fecha_fin
    ).all()
    
    conciliados = []
    sin_conciliar_banco = []
    sin_conciliar_sistema = list(pagos)
    
    # Intentar match por referencia y monto
    for mov in movimientos:
        encontrado = False
        
        for pago in sin_conciliar_sistema[:]:
            # Match por referencia
            if mov.referencia and pago.referencia_bancaria == mov.referencia:
                conciliados.append({
                    "movimiento_bancario": mov,
                    "pago": pago,
                    "tipo_match": "referencia"
                })
                sin_conciliar_sistema.remove(pago)
                encontrado = True
                break
            
            # Match por monto y fecha (±2 días)
            diferencia_dias = abs((mov.fecha - pago.fecha_pago).days)
            if mov.monto == pago.monto and diferencia_dias <= 2:
                conciliados.append({
                    "movimiento_bancario": mov,
                    "pago": pago,
                    "tipo_match": "monto_fecha"
                })
                sin_conciliar_sistema.remove(pago)
                encontrado = True
                break
        
        if not encontrado:
            sin_conciliar_banco.append(mov)
    
    return ResultadoConciliacion(
        total_movimientos=len(movimientos),
        total_pagos=len(pagos),
        conciliados=len(conciliados),
        sin_conciliar_banco=len(sin_conciliar_banco),
        sin_conciliar_sistema=len(sin_conciliar_sistema),
        detalle_conciliados=conciliados,
        detalle_sin_conciliar_banco=sin_conciliar_banco,
        detalle_sin_conciliar_sistema=sin_conciliar_sistema
    )


@router.post("/confirmar-conciliacion/{pago_id}")
def confirmar_conciliacion(
    pago_id: int,
    referencia_bancaria: str,
    db: Session = Depends(get_db)
):
    """
    Confirma manualmente la conciliación de un pago.
    """
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    
    pago.referencia_bancaria = referencia_bancaria
    pago.estado_conciliacion = EstadoConciliacion.CONCILIADO
    pago.fecha_conciliacion = datetime.now()
    
    db.commit()
    db.refresh(pago)
    
    return {"message": "Conciliación confirmada", "pago_id": pago_id}


@router.get("/pendientes", response_model=List[dict])
def obtener_pendientes_conciliacion(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Obtiene pagos pendientes de conciliar.
    """
    query = db.query(Pago).filter(
        Pago.estado_conciliacion == EstadoConciliacion.PENDIENTE
    )
    
    if fecha_inicio:
        query = query.filter(Pago.fecha_pago >= fecha_inicio)
    if fecha_fin:
        query = query.filter(Pago.fecha_pago <= fecha_fin)
    
    pagos = query.all()
    
    return [
        {
            "id": p.id,
            "prestamo_id": p.prestamo_id,
            "monto": p.monto,
            "fecha_pago": p.fecha_pago,
            "concepto": p.concepto
        }
        for p in pagos
    ]


@router.get("/reporte-conciliacion")
def reporte_conciliacion(
    mes: int,
    anio: int,
    db: Session = Depends(get_db)
):
    """
    Genera reporte mensual de conciliación.
    """
    from calendar import monthrange
    
    fecha_inicio = date(anio, mes, 1)
    ultimo_dia = monthrange(anio, mes)[1]
    fecha_fin = date(anio, mes, ultimo_dia)
    
    total_pagos = db.query(Pago).filter(
        Pago.fecha_pago >= fecha_inicio,
        Pago.fecha_pago <= fecha_fin
    ).count()
    
    conciliados = db.query(Pago).filter(
        Pago.fecha_pago >= fecha_inicio,
        Pago.fecha_pago <= fecha_fin,
        Pago.estado_conciliacion == EstadoConciliacion.CONCILIADO
    ).count()
    
    pendientes = total_pagos - conciliados
    
    return {
        "mes": mes,
        "anio": anio,
        "total_pagos": total_pagos,
        "conciliados": conciliados,
        "pendientes": pendientes,
        "porcentaje_conciliacion": round((conciliados / total_pagos * 100) if total_pagos > 0 else 0, 2)
    }
