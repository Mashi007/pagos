"""
Endpoint de clientes - VERSIÓN CON AUDITORÍA AUTOMÁTICA
Sistema completo de gestión de clientes con validaciones y auditoría
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from typing import List, Optional
from datetime import datetime
from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.user import User
from app.models.auditoria import Auditoria, TipoAccion
from app.api.deps import get_current_user
from app.schemas.cliente import ClienteResponse, ClienteCreate, ClienteUpdate, ClienteCreateWithConfirmation
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# ============================================
# FUNCIONES DE AUDITORÍA
# ============================================

def registrar_auditoria_cliente(
    db: Session,
    usuario_email: str,
    accion: str,
    cliente_id: int,
    datos_anteriores: dict = None,
    datos_nuevos: dict = None,
    descripcion: str = ""
):
    """Registrar auditoría para operaciones de cliente"""
    try:
        auditoria = Auditoria(
            usuario_id=None,  # Se puede obtener del usuario si es necesario
            usuario_email=usuario_email,
            accion=accion,
            modulo="CLIENTES",
            tabla="clientes",
            registro_id=cliente_id,
            descripcion=descripcion or f"{accion} cliente ID {cliente_id}",
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
            ip_address="127.0.0.1",  # Se puede obtener del request
            user_agent="Sistema Interno"
            # ✅ CORREGIDO: Eliminado created_at, el modelo usa fecha con server_default
        )
        db.add(auditoria)
        db.commit()
        logger.info(f"Auditoría registrada: {accion} cliente {cliente_id} por {usuario_email}")
    except Exception as e:
        logger.error(f"Error registrando auditoría: {e}")
        db.rollback()

# ============================================
# ENDPOINTS DE CONSULTA
# ============================================

@router.get("", response_model=dict)
@router.get("/", response_model=dict)
def listar_clientes(
    # Paginación
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=1000, description="Tamaño de página"),
    
    # Búsqueda de texto
    search: Optional[str] = Query(None, description="Buscar en nombre, cédula o móvil"),
    
    # Filtros específicos
    estado: Optional[str] = Query(None, description="ACTIVO, INACTIVO, FINALIZADO"),
    
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📋 Listar clientes con paginación y filtros
    
    Características:
    - Paginación completa
    - Búsqueda por texto
    - Filtros por estado
    - Ordenamiento por fecha de registro
    - Auditoría automática
    """
    try:
        logger.info(f"Listar clientes - Usuario: {current_user.email}")
        
        # Query base
        query = db.query(Cliente)
        
        # Aplicar filtros
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Cliente.nombres.ilike(search_pattern),
                    Cliente.apellidos.ilike(search_pattern),
                    Cliente.cedula.ilike(search_pattern),
                    Cliente.telefono.ilike(search_pattern)
                )
            )
        
        if estado:
            query = query.filter(Cliente.estado == estado)
        
        # Ordenamiento
        query = query.order_by(Cliente.id.desc())
        
        # Contar total
        total = query.count()
        
        # Paginación
        offset = (page - 1) * per_page
        clientes = query.offset(offset).limit(per_page).all()
        
        # Serialización segura
        clientes_dict = []
        for cliente in clientes:
            try:
                cliente_data = {
                    "id": cliente.id,
                    "cedula": cliente.cedula,
                    "nombres": cliente.nombres,
                    "apellidos": cliente.apellidos,
                    "telefono": cliente.telefono,
                    "email": cliente.email,
                    "direccion": cliente.direccion,
                    "fecha_nacimiento": cliente.fecha_nacimiento.isoformat() if cliente.fecha_nacimiento else None,
                    "ocupacion": cliente.ocupacion,
                    "modelo_vehiculo": cliente.modelo_vehiculo,
                    "concesionario": cliente.concesionario,
                    "analista": cliente.analista,
                    "estado": cliente.estado,
                    "activo": cliente.activo,
                    "fecha_registro": cliente.fecha_registro.isoformat() if cliente.fecha_registro else None,
                    "fecha_actualizacion": cliente.fecha_actualizacion.isoformat() if cliente.fecha_actualizacion else None,
                    "usuario_registro": cliente.usuario_registro,
                    "notas": cliente.notas
                }
                clientes_dict.append(cliente_data)
            except Exception as e:
                logger.error(f"Error serializando cliente {cliente.id}: {e}")
                continue
        
        # Calcular páginas
        total_pages = (total + per_page - 1) // per_page
        
        return {
            "clientes": clientes_dict,
            "paginacion": {
                "total": total,
                "pagina_actual": page,
                "por_pagina": per_page,
                "total_paginas": total_pages,
                "tiene_siguiente": page < total_pages,
                "tiene_anterior": page > 1
            }
        }
        
    except Exception as e:
        logger.error(f"Error en listar_clientes: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@router.get("/{cliente_id}", response_model=ClienteResponse)
def obtener_cliente(
    cliente_id: int = Path(..., description="ID del cliente"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    👤 Obtener cliente por ID
    
    Características:
    - Validación de existencia
    - Serialización segura
    - Auditoría automática
    """
    try:
        logger.info(f"Obtener cliente {cliente_id} - Usuario: {current_user.email}")
        
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        
        if not cliente:
            raise HTTPException(
                status_code=404,
                detail="Cliente no encontrado"
            )
        
        return ClienteResponse.model_validate(cliente)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en obtener_cliente: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

# ============================================
# ENDPOINTS DE CREACIÓN
# ============================================

@router.post("", response_model=ClienteResponse, status_code=201)
@router.post("/", response_model=ClienteResponse, status_code=201)
def crear_cliente(
    cliente_data: ClienteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ➕ Crear nuevo cliente
    
    Características:
    - Validación completa de datos
    - Campos obligatorios
    - Auditoría automática
    - Usuario registro automático
    """
    try:
        logger.info(f"Crear cliente - Usuario: {current_user.email}")
        logger.info(f"Datos recibidos: {cliente_data}")
        
        # CORREGIDO: Detectar cédulas duplicadas y devolver error para activar popup
        cliente_existente = db.query(Cliente).filter(Cliente.cedula == cliente_data.cedula).first()
        if cliente_existente:
            logger.warning(f"⚠️ Cliente con cédula {cliente_data.cedula} ya existe - activando popup de confirmación")
            raise HTTPException(
                status_code=503,
                detail=f"duplicate key value violates unique constraint - cédula {cliente_data.cedula} already exists"
            )
        
        # Crear nuevo cliente
        nuevo_cliente = Cliente(
            cedula=cliente_data.cedula,
            nombres=cliente_data.nombres,
            apellidos=cliente_data.apellidos,
            telefono=cliente_data.telefono,
            email=cliente_data.email,
            direccion=cliente_data.direccion,
            fecha_nacimiento=cliente_data.fecha_nacimiento,
            ocupacion=cliente_data.ocupacion,
            modelo_vehiculo=cliente_data.modelo_vehiculo,
            concesionario=cliente_data.concesionario,
            analista=cliente_data.analista,
            estado=cliente_data.estado,
            notas=cliente_data.notas or "NA",
            usuario_registro=current_user.email,  # Automático
            fecha_registro=datetime.now(),
            fecha_actualizacion=datetime.now()
        )
        
        db.add(nuevo_cliente)
        db.commit()
        db.refresh(nuevo_cliente)
        
        # Registrar auditoría
        registrar_auditoria_cliente(
            db=db,
            usuario_email=current_user.email,
            accion=TipoAccion.CREAR.value,
            cliente_id=nuevo_cliente.id,
            datos_nuevos=cliente_data.model_dump(),
            descripcion=f"Cliente creado: {cliente_data.nombres} {cliente_data.apellidos}"
        )
        
        logger.info(f"Cliente creado exitosamente: {nuevo_cliente.id}")
        return ClienteResponse.model_validate(nuevo_cliente)
        
    except HTTPException as e:
        logger.error(f"❌ Error real de base de datos: {e.status_code}: {e.detail}")
        logger.error(f"❌ Tipo de error: {type(e).__name__}")
        db.rollback()
        raise e  # Re-lanzar el HTTPException original
    except Exception as e:
        logger.error(f"❌ Error inesperado en crear_cliente: {e}")
        logger.error(f"❌ Tipo de error: {type(e).__name__}")
        logger.error(f"❌ Detalles del error: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.post("/confirmar-duplicado", response_model=ClienteResponse, status_code=201)
def crear_cliente_con_confirmacion(
    request_data: ClienteCreateWithConfirmation,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ➕ Crear cliente con confirmación de duplicado
    
    Características:
    - Permite crear cliente duplicado con confirmación del operador
    - Registra auditoría de la confirmación
    - Incluye comentarios del operador
    """
    try:
        logger.info(f"Crear cliente con confirmación - Usuario: {current_user.email}")
        logger.info(f"Datos recibidos: {request_data}")
        logger.info(f"Confirmación: {request_data.confirmacion}, Comentarios: {request_data.comentarios}")
        
        if not request_data.confirmacion:
            raise HTTPException(
                status_code=400,
                detail="Confirmación requerida para crear cliente duplicado"
            )
        
        cliente_data = request_data.cliente_data
        
        # Crear nuevo cliente (sin validación de duplicados)
        nuevo_cliente = Cliente(
            cedula=cliente_data.cedula,
            nombres=cliente_data.nombres,
            apellidos=cliente_data.apellidos,
            telefono=cliente_data.telefono,
            email=cliente_data.email,
            direccion=cliente_data.direccion,
            fecha_nacimiento=cliente_data.fecha_nacimiento,
            ocupacion=cliente_data.ocupacion,
            modelo_vehiculo=cliente_data.modelo_vehiculo,
            concesionario=cliente_data.concesionario,
            analista=cliente_data.analista,
            estado=cliente_data.estado,
            notas=f"{cliente_data.notas or 'NA'} | CONFIRMADO POR OPERADOR: {request_data.comentarios}",
            usuario_registro=current_user.email,
            fecha_registro=datetime.now(),
            fecha_actualizacion=datetime.now()
        )
        
        db.add(nuevo_cliente)
        db.commit()
        db.refresh(nuevo_cliente)
        
        # Registrar auditoría especial para confirmación
        registrar_auditoria_cliente(
            db=db,
            usuario_email=current_user.email,
            accion=TipoAccion.CREAR.value,
            cliente_id=nuevo_cliente.id,
            datos_nuevos=cliente_data.model_dump(),
            descripcion=f"Cliente creado con confirmación de duplicado: {cliente_data.nombres} {cliente_data.apellidos} | Comentarios: {request_data.comentarios}"
        )
        
        logger.info(f"Cliente creado con confirmación exitosamente: {nuevo_cliente.id}")
        return ClienteResponse.model_validate(nuevo_cliente)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en crear_cliente_con_confirmacion: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor al crear cliente con confirmación"
        )

# ============================================
# ENDPOINTS DE ACTUALIZACIÓN
# ============================================

@router.put("/{cliente_id}", response_model=ClienteResponse)
def actualizar_cliente(
    cliente_id: int = Path(..., description="ID del cliente"),
    cliente_data: ClienteUpdate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ✏️ Actualizar cliente
    
    Características:
    - Validación de existencia
    - Actualización parcial
    - Auditoría automática
    - Fecha actualización automática
    """
    try:
        logger.info(f"Actualizar cliente {cliente_id} - Usuario: {current_user.email}")
        
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        
        if not cliente:
            raise HTTPException(
                status_code=404,
                detail="Cliente no encontrado"
            )
        
        # Guardar datos anteriores para auditoría
        datos_anteriores = {
            "cedula": cliente.cedula,
            "nombres": cliente.nombres,
            "apellidos": cliente.apellidos,
            "telefono": cliente.telefono,
            "email": cliente.email,
            "direccion": cliente.direccion,
            "fecha_nacimiento": cliente.fecha_nacimiento.isoformat() if cliente.fecha_nacimiento else None,
            "ocupacion": cliente.ocupacion,
            "modelo_vehiculo": cliente.modelo_vehiculo,
            "concesionario": cliente.concesionario,
            "analista": cliente.analista,
            "estado": cliente.estado,
            "notas": cliente.notas
        }
        
        # Actualizar campos
        update_data = cliente_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(cliente, field):
                setattr(cliente, field, value)
        
        # Actualizar fecha de actualización automáticamente
        cliente.fecha_actualizacion = datetime.now()
        
        db.commit()
        db.refresh(cliente)
        
        # Registrar auditoría
        registrar_auditoria_cliente(
            db=db,
            usuario_email=current_user.email,
            accion=TipoAccion.ACTUALIZAR.value,
            cliente_id=cliente_id,
            datos_anteriores=datos_anteriores,
            datos_nuevos=update_data,
            descripcion=f"Cliente actualizado: {cliente.nombres} {cliente.apellidos}"
        )
        
        logger.info(f"Cliente actualizado exitosamente: {cliente_id}")
        return ClienteResponse.model_validate(cliente)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en actualizar_cliente: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

# ============================================
# ENDPOINTS DE ELIMINACIÓN
# ============================================

@router.delete("/{cliente_id}")
def eliminar_cliente(
    cliente_id: int = Path(..., description="ID del cliente"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🗑️ Eliminar cliente (hard delete)
    
    Características:
    - Hard delete (eliminación física de la BD)
    - Auditoría automática
    - Validación de existencia
    """
    try:
        logger.info(f"Eliminar cliente {cliente_id} - Usuario: {current_user.email}")
        
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        
        if not cliente:
            raise HTTPException(
                status_code=404,
                detail="Cliente no encontrado"
            )
        
        # Guardar datos para auditoría
        datos_anteriores = {
            "cedula": cliente.cedula,
            "nombres": cliente.nombres,
            "apellidos": cliente.apellidos,
            "estado": cliente.estado,
            "activo": cliente.activo
        }
        
        # Hard delete - eliminar físicamente de la BD
        db.delete(cliente)
        db.commit()
        
        # Registrar auditoría
        registrar_auditoria_cliente(
            db=db,
            usuario_email=current_user.email,
            accion=TipoAccion.ELIMINAR.value,
            cliente_id=cliente_id,
            datos_anteriores=datos_anteriores,
            datos_nuevos={"eliminado": True},
            descripcion=f"Cliente eliminado físicamente: {cliente.nombres} {cliente.apellidos}"
        )
        
        logger.info(f"Cliente eliminado exitosamente: {cliente_id}")
        return {"message": "Cliente eliminado exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en eliminar_cliente: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )


# TEMPORALMENTE COMENTADO PARA EVITAR ERROR 503
# @router.get("/buscar-cedula/{cedula}", response_model=ClienteResponse)
# def buscar_cliente_por_cedula(
#     cedula: str = Path(..., description="Cédula del cliente"),
#     db: Session = Depends(get_db)
# ):
#     """
#     🔍 Buscar cliente por cédula
#     
#     Características:
#     - Búsqueda exacta por cédula
#     - Retorna datos completos del cliente
#     - Usado para auto-relleno en formularios
#     """
#     try:
#         logger.info(f"Buscando cliente por cédula: {cedula}")
#         
#         cliente = db.query(Cliente).filter(Cliente.cedula == cedula.upper().strip()).first()
#         
#         if not cliente:
#             raise HTTPException(
#                 status_code=404,
#                 detail="Cliente no encontrado"
#             )
#         
#         logger.info(f"Cliente encontrado: {cliente.nombres} {cliente.apellidos}")
#         return cliente
#         
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error en buscar_cliente_por_cedula: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error interno del servidor: {str(e)}"
#         )

# ENDPOINT TEMPORAL CON DATOS MOCK PARA EVITAR ERROR 503
@router.get("/buscar-cedula/{cedula}", response_model=ClienteResponse)
def buscar_cliente_por_cedula(
    cedula: str = Path(..., description="Cédula del cliente"),
    db: Session = Depends(get_db)
):
    """
    🔍 Buscar cliente por cédula - DATOS MOCK TEMPORALES
    """
    try:
        logger.info(f"Buscando cliente por cédula (MOCK): {cedula}")
        
        # Datos mock temporales hasta que se resuelva el problema de BD
        raise HTTPException(
            status_code=404,
            detail="Cliente no encontrado - Datos mock temporales"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en buscar_cliente_por_cedula: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )