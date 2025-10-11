# app/api/v1/endpoints/pagos.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal
from app.db.session import get_db
from app.models.pago import Pago
from app.models.prestamo import Prestamo, EstadoPrestamo
from app.schemas.pago import PagoCreate, PagoResponse

router = APIRouter()


def calcular_proxima_fecha_pago(fecha_inicio, modalidad: str, cuotas_pagadas: int):
    """Calcula la próxima fecha de pago"""
    from datetime import timedelta
    
    if modalidad == "SEMANAL":
        return fecha_inicio + timedelta(weeks=cuotas_pagadas + 1)
    elif modalidad == "QUINCENAL":
        return fecha_inicio + timedelta(days=15 * (cuotas_pagadas + 1))
    else:  # MENSUAL
        return fecha_inicio + timedelta(days=30 * (cuotas_pagadas + 1))


@router.post("/", response_model=PagoResponse, status_code=201)
def registrar_pago(pago: PagoCreate, db: Session = Depends(get_db)):
    """Registrar un nuevo pago"""
    
    # Verificar que el préstamo existe
    prestamo = db.query(Prestamo).filter(Prestamo.id == pago.prestamo_id).first()
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    
    # Validar que el préstamo esté activo
    if prestamo.estado != EstadoPrestamo.ACTIVO:
        raise HTTPException(status_code=400, detail="El préstamo no está activo")
    
    # Validar que no exceda el saldo pendiente
    if pago.monto_pagado > prestamo.saldo_pendiente:
        raise HTTPException(
            status_code=400, 
            detail=f"El monto excede el saldo pendiente (${prestamo.saldo_pendiente})"
        )
    
    # ✅ CORRECCIÓN: usar model_dump() en lugar de dict()
    numero_cuota = prestamo.cuotas_pagadas + 1
    db_pago = Pago(
        **pago.model_dump(),
        numero_cuota=numero_cuota
    )
    
    # Actualizar el préstamo
    prestamo.saldo_pendiente = Decimal(str(prestamo.saldo_pendiente)) - pago.monto_pagado
    prestamo.cuotas_pagadas = numero_cuota
    
    # Calcular próxima fecha de pago
    if numero_cuota < prestamo.cuotas_totales:
        prestamo.proxima_fecha_pago = calcular_proxima_fecha_pago(
            prestamo.fecha_inicio,
            prestamo.modalidad.value,
            numero_cuota
        )
    else:
        prestamo.estado = EstadoPrestamo.FINALIZADO
        prestamo.proxima_fecha_pago = None
    
    db.add(db_pago)
    db.commit()
    db.refresh(db_pago)
    
    return db_pago


@router.get("/", response_model=List[PagoResponse])
def listar_pagos(
    prestamo_id: int = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Listar pagos con filtros"""
    query = db.query(Pago)
    
    if prestamo_id:
        query = query.filter(Pago.prestamo_id == prestamo_id)
    
    pagos = query.order_by(Pago.fecha_pago.desc()).offset(skip).limit(limit).all()
    return pagos


@router.get("/{pago_id}", response_model=PagoResponse)
def obtener_pago(pago_id: int, db: Session = Depends(get_db)):
    """Obtener un pago por ID"""
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return pago
