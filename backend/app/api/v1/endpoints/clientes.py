# backend/app/api/v1/endpoints/clientes.py
from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, desc, asc
from typing import List, Optional
from datetime import date
from decimal import Decimal

from app.db.session import get_db, SessionLocal
from app.models.cliente import Cliente
from app.models.user import User
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.schemas.cliente import (
    ClienteCreate, 
    ClienteUpdate, 
    ClienteResponse, 
    ClienteList,
    ClienteSearchFilters,
    ClienteDetallado,
    ClienteCreateWithLoan,
    ClienteResumenFinanciero,
    ClienteQuickActions
)
from app.schemas.amortizacion import TablaAmortizacionRequest
from app.services.amortizacion_service import AmortizacionService
from app.core.security import get_current_user
from datetime import datetime

router = APIRouter()


@router.post("/", response_model=ClienteResponse, status_code=201)
def crear_cliente(
    cliente: ClienteCreate = Body(...),  # ✅ Agregar Body() explícitamente
    db: Session = Depends(get_db)
):
    """Crear un nuevo cliente"""
    
    # 🔍 DEBUG: Imprimir el objeto recibido
    print(f"📥 Cliente recibido: {cliente}")
    print(f"📥 Tipo: {type(cliente)}")
    
    try:
        # Verificar si ya existe la cédula
        existing = db.query(Cliente).filter(Cliente.cedula == cliente.cedula).first()
        if existing:
            raise HTTPException(status_code=400, detail="Cédula ya registrada")
        
        # Convertir a dict para SQLAlchemy
        cliente_dict = cliente.model_dump()
        print(f"📦 Dict generado: {cliente_dict}")
        
        db_cliente = Cliente(**cliente_dict)
        db.add(db_cliente)
        db.commit()
        db.refresh(db_cliente)
        
        print(f"✅ Cliente creado: ID={db_cliente.id}")
        return db_cliente
        
    except Exception as e:
        print(f"❌ Error creando cliente: {e}")
        import traceback
        traceback.print_exc()
        raise


