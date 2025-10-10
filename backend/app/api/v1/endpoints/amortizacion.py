# backend/app/api/v1/endpoints/amortizacion.py
"""
Endpoints para gestión de amortización y cuotas
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import date
from decimal import Decimal

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.prestamo import Prestamo
from app.models.amortizacion import Cuota
from app.schemas.amortizacion import (
    TablaAmortizacionRequest,
    TablaAmortizacionResponse,
    CuotaResponse,
    RecalcularMoraRequest,
    RecalcularMoraResponse,
    EstadoCuentaResponse,
    ProyeccionPagoRequest,
    ProyeccionPagoResponse
)
from app.services.amortizacion_service import AmortizacionService

router = APIRouter()


@router.post("/generar", response_model=TablaAmortizacionResponse)
def generar_tabla_amortizacion(
    request: TablaAmortizacionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Genera una tabla de amortización (simulación)
    No crea registros en BD, solo devuelve el cálculo
    """
    try:
        tabla = AmortizacionService.generar_tabla_amortizacion(request)
        return tabla
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/prestamo/{prestamo_id}/crear-cuotas", response_model=List[CuotaResponse])
def crear_cuotas_prestamo(
    prestamo_id: int,
    request: TablaAmortizacionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Crea las cuotas en BD para un préstamo específico
    """
    # Verificar que el préstamo existe
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Préstamo no encontrado"
        )
    
    # Verificar que no tenga cuotas ya creadas
    cuotas_existentes = db.query(Cuota).filter(Cuota.prestamo_id == prestamo_id).count()
    if cuotas_existentes > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El préstamo ya tiene cuotas generadas"
        )
    
    try:
        # Generar tabla
        tabla = AmortizacionService.generar_tabla_amortizacion(request)
        
        # Crear cuotas en BD
        cuotas = AmortizacionService.crear_cuotas_prestamo(db, prestamo_id, tabla)
        
        return cuotas
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/prestamo/{prestamo_id}/cuotas", response_model=List[CuotaResponse])
def obtener_cuotas_prestamo(
    prestamo_id: int,
    estado: Optional[str] = Query(None, description="Filtrar por estado: PENDIENTE, PAGADA, VENCIDA, PARCIAL"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtiene las cuotas de un préstamo
    """
    # Verificar préstamo
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Préstamo no encontrado"
        )
    
    cuotas = AmortizacionService.obtener_cuotas_prestamo(db, prestamo_id, estado)
    
    # Agregar propiedades calculadas
    for cuota in cuotas:
        cuota.esta_vencida = cuota.esta_vencida
        cuota.monto_pendiente_total = cuota.monto_pendiente_total
        cuota.porcentaje_pagado = cuota.porcentaje_pagado
    
    return cuotas


@router.get("/cuota/{cuota_id}", response_model=CuotaResponse)
def obtener_cuota(
    cuota_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtiene el detalle de una cuota específica
    """
    cuota = db.query(Cuota).filter(Cuota.id == cuota_id).first()
    if not cuota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cuota no encontrada"
        )
    
    # Agregar propiedades calculadas
    cuota.esta_vencida = cuota.esta_vencida
    cuota.monto_pendiente_total = cuota.monto_pendiente_total
    cuota.porcentaje_pagado = cuota.porcentaje_pagado
    
    return cuota


@router.post("/prestamo/{prestamo_id}/recalcular-mora", response_model=RecalcularMoraResponse)
def recalcular_mora(
    prestamo_id: int,
    request: RecalcularMoraRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Recalcula la mora de todas las cuotas vencidas de un préstamo
    """
    # Verificar préstamo
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Préstamo no encontrado"
        )
    
    # Tasa de mora por defecto (0.1% diario = 3% mensual)
    tasa_mora = request.tasa_mora_diaria or Decimal("0.1")
    fecha_calculo = request.fecha_calculo or date.today()
    
    try:
        resultado = AmortizacionService.recalcular_mora(
            db,
            prestamo_id,
            tasa_mora,
            fecha_calculo
        )
        
        # Obtener cuotas con mora
        cuotas_con_mora = db.query(Cuota).filter(
            Cuota.prestamo_id == prestamo_id,
            Cuota.monto_mora > 0
        ).all()
        
        cuotas_detalle = [
            {
                "cuota_id": c.id,
                "numero_cuota": c.numero_cuota,
                "dias_mora": c.dias_mora,
                "monto_mora": float(c.monto_mora),
                "capital_pendiente": float(c.capital_pendiente)
            }
            for c in cuotas_con_mora
        ]
        
        return RecalcularMoraResponse(
            prestamo_id=prestamo_id,
            cuotas_actualizadas=resultado["cuotas_actualizadas"],
            total_mora_anterior=resultado["total_mora_anterior"],
            total_mora_nueva=resultado["total_mora_nueva"],
            diferencia=resultado["diferencia"],
            cuotas_con_mora=cuotas_detalle,
            mensaje=f"Se recalculó la mora de {resultado['cuotas_actualizadas']} cuotas"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al recalcular mora: {str(e)}"
        )


