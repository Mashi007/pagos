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
    order_direction: Optional[str] = Query("desc", regex="^(asc|desc)$", description="Dirección del ordenamiento"),
    
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
    Crear cliente con financiamiento y generar tabla de amortización automáticamente
    """
    try:
        # Verificar que no exista la cédula
        existing = db.query(Cliente).filter(Cliente.cedula == cliente_data.cedula).first()
        if existing:
            raise HTTPException(status_code=400, detail="Cédula ya registrada")
        
        # Verificar que el asesor existe
        asesor = db.query(User).filter(User.id == cliente_data.asesor_id).first()
        if not asesor:
            raise HTTPException(status_code=400, detail="Asesor no encontrado")
        
        # Calcular monto financiado
        monto_financiado = cliente_data.total_financiamiento - cliente_data.cuota_inicial
        
        # Crear cliente
        cliente_dict = cliente_data.model_dump()
        cliente_dict['monto_financiado'] = monto_financiado
        cliente_dict['fecha_asignacion'] = date.today()
        cliente_dict['usuario_registro'] = current_user.email
        
        db_cliente = Cliente(**cliente_dict)
        db.add(db_cliente)
        db.commit()
        db.refresh(db_cliente)
        
        # Generar tabla de amortización si se solicita
        if cliente_data.generar_tabla_automatica:
            background_tasks.add_task(
                _generar_tabla_amortizacion_cliente,
                cliente_id=db_cliente.id,
                cliente_data=cliente_data
            )
        
        return db_cliente
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creando cliente: {str(e)}")


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