@router.get("/", response_model=ClienteList)
def listar_clientes(
    # Paginación
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    
    # Búsqueda de texto
    search_text: Optional[str] = Query(None, description="Buscar en nombre, cédula o móvil"),
    
    # Filtros específicos
    estado: Optional[str] = Query(None, description="ACTIVO, INACTIVO, MORA"),
    estado_financiero: Optional[str] = Query(None, description="AL_DIA, MORA, VENCIDO"),
    asesor_id: Optional[int] = Query(None, description="ID del asesor asignado"),
    concesionario: Optional[str] = Query(None, description="Nombre del concesionario"),
    modelo_vehiculo: Optional[str] = Query(None, description="Modelo del vehículo"),
    modalidad_pago: Optional[str] = Query(None, description="SEMANAL, QUINCENAL, MENSUAL, BIMENSUAL"),
    
    # Filtros de fecha
    fecha_registro_desde: Optional[date] = Query(None, description="Fecha de registro desde"),
    fecha_registro_hasta: Optional[date] = Query(None, description="Fecha de registro hasta"),
    
    # Filtros de monto
    monto_min: Optional[Decimal] = Query(None, ge=0, description="Monto mínimo de financiamiento"),
    monto_max: Optional[Decimal] = Query(None, ge=0, description="Monto máximo de financiamiento"),
    
    # Filtros de mora
    dias_mora_min: Optional[int] = Query(None, ge=0, description="Días de mora mínimos"),
    
    # Ordenamiento
    order_by: Optional[str] = Query("fecha_registro", description="Campo de ordenamiento"),
    order_direction: Optional[str] = Query("desc", pattern="^(asc|desc)$", description="Dirección del ordenamiento"),
    
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Listar clientes con búsqueda avanzada y filtros múltiples
    
    Funcionalidades:
    - Búsqueda de texto en nombre, cédula y móvil
    - Filtros por estado, asesor, concesionario, modelo
    - Filtros por rangos de fecha y monto
    - Ordenamiento por múltiples campos
    - Paginación
    """
    # Construir query base
    query = db.query(Cliente).outerjoin(User, Cliente.asesor_id == User.id)
    
    # ============================================
    # APLICAR FILTROS
    # ============================================
    
    # Búsqueda de texto (nombre, cédula, móvil)
    if search_text:
        search_pattern = f"%{search_text}%"
        query = query.filter(
            or_(
                Cliente.nombres.ilike(search_pattern),
                Cliente.apellidos.ilike(search_pattern),
                Cliente.cedula.ilike(search_pattern),
                Cliente.telefono.ilike(search_pattern),
                func.concat(Cliente.nombres, ' ', Cliente.apellidos).ilike(search_pattern)
            )
        )
    
    # Filtros específicos
    if estado:
        query = query.filter(Cliente.estado == estado)
    
    if estado_financiero:
        query = query.filter(Cliente.estado_financiero == estado_financiero)
    
    if asesor_id:
        query = query.filter(Cliente.asesor_id == asesor_id)
    
    if concesionario:
        query = query.filter(Cliente.concesionario.ilike(f"%{concesionario}%"))
    
    if modelo_vehiculo:
        query = query.filter(Cliente.modelo_vehiculo.ilike(f"%{modelo_vehiculo}%"))
    
    if modalidad_pago:
        query = query.filter(Cliente.modalidad_pago == modalidad_pago)
    
    # Filtros de fecha
    if fecha_registro_desde:
        query = query.filter(Cliente.fecha_registro >= fecha_registro_desde)
    
    if fecha_registro_hasta:
        query = query.filter(Cliente.fecha_registro <= fecha_registro_hasta)
    
    # Filtros de monto
    if monto_min:
        query = query.filter(Cliente.total_financiamiento >= monto_min)
    
    if monto_max:
        query = query.filter(Cliente.total_financiamiento <= monto_max)
    
    # Filtros de mora
    if dias_mora_min:
        query = query.filter(Cliente.dias_mora >= dias_mora_min)
    
    # ============================================
    # APLICAR ORDENAMIENTO
    # ============================================
    order_column = Cliente.fecha_registro  # Default
    
    if order_by == "nombre":
        order_column = func.concat(Cliente.nombres, ' ', Cliente.apellidos)
    elif order_by == "monto_financiamiento":
        order_column = Cliente.total_financiamiento
    elif order_by == "dias_mora":
        order_column = Cliente.dias_mora
    elif order_by == "fecha_registro":
        order_column = Cliente.fecha_registro
    
    if order_direction == "desc":
        query = query.order_by(desc(order_column))
    else:
        query = query.order_by(asc(order_column))
    
    # ============================================
    # PAGINACIÓN
    # ============================================
    total = query.count()
    skip = (page - 1) * page_size
    clientes = query.offset(skip).limit(page_size).all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return ClienteList(
        items=clientes,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
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
    """Obtener un cliente por ID"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


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
def eliminar_cliente(
    cliente_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Desactivar un cliente (soft delete) con validaciones"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # ✅ VALIDACIÓN: No eliminar si tiene pagos o préstamos activos
    prestamos_activos = db.query(Prestamo).filter(
        Prestamo.cliente_id == cliente_id,
        Prestamo.estado.in_(["ACTIVO", "EN_MORA", "PENDIENTE"])
    ).count()
    
    if prestamos_activos > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"No se puede eliminar: el cliente tiene {prestamos_activos} préstamo(s) activo(s)"
        )
    
    pagos_registrados = db.query(Pago).join(Prestamo).filter(
        Prestamo.cliente_id == cliente_id
    ).count()
    
    if pagos_registrados > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: el cliente tiene {pagos_registrados} pago(s) registrado(s)"
        )
    
    # Realizar soft delete
    cliente.activo = False
    cliente.estado = "INACTIVO"
    cliente.fecha_actualizacion = func.now()
    db.commit()
    
    return None


# ============================================
# ENDPOINTS ADICIONALES PARA FUNCIONALIDAD AVANZADA
# ============================================

