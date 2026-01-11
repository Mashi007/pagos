from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.amortizacion import Cuota
from app.models.prestamo import Prestamo
from app.models.user import User
from app.schemas.amortizacion import (
    CuotaResponse,
    CuotaUpdate,
    EstadoCuentaResponse,
    ProyeccionPagoRequest,
    ProyeccionPagoResponse,
    RecalcularMoraRequest,
    RecalcularMoraResponse,
    TablaAmortizacionRequest,
    TablaAmortizacionResponse,
)
from app.services.amortizacion_service import AmortizacionService

router = APIRouter()


@router.post("/generar-tabla", response_model=TablaAmortizacionResponse)
def generar_tabla_amortizacion(
    request: TablaAmortizacionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Genera tabla de amortización para un préstamo
    try:
        tabla = AmortizacionService.generar_tabla_amortizacion(request)
        return tabla
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/prestamo/{prestamo_id}/cuotas", response_model=List[CuotaResponse])
def crear_cuotas_prestamo(
    prestamo_id: int,
    request_data: TablaAmortizacionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Crea las cuotas en BD para un préstamo específico
    # Verificar que el préstamo existe
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Préstamo no encontrado",
        )

    # Verificar que no tenga cuotas ya creadas
    cuotas_existentes = db.query(Cuota).filter(Cuota.prestamo_id == prestamo_id).count()
    if cuotas_existentes > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El préstamo ya tiene cuotas generadas",
        )

    try:
        # Generar tabla
        tabla = AmortizacionService.generar_tabla_amortizacion(request_data)

        # Crear cuotas en BD
        cuotas = AmortizacionService.crear_cuotas_prestamo(db, prestamo_id, tabla)
        return cuotas
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/prestamo/{prestamo_id}/cuotas", response_model=List[CuotaResponse])
def obtener_cuotas_prestamo(
    prestamo_id: int,
    estado: Optional[str] = Query(None, description="Filtrar por estado: PENDIENTE, PAGADA, VENCIDA, PARCIAL"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Obtiene las cuotas de un préstamo
    # Verificar préstamo
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Préstamo no encontrado",
        )

    cuotas = AmortizacionService.obtener_cuotas_prestamo(db, prestamo_id, estado)

    # Las propiedades calculadas (esta_vencida, monto_pendiente_total, porcentaje_pagado)
    # se calculan automáticamente por el modelo cuando se accede a ellas
    # El schema CuotaResponse las incluirá automáticamente usando from_attributes=True
    return cuotas


@router.post("/cuotas/multiples", response_model=List[CuotaResponse])
def obtener_cuotas_multiples_prestamos(
    prestamo_ids: List[int] = Body(..., description="Lista de IDs de préstamos"),
    estado: Optional[str] = Query(None, description="Filtrar por estado: PENDIENTE, PAGADA, VENCIDA, PARCIAL"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Obtiene cuotas de múltiples préstamos en una sola query.
    Optimiza el problema N+1 queries en frontend.
    """
    if not prestamo_ids:
        return []

    # Validar que no haya más de 100 préstamos (límite razonable)
    if len(prestamo_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No se pueden consultar más de 100 préstamos a la vez"
        )

    # Obtener todas las cuotas en una sola query
    query = db.query(Cuota).filter(Cuota.prestamo_id.in_(prestamo_ids))

    if estado:
        query = query.filter(Cuota.estado == estado)

    cuotas = query.order_by(Cuota.prestamo_id, Cuota.numero_cuota).all()

    # Las propiedades calculadas (esta_vencida, monto_pendiente_total, porcentaje_pagado)
    # se calculan automáticamente por el modelo cuando se accede a ellas
    # El schema CuotaResponse las incluirá automáticamente usando from_attributes=True
    return cuotas


@router.get("/cuota/{cuota_id}", response_model=CuotaResponse)
def obtener_cuota(
    cuota_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Obtiene el detalle de una cuota específica
    cuota = db.query(Cuota).filter(Cuota.id == cuota_id).first()
    if not cuota:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuota no encontrada")

    # Las propiedades calculadas (esta_vencida, monto_pendiente_total, porcentaje_pagado)
    # se calculan automáticamente por el modelo cuando se accede a ellas
    # El schema CuotaResponse las incluirá automáticamente usando from_attributes=True
    return cuota


@router.put("/cuota/{cuota_id}", response_model=CuotaResponse)
def actualizar_cuota(
    cuota_id: int,
    cuota_data: CuotaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Actualizar una cuota existente
    Solo administradores pueden actualizar cuotas
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden actualizar cuotas")

    try:
        cuota = db.query(Cuota).filter(Cuota.id == cuota_id).first()
        if not cuota:
            raise HTTPException(status_code=404, detail="Cuota no encontrada")

        # Aplicar cambios
        update_data = cuota_data.model_dump(exclude_unset=True)
        
        # Validar que haya al menos un campo para actualizar
        if not update_data:
            raise HTTPException(status_code=400, detail="No se proporcionaron campos para actualizar")
        
        # Log para debugging (solo en desarrollo)
        import os
        if os.getenv("ENVIRONMENT") == "development" or os.getenv("DEBUG") == "true":
            print(f"📝 [actualizar_cuota] Actualizando cuota {cuota_id} con campos: {list(update_data.keys())}")
        
        for field, value in update_data.items():
            if hasattr(cuota, field):
                # Permitir establecer None para campos opcionales (como fecha_pago, observaciones)
                if value is not None or field in ["fecha_pago", "observaciones"]:
                    try:
                        setattr(cuota, field, value)
                    except Exception as e:
                        print(f"⚠️ Error estableciendo campo {field}: {e}")
                        raise HTTPException(
                            status_code=400,
                            detail=f"Error al actualizar campo {field}: {str(e)}"
                        )

        # Recalcular total_pagado si se actualizaron campos de pago
        if any(field in update_data for field in ["capital_pagado", "interes_pagado"]):
            cuota.total_pagado = (
                (cuota.capital_pagado or Decimal("0"))
                + (cuota.interes_pagado or Decimal("0"))
            )
        # Si se actualiza total_pagado directamente pero no capital_pagado/interes_pagado,
        # mantener el total_pagado como está (el usuario lo estableció manualmente)

        # Recalcular campos pendientes si se actualizaron montos base o pagados
        if any(field in update_data for field in ["monto_capital", "capital_pagado"]):
            cuota.capital_pendiente = cuota.monto_capital - (cuota.capital_pagado or Decimal("0"))
        
        if any(field in update_data for field in ["monto_interes", "interes_pagado"]):
            cuota.interes_pendiente = cuota.monto_interes - (cuota.interes_pagado or Decimal("0"))
        
        # Si se actualizan directamente los pendientes, recalcular campos pagados
        if "capital_pendiente" in update_data:
            # Si se actualiza directamente, recalcular capital_pagado
            if "capital_pagado" not in update_data:
                cuota.capital_pagado = cuota.monto_capital - (cuota.capital_pendiente or Decimal("0"))
                # Recalcular total_pagado si cambió capital_pagado
                cuota.total_pagado = (
                    (cuota.capital_pagado or Decimal("0"))
                    + (cuota.interes_pagado or Decimal("0"))
                )
        
        if "interes_pendiente" in update_data:
            # Si se actualiza directamente, recalcular interes_pagado
            if "interes_pagado" not in update_data:
                cuota.interes_pagado = cuota.monto_interes - (cuota.interes_pendiente or Decimal("0"))
                # Recalcular total_pagado si cambió interes_pagado
                cuota.total_pagado = (
                    (cuota.capital_pagado or Decimal("0"))
                    + (cuota.interes_pagado or Decimal("0"))
                )

        # Actualizar estado si es necesario (solo si no se actualizó manualmente)
        if "estado" not in update_data:
            if cuota.total_pagado >= cuota.monto_cuota:
                cuota.estado = "PAGADO"
            elif cuota.total_pagado > Decimal("0"):
                cuota.estado = "PARCIAL"
            else:
                cuota.estado = "PENDIENTE"

        # Asegurar que todos los cambios se persistan en la base de datos
        try:
            db.add(cuota)  # Marcar como modificado explícitamente
            db.flush()  # Enviar cambios a la BD sin commit (para validar)
            db.commit()  # Confirmar cambios en la BD
            db.refresh(cuota)  # Refrescar para obtener valores actualizados de la BD
            
            # Log para debugging
            import os
            if os.getenv("ENVIRONMENT") == "development" or os.getenv("DEBUG") == "true":
                print(f"✅ [actualizar_cuota] Cuota {cuota_id} actualizada exitosamente en BD")
        except Exception as commit_error:
            db.rollback()
            print(f"❌ Error en commit de cuota {cuota_id}: {commit_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Error al guardar cambios en la base de datos: {str(commit_error)}"
            )

        # Las propiedades calculadas (esta_vencida, monto_pendiente_total, porcentaje_pagado)
        # se calculan automáticamente por el modelo cuando se accede a ellas
        # El schema CuotaResponse las incluirá automáticamente usando from_attributes=True
        return cuota

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        error_detail = f"Error actualizando cuota: {str(e)}"
        print(f"❌ Error en actualizar_cuota: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)


@router.delete("/cuota/{cuota_id}")
def eliminar_cuota(
    cuota_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Eliminar una cuota
    Solo administradores pueden eliminar cuotas
    ADVERTENCIA: Esto puede afectar la integridad de los datos del préstamo
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar cuotas")

    try:
        cuota = db.query(Cuota).filter(Cuota.id == cuota_id).first()
        if not cuota:
            raise HTTPException(status_code=404, detail="Cuota no encontrada")

        prestamo_id = cuota.prestamo_id

        # Verificar si la cuota tiene pagos aplicados
        if cuota.total_pagado > Decimal("0"):
            raise HTTPException(
                status_code=400, detail=f"No se puede eliminar una cuota con pagos aplicados (${cuota.total_pagado:.2f})"
            )

        db.delete(cuota)
        db.commit()

        return {"message": "Cuota eliminada exitosamente", "cuota_id": cuota_id, "prestamo_id": prestamo_id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error eliminando cuota: {str(e)}")


@router.post("/prestamo/{prestamo_id}/recalcular-mora", response_model=RecalcularMoraResponse)
def recalcular_mora(
    prestamo_id: int,
    request: RecalcularMoraRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Recalcula la mora de todas las cuotas vencidas de un préstamo
    # Verificar préstamo
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Préstamo no encontrado",
        )

    # Tasa de mora por defecto (0.1% diario = 3% mensual)
    tasa_mora = request.tasa_mora_diaria or Decimal("0.1")
    fecha_calculo = request.fecha_calculo or date.today()

    try:
        resultado = AmortizacionService.recalcular_mora(db, prestamo_id, tasa_mora, fecha_calculo)

        # Obtener cuotas con mora
        cuotas_con_mora = db.query(Cuota).filter(Cuota.prestamo_id == prestamo_id, Cuota.monto_mora > 0).all()

        cuotas_detalle = [
            {
                "cuota_id": c.id,
                "numero_cuota": c.numero_cuota,
                "monto_mora": float(c.monto_mora),
                "capital_pendiente": float(c.capital_pendiente),
            }
            for c in cuotas_con_mora
        ]

        return RecalcularMoraResponse(
            cuotas_actualizadas=resultado["cuotas_actualizadas"],
            monto_mora_total=float(resultado["monto_mora_total"]),
            cuotas_detalle=cuotas_detalle,
            mensaje=f"Se recalculó la mora de {resultado['cuotas_actualizadas']} cuotas",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al recalcular mora: {str(e)}",
        )


@router.get("/prestamo/{prestamo_id}/estado-cuenta", response_model=EstadoCuentaResponse)
def obtener_estado_cuenta(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Obtiene el estado de cuenta completo de un préstamo
    # Incluye resumen, cuotas pagadas, pendientes, vencidas y próximas
    # Verificar préstamo
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Préstamo no encontrado",
        )

    # Obtener cuotas por estado
    cuotas_pagadas = (
        db.query(Cuota).filter(Cuota.prestamo_id == prestamo_id, Cuota.estado == "PAGADA").order_by(Cuota.numero_cuota).all()
    )

    cuotas_vencidas = (
        db.query(Cuota)
        .filter(
            Cuota.prestamo_id == prestamo_id,
            Cuota.estado.in_(["VENCIDA", "PARCIAL"]),
        )
        .order_by(Cuota.numero_cuota)
        .all()
    )

    cuotas_pendientes = (
        db.query(Cuota)
        .filter(Cuota.prestamo_id == prestamo_id, Cuota.estado == "PENDIENTE")
        .order_by(Cuota.numero_cuota)
        .all()
    )

    # Próximas 3 cuotas
    proximas_cuotas = (
        db.query(Cuota)
        .filter(Cuota.prestamo_id == prestamo_id, Cuota.estado == "PENDIENTE")
        .order_by(Cuota.numero_cuota)
        .limit(3)
        .all()
    )

    # Calcular resumen
    total_mora = sum(c.monto_mora for c in cuotas_vencidas)

    resumen = {
        "cuotas_pagadas": len(cuotas_pagadas),
        "cuotas_vencidas": len(cuotas_vencidas),
        "cuotas_pendientes": len(cuotas_pendientes),
        "cuotas_totales": prestamo.numero_cuotas,
    }

    # Cliente info
    cliente_info = {
        "id": prestamo.cliente.id,
        "nombre_completo": prestamo.cliente.nombre_completo,
        "dni": prestamo.cliente.dni,
    }

    return EstadoCuentaResponse(
        prestamo_id=prestamo_id,
        cliente_info=cliente_info,
        resumen=resumen,
        cuotas_pagadas=[CuotaResponse.model_validate(c) for c in cuotas_pagadas],
        cuotas_vencidas=[CuotaResponse.model_validate(c) for c in cuotas_vencidas],
        cuotas_pendientes=[CuotaResponse.model_validate(c) for c in cuotas_pendientes],
        proximas_cuotas=[CuotaResponse.model_validate(c) for c in proximas_cuotas],
        total_mora=float(total_mora),
    )


@router.post("/prestamo/{prestamo_id}/proyectar-pago", response_model=ProyeccionPagoResponse)
def proyectar_pago(
    prestamo_id: int,
    request: ProyeccionPagoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Proyecta cómo se aplicaría un pago sobre las cuotas pendientes
    # No realiza el pago, solo muestra la simulación
    # Verificar préstamo
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Préstamo no encontrado",
        )

    # Obtener cuotas pendientes ordenadas (primero vencidas, luego por número)
    cuotas = (
        db.query(Cuota)
        .filter(
            Cuota.prestamo_id == prestamo_id,
            Cuota.estado.in_(["PENDIENTE", "VENCIDA", "PARCIAL"]),
        )
        .order_by(Cuota.estado.desc(), Cuota.numero_cuota)  # VENCIDA primero
        .all()
    )

    if not cuotas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay cuotas pendientes para aplicar pago",
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
        monto_aplicado=float(request.monto_pago),
        monto_a_mora=float(monto_a_mora),
        monto_a_interes=float(monto_a_interes),
        monto_a_capital=float(monto_a_capital),
        cuotas_afectadas=len(cuotas_afectadas),
        cuotas_restantes=cuotas_restantes,
        nuevo_saldo_pendiente=float(nuevo_saldo),
        mensaje=f"El pago afectaría {len(cuotas_afectadas)} cuota(s)",
    )


@router.get("/prestamo/{prestamo_id}/informacion-adicional")
def obtener_informacion_adicional(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Obtener información adicional de la tabla de amortización
    # - Cuotas pagadas / Total
    # - % de avance
    # - Próximo vencimiento
    # - Días en mora
    # - Total pagado hasta la fecha
    # - Saldo pendiente
    # Verificar préstamo
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Préstamo no encontrado",
        )

    # Obtener todas las cuotas
    todas_cuotas = db.query(Cuota).filter(Cuota.prestamo_id == prestamo_id).all()

    # Calcular estadísticas
    cuotas_pagadas = len([c for c in todas_cuotas if c.estado == "PAGADA"])
    cuotas_totales = len(todas_cuotas)
    porcentaje_avance = round((cuotas_pagadas / cuotas_totales * 100), 2) if cuotas_totales > 0 else 0

    # Próximo vencimiento
    proxima_cuota = (
        db.query(Cuota)
        .filter(
            Cuota.prestamo_id == prestamo_id,
            Cuota.estado.in_(["PENDIENTE", "VENCIDA"]),
        )
        .order_by(Cuota.fecha_vencimiento)
        .first()
    )

    proximo_vencimiento = None
    if proxima_cuota:
        dias_hasta_vencimiento = (proxima_cuota.fecha_vencimiento - date.today()).days
        proximo_vencimiento = {
            "fecha": proxima_cuota.fecha_vencimiento,
            "dias_hasta": dias_hasta_vencimiento,
            "esta_vencida": proxima_cuota.esta_vencida,
        }

    # Días en mora (máximo de todas las cuotas)
    cuotas_vencidas = [c for c in todas_cuotas if c.esta_vencida]
    dias_mora_maximo = max([c.dias_mora for c in cuotas_vencidas], default=0)

    # Total pagado hasta la fecha
    total_pagado = sum(c.monto_pagado for c in todas_cuotas if c.monto_pagado > 0)
    total_mora_acumulada = sum(c.monto_mora for c in cuotas_vencidas)

    return {
        "prestamo_id": prestamo_id,
        "codigo_prestamo": prestamo.codigo_prestamo,
        "resumen_cuotas": {
            "cuotas_pagadas": cuotas_pagadas,
            "cuotas_totales": cuotas_totales,
            "porcentaje_avance": porcentaje_avance,
            "total_mora_acumulada": float(total_mora_acumulada),
            "cuotas_en_mora": len(cuotas_vencidas),
        },
        "financiero": {
            "total_pagado": float(total_pagado),
            "saldo_pendiente": float(prestamo.saldo_pendiente),
            "porcentaje_pagado": (
                round((float(total_pagado) / float(prestamo.monto_total) * 100), 2) if prestamo.monto_total > 0 else 0
            ),
        },
        "proximo_vencimiento": proximo_vencimiento,
        "dias_mora_maximo": dias_mora_maximo,
    }


@router.get("/prestamo/{prestamo_id}/tabla-visual")
def obtener_tabla_visual(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Obtener tabla de amortización en formato visual como el diagrama
    # Verificar préstamo
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Préstamo no encontrado",
        )

    # Obtener cuotas ordenadas: primero NO PAGADAS (más antigua primero), luego PAGADAS
    from sqlalchemy import case

    cuotas = (
        db.query(Cuota)
        .filter(Cuota.prestamo_id == prestamo_id)
        .order_by(
            # Primero: NO PAGADAS (estado != 'PAGADO'), luego PAGADAS
            case((Cuota.estado != "PAGADO", 0), else_=1),
            # Dentro de NO PAGADAS: ordenar por fecha_vencimiento (más antigua primero)
            Cuota.fecha_vencimiento,
            # Como desempate: numero_cuota
            Cuota.numero_cuota,
        )
        .all()
    )

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
        if cuota.fecha_pago and cuota.fecha_pago < cuota.fecha_vencimiento:
            emoji = "🚀"
            color = "primary"

        tabla_visual.append(
            {
                "numero_cuota": cuota.numero_cuota,
                "fecha_vencimiento": cuota.fecha_vencimiento,
                "monto_cuota": f"${float(cuota.monto_cuota):,.2f}",
                "estado": cuota.estado,
                "estado_visual": f"{emoji} {cuota.estado}",
                "color": color,
                "dias_mora": cuota.dias_mora if cuota.dias_mora > 0 else None,
                "monto_mora": (float(cuota.monto_mora) if cuota.monto_mora > 0 else None),
                "porcentaje_pagado": float(cuota.porcentaje_pagado),
                "fecha_pago_real": cuota.fecha_pago,
            }
        )

    return {
        "prestamo_id": prestamo_id,
        "codigo_prestamo": prestamo.codigo_prestamo,
        "tabla_visual": tabla_visual,
        "total_cuotas": len(tabla_visual),
    }