@router.get("/prestamo/{prestamo_id}/estado-cuenta", response_model=EstadoCuentaResponse)
def obtener_estado_cuenta(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtiene el estado de cuenta completo de un préstamo
    Incluye resumen, cuotas pagadas, pendientes, vencidas y próximas
    """
    # Verificar préstamo
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Préstamo no encontrado"
        )
    
    # Obtener cuotas por estado
    cuotas_pagadas = db.query(Cuota).filter(
        Cuota.prestamo_id == prestamo_id,
        Cuota.estado == "PAGADA"
    ).order_by(Cuota.numero_cuota).all()
    
    cuotas_vencidas = db.query(Cuota).filter(
        Cuota.prestamo_id == prestamo_id,
        Cuota.estado.in_(["VENCIDA", "PARCIAL"])
    ).order_by(Cuota.numero_cuota).all()
    
    cuotas_pendientes = db.query(Cuota).filter(
        Cuota.prestamo_id == prestamo_id,
        Cuota.estado == "PENDIENTE"
    ).order_by(Cuota.numero_cuota).all()
    
    # Próximas 3 cuotas
    proximas_cuotas = db.query(Cuota).filter(
        Cuota.prestamo_id == prestamo_id,
        Cuota.estado == "PENDIENTE"
    ).order_by(Cuota.numero_cuota).limit(3).all()
    
    # Calcular resumen
    total_mora = sum(c.monto_mora for c in cuotas_vencidas)
    
    resumen = {
        "monto_total": float(prestamo.monto_total),
        "monto_financiado": float(prestamo.monto_financiado),
        "saldo_pendiente": float(prestamo.saldo_pendiente),
        "total_pagado": float(prestamo.total_pagado),
        "total_mora": float(total_mora),
        "cuotas_pagadas": len(cuotas_pagadas),
        "cuotas_vencidas": len(cuotas_vencidas),
        "cuotas_pendientes": len(cuotas_pendientes),
        "cuotas_totales": prestamo.numero_cuotas
    }
    
    # Cliente info
    cliente_info = {
        "id": prestamo.cliente.id,
        "nombre_completo": prestamo.cliente.nombre_completo,
        "dni": prestamo.cliente.dni
    }
    
    return EstadoCuentaResponse(
        prestamo_id=prestamo_id,
        codigo_prestamo=prestamo.codigo_prestamo or f"PREST-{prestamo_id}",
        cliente=cliente_info,
        resumen=resumen,
        cuotas_pagadas=cuotas_pagadas,
        cuotas_pendientes=cuotas_pendientes,
        cuotas_vencidas=cuotas_vencidas,
        proximas_cuotas=proximas_cuotas,
        historial_pagos=[]  # TODO: Implementar cuando tengamos endpoint de pagos
    )


@router.post("/prestamo/{prestamo_id}/proyeccion-pago", response_model=ProyeccionPagoResponse)
def proyectar_pago(
    prestamo_id: int,
    request: ProyeccionPagoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Proyecta cómo se aplicaría un pago sobre las cuotas pendientes
    No realiza el pago, solo muestra la simulación
    """
    # Verificar préstamo
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Préstamo no encontrado"
        )
    
    # Obtener cuotas pendientes ordenadas (primero vencidas, luego por número)
    cuotas = db.query(Cuota).filter(
        Cuota.prestamo_id == prestamo_id,
        Cuota.estado.in_(["PENDIENTE", "VENCIDA", "PARCIAL"])
    ).order_by(
        Cuota.estado.desc(),  # VENCIDA primero
        Cuota.numero_cuota
    ).all()
    
    if not cuotas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay cuotas pendientes para aplicar pago"
        )
    
    # Simular aplicación de pago
    monto_disponible = request.monto_pago
    cuotas_afectadas = []
    monto_a_mora = Decimal("0.00")
    monto_a_interes = Decimal("0.00")
    monto_a_capital = Decimal("0.00")
    
    for cuota in cuotas:
        if monto_disponible <= 0:
            break
        
        # Simular aplicación (sin guardar)
        aplicado_mora = min(monto_disponible, cuota.monto_mora)
        monto_disponible -= aplicado_mora
        monto_a_mora += aplicado_mora
        
        if monto_disponible > 0:
            aplicado_interes = min(monto_disponible, cuota.interes_pendiente)
            monto_disponible -= aplicado_interes
            monto_a_interes += aplicado_interes
        
        if monto_disponible > 0:
            aplicado_capital = min(monto_disponible, cuota.capital_pendiente)
            monto_disponible -= aplicado_capital
            monto_a_capital += aplicado_capital
        
        if aplicado_mora > 0 or aplicado_interes > 0 or aplicado_capital > 0:
            cuotas_afectadas.append(cuota)
    
    nuevo_saldo = prestamo.saldo_pendiente - monto_a_capital
    cuotas_restantes = len([c for c in cuotas if c not in cuotas_afectadas])
    
    return ProyeccionPagoResponse(
        cuotas_que_se_pagarian=cuotas_afectadas,
        monto_a_mora=monto_a_mora,
        monto_a_interes=monto_a_interes,
        monto_a_capital=monto_a_capital,
        monto_sobrante=monto_disponible,
        nuevo_saldo_pendiente=nuevo_saldo,
        cuotas_restantes=cuotas_restantes,
        mensaje=f"El pago de {request.monto_pago} afectaría {len(cuotas_afectadas)} cuota(s)"
    )