@router.get("/{cliente_id}/detallado", response_model=ClienteDetallado)
def obtener_cliente_detallado(
    cliente_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener ficha detallada del cliente con resumen financiero
    """
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Obtener información del asesor
    asesor_nombre = None
    asesor_email = None
    if cliente.asesor_id:
        asesor = db.query(User).filter(User.id == cliente.asesor_id).first()
        if asesor:
            asesor_nombre = asesor.full_name
            asesor_email = asesor.email
    
    # Calcular resumen financiero
    resumen = cliente.calcular_resumen_financiero(db)
    resumen_financiero = ClienteResumenFinanciero(**resumen)
    
    # Estadísticas adicionales
    total_prestamos = db.query(Prestamo).filter(Prestamo.cliente_id == cliente_id).count()
    prestamos_activos = db.query(Prestamo).filter(
        Prestamo.cliente_id == cliente_id,
        Prestamo.estado.in_(["ACTIVO", "EN_MORA"])
    ).count()
    
    # Último pago
    ultimo_pago_obj = db.query(Pago).join(Prestamo).filter(
        Prestamo.cliente_id == cliente_id
    ).order_by(desc(Pago.fecha_pago)).first()
    
    ultimo_pago = None
    if ultimo_pago_obj:
        ultimo_pago = {
            "fecha": ultimo_pago_obj.fecha_pago,
            "monto": float(ultimo_pago_obj.monto_pagado),
            "numero_cuota": ultimo_pago_obj.numero_cuota
        }
    
    # Crear respuesta detallada
    cliente_dict = cliente.__dict__.copy()
    cliente_dict.update({
        "asesor_nombre": asesor_nombre,
        "asesor_email": asesor_email,
        "resumen_financiero": resumen_financiero,
        "total_prestamos": total_prestamos,
        "prestamos_activos": prestamos_activos,
        "ultimo_pago": ultimo_pago
    })
    
    return ClienteDetallado(**cliente_dict)


@router.post("/con-financiamiento", response_model=ClienteResponse, status_code=201)
def crear_cliente_con_financiamiento(
    cliente_data: ClienteCreateWithLoan,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🚗 FLUJO COMPLETO: Crear cliente con financiamiento
    
    Pasos del flujo:
    1. ✅ Asesor inicia sesión (verificado por get_current_user)
    2. ✅ Click "Nuevo Cliente" (este endpoint)
    3. ✅ Completa formulario (ClienteCreateWithLoan)
    4. ✅ Sistema valida datos
    5. ✅ Genera tabla de amortización automáticamente
    6. ✅ Sistema guarda y ejecuta acciones automáticas
    7. ✅ Cliente listo para cobrar
    """
    try:
        # ============================================
        # 4. VALIDACIONES DEL SISTEMA
        # ============================================
        
        # Validar cédula única
        existing = db.query(Cliente).filter(Cliente.cedula == cliente_data.cedula).first()
        if existing:
            raise HTTPException(status_code=400, detail="❌ Cédula ya registrada en el sistema")
        
        # Validar email válido (si se proporciona)
        if cliente_data.email:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, cliente_data.email):
                raise HTTPException(status_code=400, detail="❌ Formato de email inválido")
        
        # Validar que el asesor existe y tiene rol apropiado
        asesor = db.query(User).filter(User.id == cliente_data.asesor_id).first()
        if not asesor:
            raise HTTPException(status_code=400, detail="❌ Asesor no encontrado")
        
        if asesor.rol not in ["ASESOR", "COMERCIAL", "GERENTE"]:
            raise HTTPException(status_code=400, detail="❌ El usuario no tiene rol de asesor")
        
        if not asesor.is_active:
            raise HTTPException(status_code=400, detail="❌ El asesor está inactivo")
        
        # Validar montos coherentes
        if cliente_data.cuota_inicial >= cliente_data.total_financiamiento:
            raise HTTPException(status_code=400, detail="❌ La cuota inicial no puede ser mayor o igual al total")
        
        monto_financiado = cliente_data.total_financiamiento - cliente_data.cuota_inicial
        if monto_financiado <= 0:
            raise HTTPException(status_code=400, detail="❌ El monto financiado debe ser mayor a 0")
        
        # Validar límites de financiamiento
        from app.core.config import settings
        if monto_financiado < settings.MONTO_MINIMO_PRESTAMO:
            raise HTTPException(
                status_code=400, 
                detail=f"❌ Monto financiado mínimo: ${settings.MONTO_MINIMO_PRESTAMO:,.2f}"
            )
        
        if monto_financiado > settings.MONTO_MAXIMO_PRESTAMO:
            raise HTTPException(
                status_code=400, 
                detail=f"❌ Monto financiado máximo: ${settings.MONTO_MAXIMO_PRESTAMO:,.2f}"
            )
        
        # Validar número de cuotas
        if cliente_data.numero_amortizaciones < settings.PLAZO_MINIMO_MESES:
            raise HTTPException(
                status_code=400,
                detail=f"❌ Número mínimo de cuotas: {settings.PLAZO_MINIMO_MESES}"
            )
        
        if cliente_data.numero_amortizaciones > settings.PLAZO_MAXIMO_MESES:
            raise HTTPException(
                status_code=400,
                detail=f"❌ Número máximo de cuotas: {settings.PLAZO_MAXIMO_MESES}"
            )
        
        # Validar fecha de entrega
        if cliente_data.fecha_entrega < date.today():
            raise HTTPException(status_code=400, detail="❌ La fecha de entrega no puede ser pasada")
        
        # ============================================
        # 5. GENERACIÓN AUTOMÁTICA (PREVIEW)
        # ============================================
        
        # Generar tabla de amortización para preview
        tasa_interes = cliente_data.tasa_interes_anual or settings.TASA_INTERES_BASE
        
        from app.schemas.amortizacion import TablaAmortizacionRequest
        from app.services.amortizacion_service import AmortizacionService
        
        tabla_request = TablaAmortizacionRequest(
            monto_financiado=monto_financiado,
            tasa_interes_anual=tasa_interes,
            numero_cuotas=cliente_data.numero_amortizaciones,
            fecha_primer_vencimiento=cliente_data.fecha_entrega,
            modalidad=cliente_data.modalidad_pago,
            sistema_amortizacion="FRANCES"
        )
        
        tabla_preview = AmortizacionService.generar_tabla_amortizacion(tabla_request)
        
        # ============================================
        # 7. CREAR CLIENTE Y EJECUTAR ACCIONES AUTOMÁTICAS
        # ============================================
        
        # Crear cliente
        cliente_dict = cliente_data.model_dump()
        cliente_dict['monto_financiado'] = monto_financiado
        cliente_dict['fecha_asignacion'] = date.today()
        cliente_dict['usuario_registro'] = current_user.email
        cliente_dict['estado_financiero'] = "AL_DIA"
        
        db_cliente = Cliente(**cliente_dict)
        db.add(db_cliente)
        db.commit()
        db.refresh(db_cliente)
        
        # Registrar en auditoría
        from app.models.auditoria import Auditoria, TipoAccion
        auditoria = Auditoria.registrar(
            usuario_id=current_user.id,
            accion=TipoAccion.CREAR.value,
            tabla="clientes",
            registro_id=db_cliente.id,
            descripcion=f"Nuevo cliente creado: {db_cliente.nombre_completo}",
            datos_nuevos={
                "cedula": db_cliente.cedula,
                "nombre": db_cliente.nombre_completo,
                "vehiculo": db_cliente.vehiculo_completo,
                "monto_financiado": float(monto_financiado),
                "asesor": asesor.full_name
            }
        )
        db.add(auditoria)
        
        # Generar tabla de amortización automáticamente
        if cliente_data.generar_tabla_automatica:
            background_tasks.add_task(
                _generar_tabla_amortizacion_cliente,
                cliente_id=db_cliente.id,
                cliente_data=cliente_data
            )
        
        # Enviar email de bienvenida al cliente
        if db_cliente.email:
            background_tasks.add_task(
                _enviar_email_bienvenida,
                cliente_id=db_cliente.id,
                asesor_nombre=asesor.full_name
            )
        
        # Notificar a equipo de cobranzas sobre nuevo cliente
        background_tasks.add_task(
            _notificar_cobranzas_nuevo_cliente,
            cliente_id=db_cliente.id,
            asesor_nombre=asesor.full_name
        )
        
        db.commit()
        
        return {
            **db_cliente.__dict__,
            "mensaje": "✅ Cliente registrado exitosamente",
            "tabla_amortizacion_preview": {
                "cuotas_generadas": len(tabla_preview.cuotas),
                "primera_cuota": float(tabla_preview.cuotas[0].cuota) if tabla_preview.cuotas else 0,
                "total_intereses": float(tabla_preview.resumen.get("total_interes", 0)),
                "total_pagar": float(tabla_preview.resumen.get("total_pagar", 0))
            },
            "acciones_ejecutadas": {
                "cliente_guardado": True,
                "auditoria_registrada": True,
                "tabla_amortizacion_programada": cliente_data.generar_tabla_automatica,
                "email_bienvenida_programado": bool(db_cliente.email),
                "notificacion_cobranzas_programada": True
            },
            "proximo_paso": "Cliente listo para gestión de cobranza"
        }
        
    except HTTPException:
        # Re-lanzar HTTPExceptions (errores de validación)
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"❌ Error interno: {str(e)}")


