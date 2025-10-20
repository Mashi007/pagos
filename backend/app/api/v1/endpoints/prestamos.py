# app/api/v1/endpoints/prestamos.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from app.db.session import get_db
from app.models.prestamo import Prestamo
from app.models.cliente import Cliente
from app.schemas.prestamo import PrestamoCreate, PrestamoUpdate, PrestamoResponse

router = APIRouter()


def calcular_proxima_fecha_pago(fecha_inicio: datetime, modalidad: str, cuotas_pagadas: int) -> datetime:
    """Calcula la próxima fecha de pago según la modalidad"""
    if modalidad == "SEMANAL":
        return fecha_inicio + timedelta(weeks=cuotas_pagadas + 1)
    elif modalidad == "QUINCENAL":
        return fecha_inicio + timedelta(days=15 * (cuotas_pagadas + 1))
    else:  # MENSUAL
        return fecha_inicio + timedelta(days=30 * (cuotas_pagadas + 1))


@router.post("/", response_model=PrestamoResponse, status_code=201)
def crear_prestamo(prestamo: PrestamoCreate, db: Session = Depends(get_db)):
    """Crear un nuevo préstamo"""
    
    # Verificar que el cliente existe
    cliente = db.query(Cliente).filter(Cliente.id == prestamo.cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Calcular próxima fecha de pago
    proxima_fecha = calcular_proxima_fecha_pago(
        prestamo.fecha_inicio, 
        prestamo.modalidad.value, 
        0
    )
    
    # ✅ CORRECCIÓN: usar model_dump() en lugar de dict()
    db_prestamo = Prestamo(
        **prestamo.model_dump(),
        saldo_pendiente=prestamo.monto_total,
        cuotas_pagadas=0,
        proxima_fecha_pago=proxima_fecha
    )
    
    db.add(db_prestamo)
    db.commit()
    db.refresh(db_prestamo)
    
    return db_prestamo


@router.get("/", response_model=List[PrestamoResponse])
def listar_prestamos(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=1000),
    cliente_id: int = Query(None),
    estado: str = Query(None),
    db: Session = Depends(get_db)
):
    """Listar préstamos con filtros"""
    query = db.query(Prestamo)
    
    if cliente_id:
        query = query.filter(Prestamo.cliente_id == cliente_id)
    
    if estado:
        query = query.filter(Prestamo.estado == estado)
    
    prestamos = query.offset(skip).limit(limit).all()
    return prestamos


@router.get("/{prestamo_id}", response_model=PrestamoResponse)
def obtener_prestamo(prestamo_id: int, db: Session = Depends(get_db)):
    """Obtener un préstamo por ID"""
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    return prestamo


@router.put("/{prestamo_id}", response_model=PrestamoResponse)
def actualizar_prestamo(
    prestamo_id: int,
    prestamo_data: PrestamoUpdate,
    db: Session = Depends(get_db)
):
    """Actualizar datos de un préstamo"""
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    
    # ✅ CORRECCIÓN: usar model_dump() en lugar de dict()
    for field, value in prestamo_data.model_dump(exclude_unset=True).items():
        setattr(prestamo, field, value)
    
    db.commit()
    db.refresh(prestamo)
    return prestamo


@router.get("/stats")
def obtener_estadisticas_prestamos(db: Session = Depends(get_db)):
    """Obtener estadísticas de préstamos"""
    try:
        # Contar préstamos por estado
        total_prestamos = db.query(Prestamo).count()
        prestamos_activos = db.query(Prestamo).filter(Prestamo.estado == "ACTIVO").count()
        prestamos_pendientes = db.query(Prestamo).filter(Prestamo.estado == "PENDIENTE").count()
        prestamos_completados = db.query(Prestamo).filter(Prestamo.estado == "COMPLETADO").count()
        prestamos_en_mora = db.query(Prestamo).filter(Prestamo.estado == "EN_MORA").count()
        
        # Calcular montos
        from sqlalchemy import func
        monto_total_prestado = db.query(func.sum(Prestamo.monto_total)).scalar() or 0
        monto_total_pendiente = db.query(func.sum(Prestamo.saldo_pendiente)).scalar() or 0
        
        return {
            "total_prestamos": total_prestamos,
            "prestamos_activos": prestamos_activos,
            "prestamos_pendientes": prestamos_pendientes,
            "prestamos_completados": prestamos_completados,
            "prestamos_en_mora": prestamos_en_mora,
            "monto_total_prestado": float(monto_total_prestado),
            "monto_total_pendiente": float(monto_total_pendiente)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener estadísticas: {str(e)}")
