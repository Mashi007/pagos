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


@router.get("/prestamo/{prestamo_id}/informacion-adicional")
def obtener_informacion_adicional(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener información adicional de la tabla de amortización
    - Cuotas pagadas / Total
    - % de avance
    - Próximo vencimiento
    - Días en mora
    - Total pagado hasta la fecha
    - Saldo pendiente
    """
    # Verificar préstamo
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Préstamo no encontrado"
        )
    
    # Obtener todas las cuotas
    todas_cuotas = db.query(Cuota).filter(Cuota.prestamo_id == prestamo_id).all()
    
    # Calcular estadísticas
    cuotas_pagadas = len([c for c in todas_cuotas if c.estado == "PAGADA"])
    cuotas_totales = len(todas_cuotas)
    porcentaje_avance = (cuotas_pagadas / cuotas_totales * 100) if cuotas_totales > 0 else 0
    
    # Próximo vencimiento
    proxima_cuota = db.query(Cuota).filter(
        Cuota.prestamo_id == prestamo_id,
        Cuota.estado.in_(["PENDIENTE", "VENCIDA"])
    ).order_by(Cuota.fecha_vencimiento).first()
    
    proximo_vencimiento = None
    if proxima_cuota:
        dias_hasta_vencimiento = (proxima_cuota.fecha_vencimiento - date.today()).days
        proximo_vencimiento = {
            "fecha": proxima_cuota.fecha_vencimiento,
            "numero_cuota": proxima_cuota.numero_cuota,
            "monto": float(proxima_cuota.monto_cuota),
            "dias_hasta_vencimiento": dias_hasta_vencimiento,
            "esta_vencida": proxima_cuota.esta_vencida
        }
    
    # Días en mora (máximo de todas las cuotas)
    cuotas_vencidas = [c for c in todas_cuotas if c.esta_vencida and c.estado != "PAGADA"]
    dias_mora_maximos = 0
    if cuotas_vencidas:
        dias_mora_maximos = max(c.dias_mora for c in cuotas_vencidas)
    
    # Totales financieros
    total_pagado = sum(c.total_pagado for c in todas_cuotas)
    saldo_pendiente = sum(c.monto_pendiente_total for c in todas_cuotas)
    total_mora_acumulada = sum(c.monto_mora for c in todas_cuotas)
    
    # Estados de cuotas
    estados_cuotas = {}
    for cuota in todas_cuotas:
        estado = cuota.estado
        if estado not in estados_cuotas:
            estados_cuotas[estado] = 0
        estados_cuotas[estado] += 1
    
    return {
        "prestamo_id": prestamo_id,
        "codigo_prestamo": prestamo.codigo_prestamo,
        "resumen_cuotas": {
            "cuotas_pagadas": cuotas_pagadas,
            "cuotas_totales": cuotas_totales,
            "porcentaje_avance": round(porcentaje_avance, 2),
            "cuotas_pendientes": estados_cuotas.get("PENDIENTE", 0),
            "cuotas_vencidas": estados_cuotas.get("VENCIDA", 0),
            "cuotas_parciales": estados_cuotas.get("PARCIAL", 0)
        },
        "proximo_vencimiento": proximo_vencimiento,
        "mora_info": {
            "dias_mora_maximos": dias_mora_maximos,
            "total_mora_acumulada": float(total_mora_acumulada),
            "cuotas_en_mora": len(cuotas_vencidas)
        },
        "financiero": {
            "monto_total_prestamo": float(prestamo.monto_total),
            "monto_financiado": float(prestamo.monto_financiado),
            "total_pagado_hasta_fecha": float(total_pagado),
            "saldo_pendiente": float(saldo_pendiente),
            "porcentaje_pagado": round((float(total_pagado) / float(prestamo.monto_total) * 100), 2) if prestamo.monto_total > 0 else 0
        },
        "estados_detalle": estados_cuotas
    }


@router.get("/prestamo/{prestamo_id}/tabla-visual")
def obtener_tabla_visual(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener tabla de amortización en formato visual como el diagrama
    """
    # Verificar préstamo
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Préstamo no encontrado"
        )
    
    # Obtener cuotas ordenadas
    cuotas = db.query(Cuota).filter(
        Cuota.prestamo_id == prestamo_id
    ).order_by(Cuota.numero_cuota).all()
    
    # Formatear para tabla visual
    tabla_visual = []
    for cuota in cuotas:
        # Determinar emoji y color según estado
        if cuota.estado == "PAGADA":
            emoji = "✅"
            color = "success"
        elif cuota.estado == "PARCIAL":
            emoji = "⏳"
            color = "warning"
        elif cuota.estado == "VENCIDA":
            emoji = "🔴"
            color = "danger"
        elif cuota.esta_vencida:
            emoji = "⚠️"
            color = "warning"
        else:  # PENDIENTE
            emoji = "⏳"
            color = "info"
        
        # Determinar si es adelantado
        if cuota.estado == "PAGADA" and cuota.fecha_pago and cuota.fecha_pago < cuota.fecha_vencimiento:
            emoji = "🚀"
            color = "primary"
        
        tabla_visual.append({
            "numero_cuota": cuota.numero_cuota,
            "fecha_vencimiento": cuota.fecha_vencimiento.strftime("%d/%m/%Y"),
            "monto_cuota": f"${float(cuota.monto_cuota):,.2f}",
            "estado": cuota.estado,
            "estado_visual": f"{emoji} {cuota.estado}",
            "color": color,
            "dias_mora": cuota.dias_mora if cuota.dias_mora > 0 else None,
            "monto_mora": float(cuota.monto_mora) if cuota.monto_mora > 0 else None,
            "porcentaje_pagado": float(cuota.porcentaje_pagado),
            "fecha_pago_real": cuota.fecha_pago.strftime("%d/%m/%Y") if cuota.fecha_pago else None
        })
    
    return {
        "prestamo_id": prestamo_id,
        "cliente": {
            "nombre": prestamo.cliente.nombre_completo,
            "cedula": prestamo.cliente.cedula
        },
        "tabla": tabla_visual,
        "leyenda_estados": {
            "✅ PAGADO": "Cuota completamente pagada",
            "⏳ PARCIAL": "Pago parcial registrado", 
            "⏳ PENDIENTE": "Sin pagar, no vencida",
            "🔴 VENCIDA": "Sin pagar, fecha pasada",
            "🚀 ADELANTADO": "Pagado antes de vencimiento"
        }
    }
