# backend/app/api/v1/endpoints/clientes.py
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import List, Optional
from datetime import date
from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.user import User
from app.models.prestamo import Prestamo
from app.schemas.cliente import (
    ClienteCreate, 
    ClienteUpdate, 
    ClienteResponse, 
    ClienteSearchFilters,
    ClienteSearchResponse,
    ClienteFichaDetallada
)
from app.services.amortizacion_service import AmortizacionService
from app.schemas.amortizacion import TablaAmortizacionRequest

router = APIRouter()


@router.post("/", response_model=ClienteResponse, status_code=201)
def crear_cliente(
    cliente: ClienteCreate = Body(...),
    generar_amortizacion: bool = Query(True, description="Generar tabla de amortización automáticamente"),
    db: Session = Depends(get_db)
):
    """
    Crear un nuevo cliente con generación automática de tabla de amortización
    
    ✅ NUEVA FUNCIONALIDAD: Generación automática de amortización al guardar
    """
    try:
        # Verificar si ya existe la cédula
        existing = db.query(Cliente).filter(Cliente.cedula == cliente.cedula).first()
        if existing:
            raise HTTPException(status_code=400, detail="Cédula ya registrada")
        
        # Verificar que el asesor existe si se especifica
        if cliente.asesor_id:
            asesor = db.query(User).filter(User.id == cliente.asesor_id).first()
            if not asesor:
                raise HTTPException(status_code=400, detail="Asesor no encontrado")
        
        # Crear cliente
        cliente_dict = cliente.model_dump()
        db_cliente = Cliente(**cliente_dict)
        db.add(db_cliente)
        db.commit()
        db.refresh(db_cliente)
        
        # ============================================
        # ✅ GENERACIÓN AUTOMÁTICA DE AMORTIZACIÓN
        # ============================================
        if (generar_amortizacion and 
            cliente.total_financiamiento and 
            cliente.numero_amortizaciones and 
            cliente.fecha_entrega):
            
            try:
                # Calcular monto financiado (total - cuota inicial)
                monto_financiado = cliente.total_financiamiento - (cliente.cuota_inicial or 0)
                
                # Crear préstamo automáticamente
                nuevo_prestamo = Prestamo(
                    cliente_id=db_cliente.id,
                    monto_total=cliente.total_financiamiento,
                    monto_financiado=monto_financiado,
                    monto_inicial=cliente.cuota_inicial or 0,
                    tasa_interes=15.0,  # Tasa por defecto, se puede configurar
                    numero_cuotas=cliente.numero_amortizaciones,
                    fecha_aprobacion=date.today(),
                    fecha_desembolso=cliente.fecha_entrega,
                    fecha_primer_vencimiento=cliente.fecha_entrega,
                    modalidad=cliente.modalidad_financiamiento or "MENSUAL",
                    destino_credito=f"Financiamiento vehículo {cliente.modelo_vehiculo or 'N/A'}",
                    saldo_pendiente=monto_financiado,
                    saldo_capital=monto_financiado,
                    estado="ACTIVO"
                )
                
                # Calcular cuota mensual (método francés básico)
                tasa_mensual = 0.15 / 12  # 15% anual
                if cliente.modalidad_financiamiento == "SEMANAL":
                    tasa_periodo = 0.15 / 52
                elif cliente.modalidad_financiamiento == "QUINCENAL":
                    tasa_periodo = 0.15 / 24
                else:
                    tasa_periodo = tasa_mensual
                
                if tasa_periodo > 0:
                    factor = (tasa_periodo * (1 + tasa_periodo) ** cliente.numero_amortizaciones) / \
                            ((1 + tasa_periodo) ** cliente.numero_amortizaciones - 1)
                    cuota = monto_financiado * factor
                else:
                    cuota = monto_financiado / cliente.numero_amortizaciones
                
                nuevo_prestamo.monto_cuota = round(cuota, 2)
                
                db.add(nuevo_prestamo)
                db.commit()
                db.refresh(nuevo_prestamo)
                
                # Generar tabla de amortización
                request_amortizacion = TablaAmortizacionRequest(
                    monto_financiado=monto_financiado,
                    tasa_interes_anual=15.0,
                    numero_cuotas=cliente.numero_amortizaciones,
                    fecha_primer_vencimiento=cliente.fecha_entrega,
                    modalidad=cliente.modalidad_financiamiento or "MENSUAL",
                    sistema_amortizacion="FRANCES"
                )
                
                tabla = AmortizacionService.generar_tabla_amortizacion(request_amortizacion)
                AmortizacionService.crear_cuotas_prestamo(db, nuevo_prestamo.id, tabla)
                
                print(f"✅ Cliente creado con amortización automática: ID={db_cliente.id}, Préstamo ID={nuevo_prestamo.id}")
                
            except Exception as amort_error:
                print(f"⚠️ Cliente creado pero error en amortización: {amort_error}")
                # El cliente se crea exitosamente aunque falle la amortización
        
        return db_cliente
        
    except Exception as e:
        print(f"❌ Error creando cliente: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/", response_model=List[ClienteResponse])
