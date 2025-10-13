# app/api/v1/endpoints/pagos.py
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, desc, asc
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal
import io

from app.db.session import get_db
from app.models.pago import Pago
from app.models.prestamo import Prestamo, EstadoPrestamo
from app.models.cliente import Cliente
from app.models.amortizacion import Cuota
from app.models.user import User
from app.schemas.pago import (
    PagoCreate, 
    PagoResponse, 
    PagoList,
    PagoManualRequest,
    PagoManualResponse,
    PagoHistorialFilters,
    PagoUpdate,
    PagoAnularRequest,
    CuotasPendientesResponse,
    DistribucionPagoResponse
)
from app.core.security import get_current_user
from app.core.permissions import UserRole, has_permission, Permission

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


# ============================================
# BÚSQUEDA DE CLIENTE Y CUOTAS PENDIENTES
# ============================================

@router.get("/cliente/cedula/{cedula}/cuotas-pendientes", response_model=CuotasPendientesResponse)
def obtener_cuotas_pendientes_por_cedula(
    cedula: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Buscar cliente por cédula y mostrar sus cuotas pendientes
    """
    # Buscar cliente
    cliente = db.query(Cliente).filter(Cliente.cedula == cedula).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Obtener préstamos activos
    prestamos = db.query(Prestamo).filter(
        Prestamo.cliente_id == cliente.id,
        Prestamo.estado.in_(["ACTIVO", "EN_MORA"])
    ).all()
    
    prestamos_data = []
    total_cuotas_pendientes = 0
    total_monto_pendiente = Decimal("0.00")
    
    for prestamo in prestamos:
        # Obtener cuotas pendientes del préstamo
        cuotas = db.query(Cuota).filter(
            Cuota.prestamo_id == prestamo.id,
            Cuota.estado.in_(["PENDIENTE", "VENCIDA", "PARCIAL"])
        ).order_by(Cuota.numero_cuota).all()
        
        cuotas_data = []
        for cuota in cuotas:
            # Calcular mora actualizada
            if cuota.esta_vencida:
                from app.core.config import settings
                mora_calculada = cuota.calcular_mora(Decimal(str(settings.TASA_MORA_DIARIA)))
                cuota.monto_mora = mora_calculada
                cuota.dias_mora = (date.today() - cuota.fecha_vencimiento).days
            
            cuotas_data.append({
                "id": cuota.id,
                "numero_cuota": cuota.numero_cuota,
                "fecha_vencimiento": cuota.fecha_vencimiento,
                "monto_cuota": float(cuota.monto_cuota),
                "capital_pendiente": float(cuota.capital_pendiente),
                "interes_pendiente": float(cuota.interes_pendiente),
                "monto_mora": float(cuota.monto_mora),
                "total_pendiente": float(cuota.monto_pendiente_total),
                "dias_mora": cuota.dias_mora,
                "estado": cuota.estado,
                "esta_vencida": cuota.esta_vencida
            })
            
            total_monto_pendiente += cuota.monto_pendiente_total
        
        prestamos_data.append({
            "id": prestamo.id,
            "codigo": prestamo.codigo_prestamo,
            "monto_total": float(prestamo.monto_total),
            "saldo_pendiente": float(prestamo.saldo_pendiente),
            "cuotas": cuotas_data
        })
        
        total_cuotas_pendientes += len(cuotas_data)
    
    return CuotasPendientesResponse(
        cliente_id=cliente.id,
        cliente_nombre=cliente.nombre_completo,
        prestamos=prestamos_data,
        total_cuotas_pendientes=total_cuotas_pendientes,
        total_monto_pendiente=total_monto_pendiente
    )


@router.post("/manual", response_model=PagoManualResponse, status_code=201)
def registrar_pago_manual(
    pago_data: PagoManualRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Registrar pago manual con selección de cuotas y distribución automática
    """
    try:
        # 1. Buscar cliente por cédula
        cliente = db.query(Cliente).filter(Cliente.cedula == pago_data.cliente_cedula).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        # 2. Verificar que las cuotas existen y pertenecen al cliente
        cuotas = db.query(Cuota).join(Prestamo).filter(
            Cuota.id.in_(pago_data.cuotas_seleccionadas),
            Prestamo.cliente_id == cliente.id,
            Cuota.estado.in_(["PENDIENTE", "VENCIDA", "PARCIAL"])
        ).order_by(Cuota.numero_cuota).all()
        
        if len(cuotas) != len(pago_data.cuotas_seleccionadas):
            raise HTTPException(
                status_code=400, 
                detail="Algunas cuotas no existen o no están disponibles para pago"
            )
        
        # 3. Calcular mora automática si está habilitado
        if pago_data.calcular_mora_automatica:
            from app.core.config import settings
            tasa_mora = Decimal(str(settings.TASA_MORA_DIARIA))
            
            for cuota in cuotas:
                if cuota.esta_vencida:
                    mora_calculada = cuota.calcular_mora(tasa_mora)
                    cuota.monto_mora = mora_calculada
                    cuota.dias_mora = (date.today() - cuota.fecha_vencimiento).days
        
        # 4. Distribuir el pago automáticamente (Mora → Interés → Capital)
        monto_disponible = pago_data.monto_pagado
        cuotas_afectadas = []
        distribucion = {
            "aplicado_a_mora": Decimal("0.00"),
            "aplicado_a_interes": Decimal("0.00"),
            "aplicado_a_capital": Decimal("0.00"),
            "sobrante": Decimal("0.00")
        }
        
        for cuota in cuotas:
            if monto_disponible <= 0:
                break
            
            detalle_aplicacion = cuota.aplicar_pago(monto_disponible)
            
            # Actualizar distribución total
            distribucion["aplicado_a_mora"] += detalle_aplicacion["mora_aplicada"]
            distribucion["aplicado_a_interes"] += detalle_aplicacion["interes_aplicado"]
            distribucion["aplicado_a_capital"] += detalle_aplicacion["capital_aplicado"]
            
            # Actualizar monto disponible
            monto_aplicado = (detalle_aplicacion["mora_aplicada"] + 
                            detalle_aplicacion["interes_aplicado"] + 
                            detalle_aplicacion["capital_aplicado"])
            monto_disponible -= monto_aplicado
            
            cuotas_afectadas.append({
                "cuota_id": cuota.id,
                "numero_cuota": cuota.numero_cuota,
                "monto_aplicado": float(monto_aplicado),
                "detalle": {
                    "mora": float(detalle_aplicacion["mora_aplicada"]),
                    "interes": float(detalle_aplicacion["interes_aplicado"]),
                    "capital": float(detalle_aplicacion["capital_aplicado"])
                },
                "nuevo_estado": cuota.estado
            })
        
        distribucion["sobrante"] = monto_disponible
        
        # 5. Crear registro de pago
        db_pago = Pago(
            prestamo_id=cuotas[0].prestamo_id,  # Tomar el préstamo de la primera cuota
            numero_cuota=cuotas[0].numero_cuota,
            monto_cuota_programado=sum(c.monto_cuota for c in cuotas),
            monto_pagado=pago_data.monto_pagado,
            monto_capital=distribucion["aplicado_a_capital"],
            monto_interes=distribucion["aplicado_a_interes"],
            monto_mora=distribucion["aplicado_a_mora"],
            monto_total=pago_data.monto_pagado,
            fecha_pago=pago_data.fecha_pago,
            fecha_vencimiento=cuotas[0].fecha_vencimiento,
            metodo_pago=pago_data.metodo_pago,
            numero_operacion=pago_data.numero_operacion,
            comprobante=pago_data.comprobante,
            banco=pago_data.banco,
            observaciones=pago_data.observaciones,
            usuario_registro=current_user.email,
            tipo_pago="MULTIPLE" if len(cuotas) > 1 else "NORMAL"
        )
        
        # Generar código de pago
        db.add(db_pago)
        db.flush()  # Para obtener el ID
        db_pago.codigo_pago = db_pago.generar_codigo_pago()
        
        db.commit()
        db.refresh(db_pago)
        
        # 6. Actualizar estado del préstamo
        prestamo = cuotas[0].prestamo
        prestamo.total_pagado += pago_data.monto_pagado
        prestamo.saldo_pendiente -= distribucion["aplicado_a_capital"]
        
        # Verificar si el préstamo está completado
        cuotas_restantes = db.query(Cuota).filter(
            Cuota.prestamo_id == prestamo.id,
            Cuota.estado.in_(["PENDIENTE", "VENCIDA", "PARCIAL"])
        ).count()
        
        if cuotas_restantes == 0:
            prestamo.estado = "COMPLETADO"
        
        db.commit()
        
        return PagoManualResponse(
            pago_id=db_pago.id,
            cliente_id=cliente.id,
            cliente_nombre=cliente.nombre_completo,
            cuotas_afectadas=cuotas_afectadas,
            distribucion_pago=distribucion,
            resumen={
                "total_pagado": float(pago_data.monto_pagado),
                "cuotas_procesadas": len(cuotas_afectadas),
                "sobrante": float(distribucion["sobrante"])
            },
            mensaje=f"Pago de ${pago_data.monto_pagado} procesado exitosamente"
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error procesando pago: {str(e)}")


@router.post("/simular", response_model=DistribucionPagoResponse)
def simular_distribucion_pago(
    cliente_cedula: str,
    cuotas_ids: list[int],
    monto_pago: Decimal,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Simular cómo se distribuiría un pago sin aplicarlo
    """
    # Buscar cliente
    cliente = db.query(Cliente).filter(Cliente.cedula == cliente_cedula).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Obtener cuotas
    cuotas = db.query(Cuota).join(Prestamo).filter(
        Cuota.id.in_(cuotas_ids),
        Prestamo.cliente_id == cliente.id
    ).order_by(Cuota.numero_cuota).all()
    
    # Simular distribución
    monto_disponible = monto_pago
    cuotas_afectadas = []
    totales = {
        "mora": Decimal("0.00"),
        "interes": Decimal("0.00"),
        "capital": Decimal("0.00")
    }
    
    for cuota in cuotas:
        if monto_disponible <= 0:
            break
        
        # Simular aplicación (sin guardar)
        aplicado_mora = min(monto_disponible, cuota.monto_mora)
        monto_disponible -= aplicado_mora
        totales["mora"] += aplicado_mora
        
        aplicado_interes = min(monto_disponible, cuota.interes_pendiente) if monto_disponible > 0 else Decimal("0.00")
        monto_disponible -= aplicado_interes
        totales["interes"] += aplicado_interes
        
        aplicado_capital = min(monto_disponible, cuota.capital_pendiente) if monto_disponible > 0 else Decimal("0.00")
        monto_disponible -= aplicado_capital
        totales["capital"] += aplicado_capital
        
        cuotas_afectadas.append({
            "cuota_id": cuota.id,
            "numero_cuota": cuota.numero_cuota,
            "mora_aplicada": float(aplicado_mora),
            "interes_aplicado": float(aplicado_interes),
            "capital_aplicado": float(aplicado_capital),
            "quedaria_pendiente": float(cuota.monto_pendiente_total - aplicado_mora - aplicado_interes - aplicado_capital)
        })
    
    return DistribucionPagoResponse(
        monto_total=monto_pago,
        aplicado_a_mora=totales["mora"],
        aplicado_a_interes=totales["interes"],
        aplicado_a_capital=totales["capital"],
        sobrante=monto_disponible,
        cuotas_afectadas=cuotas_afectadas
    )


# ============================================
# HISTORIAL DE PAGOS CON FILTROS AVANZADOS
# ============================================

@router.get("/historial", response_model=PagoList)
def historial_pagos(
    # Paginación
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    
    # Filtros de cliente
    cliente_id: Optional[int] = Query(None, description="ID del cliente"),
    cliente_cedula: Optional[str] = Query(None, description="Cédula del cliente"),
    cliente_nombre: Optional[str] = Query(None, description="Nombre del cliente"),
    
    # Filtros de fecha
    fecha_desde: Optional[date] = Query(None, description="Fecha desde"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha hasta"),
    
    # Filtros de pago
    metodo_pago: Optional[str] = Query(None, description="Método de pago"),
    estado_conciliacion: Optional[str] = Query(None, description="Estado de conciliación"),
    monto_min: Optional[Decimal] = Query(None, ge=0, description="Monto mínimo"),
    monto_max: Optional[Decimal] = Query(None, ge=0, description="Monto máximo"),
    
    # Filtros de mora
    con_mora: Optional[bool] = Query(None, description="Solo pagos con mora"),
    
    # Ordenamiento
    order_by: Optional[str] = Query("fecha_pago", description="Campo de ordenamiento"),
    order_direction: Optional[str] = Query("desc", description="Dirección del ordenamiento"),
    
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Historial de pagos con filtros avanzados
    
    Columnas mostradas:
    - Cliente (Nombre + Cédula)
    - Cuota #
    - Fecha programada vs Fecha real
    - Monto
    - Mora aplicada
    - Documento
    - Estado
    """
    # Query base con joins
    query = db.query(Pago).join(Prestamo).join(Cliente)
    
    # Aplicar filtros
    if cliente_id:
        query = query.filter(Cliente.id == cliente_id)
    
    if cliente_cedula:
        query = query.filter(Cliente.cedula == cliente_cedula)
    
    if cliente_nombre:
        search_pattern = f"%{cliente_nombre}%"
        query = query.filter(
            or_(
                Cliente.nombres.ilike(search_pattern),
                Cliente.apellidos.ilike(search_pattern),
                func.concat(Cliente.nombres, ' ', Cliente.apellidos).ilike(search_pattern)
            )
        )
    
    if fecha_desde:
        query = query.filter(Pago.fecha_pago >= fecha_desde)
    
    if fecha_hasta:
        query = query.filter(Pago.fecha_pago <= fecha_hasta)
    
    if metodo_pago:
        query = query.filter(Pago.metodo_pago == metodo_pago)
    
    if estado_conciliacion:
        query = query.filter(Pago.estado_conciliacion == estado_conciliacion)
    
    if monto_min:
        query = query.filter(Pago.monto_pagado >= monto_min)
    
    if monto_max:
        query = query.filter(Pago.monto_pagado <= monto_max)
    
    if con_mora is not None:
        if con_mora:
            query = query.filter(Pago.monto_mora > 0)
        else:
            query = query.filter(Pago.monto_mora == 0)
    
    # Aplicar ordenamiento
    if order_by == "cliente":
        order_column = func.concat(Cliente.nombres, ' ', Cliente.apellidos)
    elif order_by == "monto_pagado":
        order_column = Pago.monto_pagado
    elif order_by == "cuota":
        order_column = Pago.numero_cuota
    else:  # fecha_pago
        order_column = Pago.fecha_pago
    
    if order_direction == "desc":
        query = query.order_by(desc(order_column))
    else:
        query = query.order_by(asc(order_column))
    
    # Paginación
    total = query.count()
    skip = (page - 1) * page_size
    pagos = query.offset(skip).limit(page_size).all()
    
    return PagoList(
        items=pagos,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/{pago_id}", response_model=PagoResponse)
def obtener_pago(
    pago_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener un pago por ID"""
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return pago


# ============================================
# MODIFICACIÓN DE PAGOS
# ============================================

@router.put("/{pago_id}", response_model=PagoResponse)
def modificar_pago(
    pago_id: int,
    pago_data: PagoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Modificar un pago existente (Solo Cobranzas/Admin)
    """
    # Verificar permisos
    user_role = UserRole(current_user.rol)
    if not has_permission(user_role, Permission.PAGO_UPDATE):
        raise HTTPException(status_code=403, detail="Sin permisos para modificar pagos")
    
    # Buscar pago
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    
    # Verificar que no esté anulado
    if pago.esta_anulado:
        raise HTTPException(status_code=400, detail="No se puede modificar un pago anulado")
    
    # Guardar datos anteriores para auditoría
    datos_anteriores = {
        "monto_pagado": float(pago.monto_pagado),
        "fecha_pago": pago.fecha_pago.isoformat(),
        "metodo_pago": pago.metodo_pago,
        "numero_operacion": pago.numero_operacion,
        "comprobante": pago.comprobante
    }
    
    # Aplicar cambios
    for field, value in pago_data.model_dump(exclude_unset=True).items():
        setattr(pago, field, value)
    
    pago.actualizado_en = func.now()
    db.commit()
    db.refresh(pago)
    
    # Registrar en auditoría
    from app.models.auditoria import Auditoria, TipoAccion
    auditoria = Auditoria.registrar(
        usuario_id=current_user.id,
        accion=TipoAccion.ACTUALIZAR.value,
        tabla="pagos",
        registro_id=pago.id,
        descripcion=f"Modificación de pago {pago.codigo_pago}",
        datos_anteriores=datos_anteriores,
        datos_nuevos=pago_data.model_dump(exclude_unset=True)
    )
    db.add(auditoria)
    db.commit()
    
    return pago


# ============================================
# ANULACIÓN DE PAGOS
# ============================================

@router.post("/{pago_id}/anular")
def anular_pago(
    pago_id: int,
    anular_data: PagoAnularRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Anular un pago (Solo Admin)
    """
    # Verificar permisos (solo ADMIN)
    if current_user.rol != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo administradores pueden anular pagos")
    
    # Buscar pago
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    
    # Verificar que no esté ya anulado
    if pago.esta_anulado:
        raise HTTPException(status_code=400, detail="El pago ya está anulado")
    
    try:
        # Guardar datos para auditoría
        datos_anteriores = {
            "estado": pago.estado,
            "monto_pagado": float(pago.monto_pagado),
            "fecha_pago": pago.fecha_pago.isoformat()
        }
        
        # Revertir cambios en amortización si se solicita
        if anular_data.revertir_amortizacion:
            # Obtener cuotas afectadas por este pago
            cuotas_afectadas = db.query(Cuota).filter(
                Cuota.prestamo_id == pago.prestamo_id,
                Cuota.numero_cuota <= pago.numero_cuota
            ).all()
            
            # Revertir aplicaciones del pago
            for cuota in cuotas_afectadas:
                # Revertir pagos aplicados (esto es una simplificación)
                # En un sistema real, necesitarías un registro más detallado
                if cuota.total_pagado >= pago.monto_capital:
                    cuota.capital_pagado -= pago.monto_capital
                    cuota.capital_pendiente += pago.monto_capital
                
                if cuota.total_pagado >= pago.monto_interes:
                    cuota.interes_pagado -= pago.monto_interes
                    cuota.interes_pendiente += pago.monto_interes
                
                if cuota.total_pagado >= pago.monto_mora:
                    cuota.mora_pagada -= pago.monto_mora
                    cuota.monto_mora += pago.monto_mora
                
                # Recalcular total pagado
                cuota.total_pagado = cuota.capital_pagado + cuota.interes_pagado + cuota.mora_pagada
                cuota.actualizar_estado()
            
            # Actualizar préstamo
            prestamo = pago.prestamo
            prestamo.total_pagado -= pago.monto_pagado
            prestamo.saldo_pendiente += pago.monto_capital
            
            if prestamo.estado == "COMPLETADO":
                prestamo.estado = "ACTIVO"
        
        # Anular el pago
        pago.anular(current_user.email, anular_data.justificacion)
        
        db.commit()
        
        # Registrar en auditoría
        from app.models.auditoria import Auditoria, TipoAccion
        auditoria = Auditoria.registrar(
            usuario_id=current_user.id,
            accion=TipoAccion.ANULAR.value,
            tabla="pagos",
            registro_id=pago.id,
            descripcion=f"Anulación de pago {pago.codigo_pago}",
            datos_anteriores=datos_anteriores,
            datos_nuevos={"justificacion": anular_data.justificacion}
        )
        db.add(auditoria)
        db.commit()
        
        return {
            "message": "Pago anulado exitosamente",
            "pago_id": pago_id,
            "codigo_pago": pago.codigo_pago,
            "monto_revertido": float(pago.monto_pagado),
            "justificacion": anular_data.justificacion
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error anulando pago: {str(e)}")


# ============================================
# EXPORTACIÓN
# ============================================

@router.get("/exportar/excel")
async def exportar_historial_excel(
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    cliente_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Exportar historial de pagos a Excel
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill
    except ImportError:
        raise HTTPException(status_code=500, detail="openpyxl no está instalado")
    
    # Query de pagos
    query = db.query(Pago).join(Prestamo).join(Cliente)
    
    if fecha_desde:
        query = query.filter(Pago.fecha_pago >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Pago.fecha_pago <= fecha_hasta)
    if cliente_id:
        query = query.filter(Cliente.id == cliente_id)
    
    pagos = query.order_by(desc(Pago.fecha_pago)).all()
    
    # Crear workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Historial de Pagos"
    
    # Encabezados
    headers = [
        "Fecha Pago", "Cliente", "Cédula", "Cuota #", "Fecha Programada",
        "Monto Pagado", "Capital", "Interés", "Mora", "Método Pago",
        "Documento", "Estado", "Estado Conciliación"
    ]
    
    ws.append(headers)
    
    # Estilo de encabezados
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    
    # Datos
    for pago in pagos:
        ws.append([
            pago.fecha_pago.strftime("%d/%m/%Y"),
            pago.prestamo.cliente.nombre_completo,
            pago.prestamo.cliente.cedula,
            pago.numero_cuota,
            pago.fecha_vencimiento.strftime("%d/%m/%Y"),
            float(pago.monto_pagado),
            float(pago.monto_capital),
            float(pago.monto_interes),
            float(pago.monto_mora),
            pago.metodo_pago,
            pago.comprobante or pago.numero_operacion or "",
            pago.estado,
            pago.estado_conciliacion
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
    
    filename = f"historial_pagos_{date.today().strftime('%Y%m%d')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============================================
# ENDPOINTS BÁSICOS (COMPATIBILIDAD)
# ============================================

@router.get("/", response_model=List[PagoResponse])
def listar_pagos(
    prestamo_id: int = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Listar pagos con filtros básicos (compatibilidad)"""
    query = db.query(Pago)
    
    if prestamo_id:
        query = query.filter(Pago.prestamo_id == prestamo_id)
    
    pagos = query.order_by(Pago.fecha_pago.desc()).offset(skip).limit(limit).all()
    return pagos


@router.post("/", response_model=PagoResponse, status_code=201)
def registrar_pago_basico(
    pago: PagoCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registrar pago básico (compatibilidad con sistema anterior)"""
    
    # Verificar que el préstamo existe
    prestamo = db.query(Prestamo).filter(Prestamo.id == pago.prestamo_id).first()
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    
    # Validar que el préstamo esté activo
    if prestamo.estado not in ["ACTIVO", "EN_MORA"]:
        raise HTTPException(status_code=400, detail="El préstamo no está activo")
    
    # Crear pago
    numero_cuota = prestamo.cuotas_pagadas + 1
    db_pago = Pago(
        **pago.model_dump(),
        numero_cuota=numero_cuota,
        usuario_registro=current_user.email
    )
    
    # Generar código
    db.add(db_pago)
    db.flush()
    db_pago.codigo_pago = db_pago.generar_codigo_pago()
    
    # Actualizar préstamo
    prestamo.saldo_pendiente -= pago.monto_pagado
    prestamo.cuotas_pagadas = numero_cuota
    prestamo.total_pagado += pago.monto_pagado
    
    db.commit()
    db.refresh(db_pago)
    
    return db_pago