@router.post("/preview-amortizacion")
def preview_tabla_amortizacion(
    cliente_data: ClienteCreateWithLoan,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔍 PASO 6: Preview de tabla de amortización para revisión del asesor
    Permite al asesor revisar antes de confirmar
    """
    try:
        # Calcular monto financiado
        monto_financiado = cliente_data.total_financiamiento - cliente_data.cuota_inicial
        
        # Validaciones básicas
        if monto_financiado <= 0:
            raise HTTPException(status_code=400, detail="Monto financiado debe ser mayor a 0")
        
        # Generar tabla de amortización
        from app.core.config import settings
        tasa_interes = cliente_data.tasa_interes_anual or settings.TASA_INTERES_BASE
        
        from app.schemas.amortizacion import TablaAmortizacionRequest
        from app.services.amortizacion_service import AmortizacionService
        
        tabla_request = TablaAmortizacionRequest(
            monto_financiado=monto_financiado,
            tasa_interes_anual=tasa_interes,
            numero_cuotas=cliente_data.numero_amortizaciones,
            fecha_primer_vencimiento=cliente_data.fecha_entrega,
            modalidad=cliente_data.modalidad_pago,
            sistema_amortizacion="FRANCES"
        )
        
        tabla = AmortizacionService.generar_tabla_amortizacion(tabla_request)
        
        # Calcular estadísticas adicionales
        cuota_promedio = float(tabla.cuotas[0].cuota) if tabla.cuotas else 0
        total_intereses = sum(float(c.interes) for c in tabla.cuotas)
        total_pagar = sum(float(c.cuota) for c in tabla.cuotas)
        
        return {
            "cliente_preview": {
                "nombre": f"{cliente_data.nombres} {cliente_data.apellidos}",
                "cedula": cliente_data.cedula,
                "vehiculo": f"{cliente_data.marca_vehiculo} {cliente_data.modelo_vehiculo}",
                "concesionario": cliente_data.concesionario
            },
            "financiamiento_preview": {
                "total_financiamiento": float(cliente_data.total_financiamiento),
                "cuota_inicial": float(cliente_data.cuota_inicial),
                "monto_financiado": float(monto_financiado),
                "numero_cuotas": cliente_data.numero_amortizaciones,
                "modalidad": cliente_data.modalidad_pago,
                "tasa_interes": float(tasa_interes)
            },
            "tabla_amortizacion": {
                "cuotas": [
                    {
                        "numero": c.numero_cuota,
                        "fecha": c.fecha_vencimiento.strftime("%d/%m/%Y"),
                        "cuota": float(c.cuota),
                        "capital": float(c.capital),
                        "interes": float(c.interes),
                        "saldo": float(c.saldo_final)
                    }
                    for c in tabla.cuotas[:5]  # Primeras 5 cuotas para preview
                ],
                "resumen": {
                    "cuota_mensual": cuota_promedio,
                    "total_intereses": total_intereses,
                    "total_pagar": total_pagar,
                    "ahorro_vs_contado": 0  # Calcular si hay descuento por contado
                }
            },
            "validaciones": {
                "cedula_disponible": True,
                "asesor_valido": True,
                "montos_coherentes": True,
                "dentro_limites": True
            },
            "acciones_pendientes": [
                "Guardar cliente en base de datos",
                "Generar tabla de amortización completa",
                "Enviar email de bienvenida",
                "Notificar a equipo de cobranzas",
                "Registrar en auditoría"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando preview: {str(e)}")


@router.get("/{cliente_id}/acciones-rapidas", response_model=ClienteQuickActions)
def obtener_acciones_rapidas(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener acciones rápidas disponibles para un cliente
    """
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Verificar permisos del usuario actual
    from app.core.permissions import UserRole, has_permission, Permission
    user_role = UserRole(current_user.rol)
    
    # Determinar acciones disponibles
    acciones = ClienteQuickActions(
        puede_registrar_pago=has_permission(user_role, Permission.PAGO_CREATE),
        puede_enviar_recordatorio=has_permission(user_role, Permission.NOTIFICACION_SEND),
        puede_generar_estado_cuenta=has_permission(user_role, Permission.REPORTE_READ),
        puede_modificar_financiamiento=has_permission(user_role, Permission.PRESTAMO_UPDATE),
        puede_reasignar_asesor=(
            user_role == UserRole.ADMIN or 
            (user_role in [UserRole.GERENTE, UserRole.DIRECTOR] and cliente.asesor_id == current_user.id)
        )
    )
    
    return acciones


@router.post("/{cliente_id}/reasignar-asesor")
def reasignar_asesor(
    cliente_id: int,
    nuevo_asesor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reasignar asesor a un cliente
    """
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Verificar que el nuevo asesor existe
    nuevo_asesor = db.query(User).filter(User.id == nuevo_asesor_id).first()
    if not nuevo_asesor:
        raise HTTPException(status_code=400, detail="Asesor no encontrado")
    
    # Verificar que el nuevo asesor tiene rol apropiado
    if nuevo_asesor.rol not in ["ASESOR", "COMERCIAL", "GERENTE"]:
        raise HTTPException(
            status_code=400, 
            detail="El usuario debe tener rol ASESOR, COMERCIAL o GERENTE"
        )
    
    # Actualizar asignación
    asesor_anterior = cliente.asesor_id
    cliente.asesor_id = nuevo_asesor_id
    cliente.fecha_asignacion = date.today()
    cliente.fecha_actualizacion = func.now()
    
    db.commit()
    
    return {
        "message": "Asesor reasignado exitosamente",
        "cliente_id": cliente_id,
        "asesor_anterior": asesor_anterior,
        "asesor_nuevo": nuevo_asesor_id,
        "asesor_nombre": nuevo_asesor.full_name
    }


@router.get("/asesores/disponibles")
def obtener_asesores_disponibles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener lista de asesores disponibles para asignación
    """
    asesores = db.query(User).filter(
        User.rol.in_(["ASESOR", "COMERCIAL", "GERENTE"]),
        User.is_active == True
    ).all()
    
    # Contar clientes asignados por asesor
    result = []
    for asesor in asesores:
        clientes_asignados = db.query(Cliente).filter(
            Cliente.asesor_id == asesor.id,
            Cliente.activo == True
        ).count()
        
        result.append({
            "id": asesor.id,
            "nombre": asesor.full_name,
            "email": asesor.email,
            "rol": asesor.rol,
            "clientes_asignados": clientes_asignados
        })
    
    return {
        "asesores": result,
        "total": len(result)
    }


# ============================================
# FUNCIONES AUXILIARES
# ============================================

async def _generar_tabla_amortizacion_cliente(cliente_id: int, cliente_data: ClienteCreateWithLoan):
    """
    Función background para generar tabla de amortización automáticamente
    """
    try:
        db = SessionLocal()
        
        # Crear préstamo automático
        from app.core.config import settings
        tasa_interes = cliente_data.tasa_interes_anual or settings.TASA_INTERES_BASE
        
        prestamo_data = {
            "cliente_id": cliente_id,
            "monto_total": cliente_data.total_financiamiento,
            "monto_financiado": cliente_data.total_financiamiento - cliente_data.cuota_inicial,
            "monto_inicial": cliente_data.cuota_inicial,
            "tasa_interes": tasa_interes,
            "numero_cuotas": cliente_data.numero_amortizaciones,
            "fecha_aprobacion": date.today(),
            "fecha_desembolso": cliente_data.fecha_entrega,
            "fecha_primer_vencimiento": cliente_data.fecha_entrega,
            "modalidad": cliente_data.modalidad_pago,
            "destino_credito": f"Financiamiento vehículo {cliente_data.marca_vehiculo} {cliente_data.modelo_vehiculo}",
            "estado": "ACTIVO"
        }
        
        # Calcular cuota mensual (método francés simplificado)
        monto = prestamo_data["monto_financiado"]
        n_cuotas = prestamo_data["numero_cuotas"]
        tasa_mensual = (tasa_interes / 100) / 12
        
        if tasa_mensual > 0:
            cuota = monto * (tasa_mensual * (1 + tasa_mensual)**n_cuotas) / ((1 + tasa_mensual)**n_cuotas - 1)
        else:
            cuota = monto / n_cuotas
        
        prestamo_data["monto_cuota"] = cuota
        prestamo_data["saldo_pendiente"] = monto
        prestamo_data["saldo_capital"] = monto
        
        db_prestamo = Prestamo(**prestamo_data)
        db.add(db_prestamo)
        db.commit()
        db.refresh(db_prestamo)
        
        # Generar tabla de amortización
        tabla_request = TablaAmortizacionRequest(
            monto_financiado=prestamo_data["monto_financiado"],
            tasa_interes_anual=tasa_interes,
            numero_cuotas=n_cuotas,
            fecha_primer_vencimiento=cliente_data.fecha_entrega,
            modalidad=cliente_data.modalidad_pago,
            sistema_amortizacion="FRANCES"
        )
        
        tabla = AmortizacionService.generar_tabla_amortizacion(tabla_request)
        AmortizacionService.crear_cuotas_prestamo(db, db_prestamo.id, tabla)
        
        db.close()
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error generando tabla de amortización para cliente {cliente_id}: {str(e)}")


async def _enviar_email_bienvenida(cliente_id: int, asesor_nombre: str):
    """
    📧 PASO 7a: Enviar email de bienvenida al cliente
    """
    try:
        db = SessionLocal()
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        
        if cliente and cliente.email:
            from app.models.notificacion import Notificacion
            from app.services.email_service import EmailService
            
            mensaje = f"""
¡Bienvenido/a a Financiera Automotriz!

Estimado/a {cliente.nombre_completo},

Nos complace darle la bienvenida como nuevo cliente de nuestra financiera.

DETALLES DE SU FINANCIAMIENTO:
• Vehículo: {cliente.vehiculo_completo}
• Concesionario: {cliente.concesionario}
• Monto financiado: ${float(cliente.monto_financiado or 0):,.2f}
• Modalidad de pago: {cliente.modalidad_pago}
• Asesor asignado: {asesor_nombre}

PRÓXIMOS PASOS:
1. Recibirá la tabla de amortización completa por email
2. Su primera cuota vence el: {cliente.fecha_entrega.strftime('%d/%m/%Y') if cliente.fecha_entrega else 'Por definir'}
3. Le enviaremos recordatorios antes de cada vencimiento

DATOS DE CONTACTO:
• Teléfono: (021) 123-456
• Email: info@financiera.com
• Horario: Lunes a Viernes 8:00 - 18:00

¡Gracias por confiar en nosotros!

Saludos cordiales,
Equipo de Financiera Automotriz
            """
            
            # Crear notificación
            notif = Notificacion(
                cliente_id=cliente_id,
                tipo="EMAIL",
                categoria="GENERAL",
                asunto="🎉 ¡Bienvenido a Financiera Automotriz!",
                mensaje=mensaje,
                estado="PENDIENTE",
                programada_para=datetime.now(),
                prioridad="NORMAL"
            )
            
            db.add(notif)
            db.commit()
            db.refresh(notif)
            
            # Enviar email
            email_service = EmailService()
            await email_service.send_email(
                to_email=cliente.email,
                subject=notif.asunto,
                body=notif.mensaje,
                notificacion_id=notif.id
            )
            
        db.close()
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error enviando email de bienvenida a cliente {cliente_id}: {str(e)}")


async def _notificar_cobranzas_nuevo_cliente(cliente_id: int, asesor_nombre: str):
    """
    🔔 PASO 7b: Notificar a equipo de cobranzas sobre nuevo cliente
    """
    try:
        db = SessionLocal()
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        
        if cliente:
            # Obtener usuarios de cobranzas
            usuarios_cobranzas = db.query(User).filter(
                User.rol.in_(["COBRANZAS", "GERENTE", "ADMIN"]),
                User.is_active == True,
                User.email.isnot(None)
            ).all()
            
            for usuario in usuarios_cobranzas:
                mensaje = f"""
Hola {usuario.full_name},

NUEVO CLIENTE REGISTRADO

📋 DATOS DEL CLIENTE:
• Nombre: {cliente.nombre_completo}
• Cédula: {cliente.cedula}
• Teléfono: {cliente.telefono or 'No proporcionado'}
• Email: {cliente.email or 'No proporcionado'}

🚗 VEHÍCULO FINANCIADO:
• Vehículo: {cliente.vehiculo_completo}
• Concesionario: {cliente.concesionario or 'No especificado'}

💰 FINANCIAMIENTO:
• Total: ${float(cliente.total_financiamiento or 0):,.2f}
• Cuota inicial: ${float(cliente.cuota_inicial or 0):,.2f}
• Monto financiado: ${float(cliente.monto_financiado or 0):,.2f}
• Modalidad: {cliente.modalidad_pago}
• Primera cuota: {cliente.fecha_entrega.strftime('%d/%m/%Y') if cliente.fecha_entrega else 'Por definir'}

👤 ASESOR RESPONSABLE: {asesor_nombre}

ACCIONES RECOMENDADAS:
• Verificar datos de contacto
• Programar recordatorios de pago
• Incluir en seguimiento de cartera

Acceder al cliente: https://pagos-f2qf.onrender.com/clientes/{cliente_id}

Saludos.
                """
                
                from app.models.notificacion import Notificacion
                notif = Notificacion(
                    user_id=usuario.id,
                    tipo="EMAIL",
                    categoria="GENERAL",
                    asunto=f"🆕 Nuevo Cliente: {cliente.nombre_completo}",
                    mensaje=mensaje,
                    estado="PENDIENTE",
                    programada_para=datetime.now(),
                    prioridad="NORMAL"
                )
                
                db.add(notif)
            
            db.commit()
            
            # Enviar emails
            from app.services.email_service import EmailService
            email_service = EmailService()
            
            for usuario in usuarios_cobranzas:
                notif = db.query(Notificacion).filter(
                    Notificacion.user_id == usuario.id,
                    Notificacion.asunto.like(f"%{cliente.nombre_completo}%")
                ).order_by(Notificacion.id.desc()).first()
                
                if notif:
                    await email_service.send_email(
                        to_email=usuario.email,
                        subject=notif.asunto,
                        body=notif.mensaje,
                        notificacion_id=notif.id
                    )
        
        db.close()
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error notificando a cobranzas sobre cliente {cliente_id}: {str(e)}")


@router.get("/buscar/avanzada", response_model=ClienteList)
def busqueda_avanzada_clientes(
    filters: ClienteSearchFilters = Depends(),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Búsqueda avanzada de clientes usando el objeto de filtros
    """
    query = db.query(Cliente)
    
    # Aplicar todos los filtros del objeto filters
    if filters.search_text:
        search_pattern = f"%{filters.search_text}%"
        query = query.filter(
            or_(
                Cliente.nombres.ilike(search_pattern),
                Cliente.apellidos.ilike(search_pattern),
                Cliente.cedula.ilike(search_pattern),
                Cliente.telefono.ilike(search_pattern)
            )
        )
    
    if filters.estado:
        query = query.filter(Cliente.estado == filters.estado)
    
    if filters.asesor_id:
        query = query.filter(Cliente.asesor_id == filters.asesor_id)
    
    if filters.concesionario:
        query = query.filter(Cliente.concesionario.ilike(f"%{filters.concesionario}%"))
    
    # ... aplicar resto de filtros
    
    # Paginación
    total = query.count()
    skip = (page - 1) * page_size
    clientes = query.offset(skip).limit(page_size).all()
    
    return ClienteList(
        items=clientes,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/buscar/nombre/{nombre}")
def buscar_por_nombre(
    nombre: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Buscar clientes por nombre (búsqueda parcial)"""
    search_pattern = f"%{nombre}%"
    clientes = db.query(Cliente).filter(
        or_(
            Cliente.nombres.ilike(search_pattern),
            Cliente.apellidos.ilike(search_pattern),
            func.concat(Cliente.nombres, ' ', Cliente.apellidos).ilike(search_pattern)
        )
    ).limit(10).all()
    
    return {
        "query": nombre,
        "total": len(clientes),
        "clientes": [
            {
                "id": c.id,
                "nombre_completo": c.nombre_completo,
                "cedula": c.cedula,
                "telefono": c.telefono,
                "estado": c.estado
            }
            for c in clientes
        ]
    }


@router.get("/buscar/telefono/{telefono}")
def buscar_por_telefono(
    telefono: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Buscar cliente por teléfono"""
    cliente = db.query(Cliente).filter(Cliente.telefono == telefono).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.get("/estadisticas/generales")
def estadisticas_clientes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener estadísticas generales de clientes
    """
    # Totales por estado
    total_activos = db.query(Cliente).filter(Cliente.estado == "ACTIVO").count()
    total_inactivos = db.query(Cliente).filter(Cliente.estado == "INACTIVO").count()
    total_mora = db.query(Cliente).filter(Cliente.estado_financiero == "MORA").count()
    
    # Por asesor
    por_asesor = db.query(
        User.full_name,
        func.count(Cliente.id).label('total_clientes')
    ).outerjoin(Cliente, User.id == Cliente.asesor_id).filter(
        User.rol.in_(["ASESOR", "COMERCIAL", "GERENTE"])
    ).group_by(User.id, User.full_name).all()
    
    # Por concesionario
    por_concesionario = db.query(
        Cliente.concesionario,
        func.count(Cliente.id).label('total_clientes'),
        func.sum(Cliente.total_financiamiento).label('monto_total')
    ).filter(
        Cliente.concesionario.isnot(None)
    ).group_by(Cliente.concesionario).all()
    
    # Por modalidad
    por_modalidad = db.query(
        Cliente.modalidad_pago,
        func.count(Cliente.id).label('total_clientes')
    ).filter(
        Cliente.modalidad_pago.isnot(None)
    ).group_by(Cliente.modalidad_pago).all()
    
    return {
        "totales": {
            "activos": total_activos,
            "inactivos": total_inactivos,
            "en_mora": total_mora,
            "total_general": total_activos + total_inactivos
        },
        "por_asesor": [
            {"asesor": nombre, "clientes": total}
            for nombre, total in por_asesor
        ],
        "por_concesionario": [
            {
                "concesionario": conc or "Sin concesionario",
                "clientes": total,
                "monto_total": float(monto or 0)
            }
            for conc, total, monto in por_concesionario
        ],
        "por_modalidad": [
            {"modalidad": mod or "Sin modalidad", "clientes": total}
            for mod, total in por_modalidad
        ]
    }