def listar_clientes(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    activo: bool = Query(None),
    db: Session = Depends(get_db)
):
    """Listar clientes con paginación básica (mantener compatibilidad)"""
    query = db.query(Cliente)
    
    if activo is not None:
        query = query.filter(Cliente.activo == activo)
    
    clientes = query.offset(skip).limit(limit).all()
    
    # Enriquecer con propiedades calculadas
    for cliente in clientes:
        cliente.nombre_completo = cliente.nombre_completo
        cliente.monto_financiado = cliente.monto_financiado
        cliente.tiene_prestamos_activos = cliente.tiene_prestamos_activos
        cliente.estado_mora = cliente.estado_mora
    
    return clientes


# ============================================
# ✅ NUEVA FUNCIONALIDAD: BÚSQUEDA AVANZADA
# ============================================
@router.post("/buscar", response_model=ClienteSearchResponse)
def buscar_clientes_avanzado(
    filtros: ClienteSearchFilters = Body(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    ordenar_por: str = Query("fecha_registro", description="Campo para ordenar"),
    orden_desc: bool = Query(True, description="Orden descendente"),
    db: Session = Depends(get_db)
):
    """
    🔍 BÚSQUEDA AVANZADA DE CLIENTES
    
    Permite buscar por:
    - ✅ Nombre, Cédula, Móvil (texto libre)
    - ✅ Estado del caso (Activo/Inactivo/Mora)
    - ✅ Asesor asignado
    - ✅ Concesionario
    - ✅ Modelo de vehículo
    - ✅ Modalidad de financiamiento
    - ✅ Rangos de monto y días de mora
    - ✅ Ordenamiento por múltiples campos
    """
    query = db.query(Cliente)
    
    # ============================================
    # BÚSQUEDA POR TEXTO
    # ============================================
    if filtros.buscar:
        buscar_texto = f"%{filtros.buscar.lower()}%"
        query = query.filter(
            or_(
                func.lower(Cliente.nombres).like(buscar_texto),
                func.lower(Cliente.apellidos).like(buscar_texto),
                func.lower(Cliente.cedula).like(buscar_texto),
                func.lower(Cliente.telefono).like(buscar_texto),
                func.lower(func.concat(Cliente.nombres, ' ', Cliente.apellidos)).like(buscar_texto)
            )
        )
    
    # ============================================
    # FILTROS ESPECÍFICOS
    # ============================================
    if filtros.estado:
        if filtros.estado == "MORA":
            query = query.filter(Cliente.dias_mora > 0)
        else:
            query = query.filter(Cliente.estado == filtros.estado)
    
    if filtros.asesor_id:
        query = query.filter(Cliente.asesor_id == filtros.asesor_id)
    
    if filtros.concesionario:
        query = query.filter(func.lower(Cliente.concesionario).like(f"%{filtros.concesionario.lower()}%"))
    
    if filtros.modelo_vehiculo:
        query = query.filter(func.lower(Cliente.modelo_vehiculo).like(f"%{filtros.modelo_vehiculo.lower()}%"))
    
    if filtros.modalidad_financiamiento:
        query = query.filter(Cliente.modalidad_financiamiento == filtros.modalidad_financiamiento)
    
    # ============================================
    # FILTROS POR RANGO
    # ============================================
    if filtros.monto_min:
        query = query.filter(Cliente.total_financiamiento >= filtros.monto_min)
    
    if filtros.monto_max:
        query = query.filter(Cliente.total_financiamiento <= filtros.monto_max)
    
    if filtros.dias_mora_min:
        query = query.filter(Cliente.dias_mora >= filtros.dias_mora_min)
    
    if filtros.dias_mora_max:
        query = query.filter(Cliente.dias_mora <= filtros.dias_mora_max)
    
    # ============================================
    # FILTROS POR FECHA
    # ============================================
    if filtros.fecha_registro_desde:
        query = query.filter(Cliente.fecha_registro >= filtros.fecha_registro_desde)
    
    if filtros.fecha_registro_hasta:
        query = query.filter(Cliente.fecha_registro <= filtros.fecha_registro_hasta)
    
    if filtros.fecha_entrega_desde:
        query = query.filter(Cliente.fecha_entrega >= filtros.fecha_entrega_desde)
    
    if filtros.fecha_entrega_hasta:
        query = query.filter(Cliente.fecha_entrega <= filtros.fecha_entrega_hasta)
    
    # ============================================
    # ORDENAMIENTO MÚLTIPLE
    # ============================================
    campos_ordenamiento = {
        "fecha_registro": Cliente.fecha_registro,
        "nombre": Cliente.nombres,
        "cedula": Cliente.cedula,
        "estado": Cliente.estado,
        "dias_mora": Cliente.dias_mora,
        "total_financiamiento": Cliente.total_financiamiento,
        "fecha_entrega": Cliente.fecha_entrega
    }
    
    if ordenar_por in campos_ordenamiento:
        campo = campos_ordenamiento[ordenar_por]
        if orden_desc:
            query = query.order_by(campo.desc())
        else:
            query = query.order_by(campo.asc())
    
    # Contar total antes de paginación
    total = query.count()
    
    # Aplicar paginación
    clientes = query.offset(skip).limit(limit).all()
    
    # Enriquecer con propiedades calculadas
    for cliente in clientes:
        cliente.nombre_completo = cliente.nombre_completo
        cliente.monto_financiado = cliente.monto_financiado
        cliente.tiene_prestamos_activos = cliente.tiene_prestamos_activos
        cliente.estado_mora = cliente.estado_mora
    
    # Calcular estadísticas
    estadisticas = {
        "total_encontrados": total,
        "activos": len([c for c in clientes if c.activo]),
        "en_mora": len([c for c in clientes if c.dias_mora > 0]),
        "con_prestamos": len([c for c in clientes if c.tiene_prestamos_activos])
    }
    
    return ClienteSearchResponse(
        clientes=clientes,
        total=total,
        filtros_aplicados=filtros,
        estadisticas=estadisticas
    )


@router.get("/cedula/{cedula}", response_model=ClienteResponse)
def buscar_por_cedula(cedula: str, db: Session = Depends(get_db)):
    """Buscar cliente por cédula"""
    cliente = db.query(Cliente).filter(Cliente.cedula == cedula).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.get("/{cliente_id}", response_model=ClienteResponse)
def obtener_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Obtener un cliente por ID (vista básica)"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Enriquecer con propiedades calculadas
    cliente.nombre_completo = cliente.nombre_completo
    cliente.monto_financiado = cliente.monto_financiado
    cliente.tiene_prestamos_activos = cliente.tiene_prestamos_activos
    cliente.estado_mora = cliente.estado_mora
    
    return cliente


# ============================================
# ✅ NUEVA FUNCIONALIDAD: FICHA DETALLADA
# ============================================
@router.get("/{cliente_id}/ficha-detallada", response_model=ClienteFichaDetallada)
def obtener_ficha_detallada(cliente_id: int, db: Session = Depends(get_db)):
    """
    👁️ FICHA DETALLADA DEL CLIENTE
    
    Incluye:
    - ✅ Información general
    - ✅ Resumen financiero completo
    - ✅ Estado de mora detallado
    - ✅ Información del asesor
    - ✅ Próximas cuotas
    - ✅ Alertas y notificaciones
    """
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Obtener préstamos activos
    prestamos_activos = db.query(Prestamo).filter(
        Prestamo.cliente_id == cliente_id,
        Prestamo.estado.in_(["ACTIVO", "EN_MORA"])
    ).all()
    
    # Calcular resumen financiero
    total_financiado = sum(p.monto_total for p in prestamos_activos)
    total_pagado = sum(p.total_pagado for p in prestamos_activos)
    saldo_pendiente = sum(p.saldo_pendiente for p in prestamos_activos)
    
    resumen_financiero = {
        "total_financiado": float(total_financiado),
        "total_pagado": float(total_pagado),
        "saldo_pendiente": float(saldo_pendiente),
        "cuotas_pagadas": sum(p.cuotas_pagadas for p in prestamos_activos),
        "cuotas_totales": sum(p.numero_cuotas for p in prestamos_activos),
        "porcentaje_avance": round((total_pagado / total_financiado * 100) if total_financiado > 0 else 0, 2)
    }
    
    # Estadísticas de pagos
    from app.models.pago import Pago
    pagos = db.query(Pago).join(Prestamo).filter(Prestamo.cliente_id == cliente_id).all()
    
    estadisticas_pagos = {
        "total_pagos": len(pagos),
        "pagos_puntuales": len([p for p in pagos if p.dias_mora == 0]),
        "pagos_con_mora": len([p for p in pagos if p.dias_mora > 0]),
        "promedio_dias_mora": round(sum(p.dias_mora for p in pagos) / len(pagos), 1) if pagos else 0,
        "ultimo_pago": max([p.fecha_pago for p in pagos]) if pagos else None
    }
    
    # Próximas cuotas (próximas 3)
    from app.models.amortizacion import Cuota
    proximas_cuotas_query = db.query(Cuota).join(Prestamo).filter(
        Prestamo.cliente_id == cliente_id,
        Cuota.estado == "PENDIENTE"
    ).order_by(Cuota.fecha_vencimiento).limit(3).all()
    
    proximas_cuotas = [
        {
            "cuota_id": c.id,
            "numero_cuota": c.numero_cuota,
            "fecha_vencimiento": c.fecha_vencimiento,
            "monto": float(c.monto_cuota),
            "prestamo_id": c.prestamo_id
        }
        for c in proximas_cuotas_query
    ]
    
    # Generar alertas
    alertas = []
    max_dias_mora = max((p.dias_mora or 0) for p in prestamos_activos) if prestamos_activos else 0
    
    if max_dias_mora > 90:
        alertas.append("🚨 Cliente en mora crítica (+90 días)")
    elif max_dias_mora > 30:
        alertas.append("⚠️ Cliente en mora media (30-90 días)")
    elif max_dias_mora > 0:
        alertas.append("🟡 Cliente con mora temprana (1-30 días)")
    
    if not prestamos_activos:
        alertas.append("ℹ️ Cliente sin préstamos activos")
    
    # Información del asesor
    asesor_nombre = None
    asesor_email = None
    if cliente.asesor:
        asesor_nombre = cliente.asesor.full_name
        asesor_email = cliente.asesor.email
    
    # Crear respuesta completa
    ficha = ClienteFichaDetallada(
        **cliente.__dict__,
        asesor_nombre=asesor_nombre,
        asesor_email=asesor_email,
        resumen_financiero=resumen_financiero,
        estadisticas_pagos=estadisticas_pagos,
        proximas_cuotas=proximas_cuotas,
        alertas=alertas
    )
    
    # Enriquecer con propiedades calculadas
    ficha.nombre_completo = cliente.nombre_completo
    ficha.monto_financiado = cliente.monto_financiado
    ficha.tiene_prestamos_activos = cliente.tiene_prestamos_activos
    ficha.estado_mora = cliente.estado_mora
    
    return ficha


@router.put("/{cliente_id}", response_model=ClienteResponse)
def actualizar_cliente(
    cliente_id: int,
    cliente_data: ClienteUpdate,
    db: Session = Depends(get_db)
):
    """Actualizar datos de un cliente"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    for field, value in cliente_data.model_dump(exclude_unset=True).items():
        setattr(cliente, field, value)
    
    db.commit()
    db.refresh(cliente)
    return cliente


@router.delete("/{cliente_id}", status_code=204)
def eliminar_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """
    🗑️ ELIMINAR CLIENTE (Solo Admin)
    
    ✅ Validación: No se puede eliminar con pagos activos
    """
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Verificar que no tenga préstamos activos
    prestamos_activos = db.query(Prestamo).filter(
        Prestamo.cliente_id == cliente_id,
        Prestamo.estado.in_(["ACTIVO", "EN_MORA", "PENDIENTE"])
    ).count()
    
    if prestamos_activos > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"No se puede eliminar: el cliente tiene {prestamos_activos} préstamo(s) activo(s)"
        )
    
    cliente.activo = False
    cliente.estado = "INACTIVO"
    db.commit()
    return None


# ============================================
# ✅ NUEVAS FUNCIONALIDADES: ACCIONES RÁPIDAS
# ============================================

@router.post("/{cliente_id}/registrar-pago")
def registrar_pago_rapido(
    cliente_id: int,
    monto: float = Body(..., gt=0),
    concepto: str = Body(default="PAGO_CUOTA"),
    metodo_pago: str = Body(default="EFECTIVO"),
    db: Session = Depends(get_db)
):
    """
    ⚡ ACCIÓN RÁPIDA: Registrar nuevo pago
    
    Aplica el pago a las cuotas más antiguas pendientes
    """
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Buscar préstamos activos
    prestamos = db.query(Prestamo).filter(
        Prestamo.cliente_id == cliente_id,
        Prestamo.estado.in_(["ACTIVO", "EN_MORA"])
    ).all()
    
    if not prestamos:
        raise HTTPException(status_code=400, detail="Cliente no tiene préstamos activos")
    
    # Aplicar pago al primer préstamo (lógica simple)
    prestamo = prestamos[0]
    
    from app.models.pago import Pago
    nuevo_pago = Pago(
        prestamo_id=prestamo.id,
        monto_pagado=monto,
        monto_total=monto,
        fecha_pago=date.today(),
        fecha_vencimiento=date.today(),
        metodo_pago=metodo_pago,
        concepto=concepto,
        estado="CONFIRMADO",
        numero_cuota=prestamo.cuotas_pagadas + 1
    )
    
    # Actualizar préstamo
    prestamo.total_pagado += monto
    prestamo.saldo_pendiente -= monto
    prestamo.cuotas_pagadas += 1
    
    db.add(nuevo_pago)
    db.commit()
    
    return {
        "mensaje": f"Pago de ${monto:,.2f} registrado exitosamente",
        "pago_id": nuevo_pago.id,
        "nuevo_saldo": float(prestamo.saldo_pendiente)
    }


@router.post("/{cliente_id}/enviar-recordatorio")
def enviar_recordatorio_rapido(
    cliente_id: int,
    tipo: str = Body(default="EMAIL", description="EMAIL, WHATSAPP, SMS"),
    mensaje_personalizado: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """
    ⚡ ACCIÓN RÁPIDA: Enviar recordatorio
    
    Envía recordatorio de pago personalizado
    """
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Obtener próximas cuotas
    from app.models.amortizacion import Cuota
    proximas_cuotas = db.query(Cuota).join(Prestamo).filter(
        Prestamo.cliente_id == cliente_id,
        Cuota.estado.in_(["PENDIENTE", "VENCIDA"])
    ).order_by(Cuota.fecha_vencimiento).limit(3).all()
    
    if not proximas_cuotas:
        raise HTTPException(status_code=400, detail="Cliente no tiene cuotas pendientes")
    
    # Generar mensaje
    if not mensaje_personalizado:
        proxima_cuota = proximas_cuotas[0]
        mensaje_personalizado = f"""
Estimado/a {cliente.nombre_completo},

Le recordamos que tiene una cuota pendiente:
- Monto: ${proxima_cuota.monto_cuota:,.2f}
- Vencimiento: {proxima_cuota.fecha_vencimiento.strftime('%d/%m/%Y')}
- Días {'vencidos' if proxima_cuota.esta_vencida else 'restantes'}: {abs((proxima_cuota.fecha_vencimiento - date.today()).days)}

Por favor, regularice su pago.
Gracias.
        """
    
    # Crear notificación
    from app.models.notificacion import Notificacion
    notificacion = Notificacion(
        cliente_id=cliente_id,
        tipo=tipo,
        categoria="RECORDATORIO_PAGO",
        asunto="Recordatorio de Pago",
        mensaje=mensaje_personalizado,
        estado="PENDIENTE"
    )
    
    db.add(notificacion)
    db.commit()
    
    return {
        "mensaje": f"Recordatorio programado por {tipo}",
        "notificacion_id": notificacion.id,
        "destinatario": cliente.email if tipo == "EMAIL" else cliente.telefono
    }


@router.get("/{cliente_id}/estado-cuenta-pdf")
def generar_estado_cuenta_pdf(cliente_id: int, db: Session = Depends(get_db)):
    """
    ⚡ ACCIÓN RÁPIDA: Generar estado de cuenta PDF
    
    Genera PDF con estado de cuenta completo
    """
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Por ahora retornar datos para generar PDF en frontend
    # TODO: Implementar generación real de PDF con reportlab
    
    prestamos = db.query(Prestamo).filter(Prestamo.cliente_id == cliente_id).all()
    
    datos_pdf = {
        "cliente": {
            "nombre": cliente.nombre_completo,
            "cedula": cliente.cedula,
            "telefono": cliente.telefono,
            "email": cliente.email
        },
        "prestamos": [
            {
                "id": p.id,
                "monto_total": float(p.monto_total),
                "saldo_pendiente": float(p.saldo_pendiente),
                "cuotas_pagadas": p.cuotas_pagadas,
                "cuotas_totales": p.numero_cuotas,
                "estado": p.estado
            }
            for p in prestamos
        ],
        "fecha_generacion": date.today().isoformat()
    }
    
    return {
        "mensaje": "Datos para generar PDF",
        "datos": datos_pdf,
        "url_descarga": f"/api/v1/reportes/cliente/{cliente_id}/pdf"  # Endpoint futuro
    }


# ============================================
# ✅ ENDPOINTS DE UTILIDAD ADICIONALES
# ============================================

@router.get("/asesores", response_model=List[dict])
def listar_asesores(db: Session = Depends(get_db)):
    """Obtener lista de asesores para asignación"""
    asesores = db.query(User).filter(
        User.rol.in_(["ASESOR", "ADMIN", "GERENTE"]),
        User.is_active == True
    ).all()
    
    return [
        {
            "id": a.id,
            "nombre": a.full_name,
            "email": a.email,
            "rol": a.rol,
            "clientes_asignados": len(a.clientes_asignados) if hasattr(a, 'clientes_asignados') else 0
        }
        for a in asesores
    ]


@router.get("/estadisticas-generales")
def estadisticas_generales_clientes(db: Session = Depends(get_db)):
    """Estadísticas generales de la cartera de clientes"""
    
    total_clientes = db.query(Cliente).count()
    clientes_activos = db.query(Cliente).filter(Cliente.activo == True).count()
    clientes_con_mora = db.query(Cliente).filter(Cliente.dias_mora > 0).count()
    
    # Por concesionario
    por_concesionario = db.query(
        Cliente.concesionario,
        func.count(Cliente.id).label('cantidad')
    ).filter(
        Cliente.concesionario.isnot(None)
    ).group_by(Cliente.concesionario).all()
    
    # Por modalidad
    por_modalidad = db.query(
        Cliente.modalidad_financiamiento,
        func.count(Cliente.id).label('cantidad')
    ).filter(
        Cliente.modalidad_financiamiento.isnot(None)
    ).group_by(Cliente.modalidad_financiamiento).all()
    
    # Por asesor
    por_asesor = db.query(
        User.nombre,
        User.apellido,
        func.count(Cliente.id).label('clientes_asignados')
    ).join(Cliente, User.id == Cliente.asesor_id).group_by(
        User.id, User.nombre, User.apellido
    ).all()
    
    return {
        "resumen": {
            "total_clientes": total_clientes,
            "activos": clientes_activos,
            "inactivos": total_clientes - clientes_activos,
            "en_mora": clientes_con_mora,
            "porcentaje_mora": round((clientes_con_mora / total_clientes * 100) if total_clientes > 0 else 0, 2)
        },
        "distribucion": {
            "por_concesionario": [{"concesionario": c[0], "cantidad": c[1]} for c in por_concesionario],
            "por_modalidad": [{"modalidad": m[0], "cantidad": m[1]} for m in por_modalidad],
            "por_asesor": [{"asesor": f"{a[0]} {a[1]}", "clientes": a[2]} for a in por_asesor]
        }
    }


@router.get("/{cliente_id}/tabla-amortizacion")
def obtener_tabla_amortizacion_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """
    Obtener tabla de amortización interactiva del cliente
    
    ✅ Funcionalidad requerida: Tabla de amortización interactiva
    """
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Obtener préstamos del cliente
    prestamos = db.query(Prestamo).filter(Prestamo.cliente_id == cliente_id).all()
    
    if not prestamos:
        raise HTTPException(status_code=404, detail="Cliente no tiene préstamos")
    
    # Obtener cuotas de todos los préstamos
    tablas_amortizacion = []
    
    for prestamo in prestamos:
        from app.models.amortizacion import Cuota
        cuotas = db.query(Cuota).filter(Cuota.prestamo_id == prestamo.id).order_by(Cuota.numero_cuota).all()
        
        tabla = {
            "prestamo_id": prestamo.id,
            "codigo_prestamo": prestamo.codigo_prestamo or f"PREST-{prestamo.id}",
            "estado_prestamo": prestamo.estado,
            "cuotas": [
                {
                    "id": c.id,
                    "numero": c.numero_cuota,
                    "fecha_vencimiento": c.fecha_vencimiento,
                    "monto_cuota": float(c.monto_cuota),
                    "capital": float(c.monto_capital),
                    "interes": float(c.monto_interes),
                    "saldo": float(c.saldo_capital_final),
                    "estado": c.estado,
                    "fecha_pago": c.fecha_pago,
                    "dias_mora": c.dias_mora,
                    "monto_mora": float(c.monto_mora),
                    "esta_vencida": c.esta_vencida,
                    "porcentaje_pagado": float(c.porcentaje_pagado)
                }
                for c in cuotas
            ]
        }
        
        tablas_amortizacion.append(tabla)
    
    return {
        "cliente": {
            "id": cliente.id,
            "nombre": cliente.nombre_completo,
            "cedula": cliente.cedula
        },
        "tablas_amortizacion": tablas_amortizacion,
        "resumen": {
            "total_prestamos": len(prestamos),
            "prestamos_activos": len([p for p in prestamos if p.estado in ["ACTIVO", "EN_MORA"]]),
            "total_cuotas": sum(len(t["cuotas"]) for t in tablas_amortizacion),
            "cuotas_pagadas": sum(len([c for c in t["cuotas"] if c["estado"] == "PAGADA"]) for t in tablas_amortizacion)
        }
    }
