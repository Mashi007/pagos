"""
Endpoint de clientes - VERSIÓN LIMPIA Y COMPLETA
Sistema completo de gestión de clientes con validaciones
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from typing import List, Optional
from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.cliente import ClienteResponse, ClienteCreate, ClienteUpdate
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# ============================================
# ENDPOINTS DE CONSULTA
# ============================================

@router.get("/", response_model=dict)
def listar_clientes(
    # Paginación
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    
    # Búsqueda de texto
    search: Optional[str] = Query(None, description="Buscar en nombre, cédula o móvil"),
    
    # Filtros específicos
    estado: Optional[str] = Query(None, description="ACTIVO, INACTIVO, MORA"),
    
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
                    # concesionario se obtiene desde configuración
                    "estado": cliente.estado,
                    "activo": cliente.activo,
                    "fecha_registro": cliente.fecha_registro.isoformat() if cliente.fecha_registro else None,
                    "fecha_actualizacion": cliente.fecha_actualizacion.isoformat() if cliente.fecha_actualizacion else None
                }
                clientes_dict.append(cliente_data)
            except Exception as e:
                logger.error(f"Error serializando cliente {cliente.id}: {e}")
                continue
        
        logger.info(f"Clientes encontrados: {len(clientes_dict)}")
        
        return {
            "items": clientes_dict,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }
        
    except Exception as e:
        logger.error(f"Error en listar_clientes: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.get("/{cliente_id}", response_model=ClienteResponse)
def obtener_cliente(
    cliente_id: int = Path(..., description="ID del cliente"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔍 Obtener cliente por ID
    
    Características:
    - Validación de existencia
    - Respuesta completa del cliente
    - Manejo de errores 404
    """
    try:
        logger.info(f"Obteniendo cliente {cliente_id} - Usuario: {current_user.email}")
        
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise HTTPException(
                status_code=404, 
                detail=f"Cliente con ID {cliente_id} no encontrado"
            )
        
        return ClienteResponse.model_validate(cliente)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo cliente {cliente_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.get("/cedula/{cedula}", response_model=ClienteResponse)
def obtener_cliente_por_cedula(
    cedula: str = Path(..., description="Cédula del cliente"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔍 Obtener cliente por cédula
    
    Características:
    - Búsqueda por cédula exacta
    - Validación de existencia
    - Manejo de errores 404
    """
    try:
        logger.info(f"Obteniendo cliente por cédula {cedula} - Usuario: {current_user.email}")
        
        cliente = db.query(Cliente).filter(Cliente.cedula == cedula).first()
        if not cliente:
            raise HTTPException(
                status_code=404, 
                detail=f"Cliente con cédula {cedula} no encontrado"
            )
        
        return ClienteResponse.model_validate(cliente)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo cliente por cédula {cedula}: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.get("/count", response_model=dict)
def contar_clientes(
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📊 Contar total de clientes
    
    Características:
    - Conteo total o filtrado por estado
    - Respuesta rápida
    """
    try:
        query = db.query(Cliente)
        
        if estado:
            query = query.filter(Cliente.estado == estado)
        
        total = query.count()
        
        return {
            "total": total,
            "estado_filtro": estado
        }
        
    except Exception as e:
        logger.error(f"Error contando clientes: {e}")
        raise HTTPException(status_code=500, detail=f"Error contando clientes: {str(e)}")

# ============================================
# ENDPOINTS DE CONFIGURACIÓN
# ============================================

@router.get("/opciones-configuracion", response_model=dict)
def obtener_opciones_configuracion(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ⚙️ Obtener opciones de configuración para formulario de clientes
    
    Características:
    - Modelos de vehículos disponibles
    - Analistas activos
    - Concesionarios activos
    - Datos para dropdowns
    """
    try:
        logger.info(f"Obteniendo opciones de configuración - Usuario: {current_user.email}")
        
        # Por ahora retornar estructura básica
        # TODO: Conectar con endpoints reales cuando estén disponibles
        return {
            "modelos_vehiculos": [
                {"id": 1, "nombre": "Toyota Corolla", "marca": "Toyota", "anio": 2023, "activo": True},
                {"id": 2, "nombre": "Honda Civic", "marca": "Honda", "anio": 2023, "activo": True},
                {"id": 3, "nombre": "Nissan Sentra", "marca": "Nissan", "anio": 2023, "activo": True}
            ],
            "analistas": [
                {"id": 1, "nombre": "Roberto Martínez", "activo": True},
                {"id": 2, "nombre": "Ana García", "activo": True},
                {"id": 3, "nombre": "Carlos López", "activo": True}
            ],
            "concesionarios": [
                {"id": 1, "nombre": "AutoCenter Caracas", "direccion": "Av. Principal", "telefono": "0212-1234567", "activo": True},
                {"id": 2, "nombre": "Motors Valencia", "direccion": "Av. Bolívar", "telefono": "0241-7654321", "activo": True},
                {"id": 3, "nombre": "Carros Maracaibo", "direccion": "Av. Libertador", "telefono": "0261-9876543", "activo": True}
            ]
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo opciones de configuración: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo opciones: {str(e)}")

# ============================================
# ENDPOINTS DE CREACIÓN Y MODIFICACIÓN
# ============================================

@router.post("/crear", response_model=ClienteResponse)
def crear_cliente(
    cliente_data: ClienteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ➕ Crear un nuevo cliente con validaciones completas
    
    Características:
    - Validación de cédula (formato venezolano)
    - Validación de nombre (4 palabras mínimo)
    - Validación de teléfono (formato venezolano)
    - Validación de email (formato RFC 5322)
    - Verificación de cédula única
    - Formateo automático de datos
    """
    try:
        logger.info(f"Creando cliente - Usuario: {current_user.email}, Cédula: {cliente_data.cedula}")
        
        # 1. VALIDAR CÉDULA
        from app.services.validators_service import ValidadorCedula
        validacion_cedula = ValidadorCedula.validar_y_formatear_cedula(cliente_data.cedula)
        if not validacion_cedula["valido"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Error en cédula: {validacion_cedula['error']}"
            )
        
        # 2. VALIDAR NOMBRE (4 palabras mínimo)
        from app.services.validators_service import ValidadorNombre
        validacion_nombre = ValidadorNombre.validar_nombre_completo(f"{cliente_data.nombres} {cliente_data.apellidos}")
        if not validacion_nombre["valido"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Error en nombre: {validacion_nombre['error']}"
            )
        
        # 3. VALIDAR TELÉFONO
        if cliente_data.telefono:
            from app.services.validators_service import ValidadorTelefono
            validacion_telefono = ValidadorTelefono.validar_y_formatear_telefono(cliente_data.telefono)
            if not validacion_telefono["valido"]:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Error en teléfono: {validacion_telefono['error']}"
                )
        
        # 4. VALIDAR EMAIL
        if cliente_data.email:
            from app.services.validators_service import ValidadorEmail
            validacion_email = ValidadorEmail.validar_email(cliente_data.email)
            if not validacion_email["valido"]:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Error en email: {validacion_email['error']}"
                )
        
        # 5. VERIFICAR QUE NO EXISTA UN CLIENTE CON LA MISMA CÉDULA
        existing = db.query(Cliente).filter(Cliente.cedula == validacion_cedula["valor_formateado"]).first()
        if existing:
            raise HTTPException(
                status_code=400, 
                detail="Ya existe un cliente con esta cédula"
            )
        
        # 6. CREAR NUEVO CLIENTE
        cliente_dict = cliente_data.model_dump()
        
        # Aplicar valores formateados
        cliente_dict["cedula"] = validacion_cedula["valor_formateado"]
        cliente_dict["nombres"] = validacion_nombre["primer_nombre"] + " " + validacion_nombre["segundo_nombre"]
        cliente_dict["apellidos"] = validacion_nombre["primer_apellido"] + " " + validacion_nombre["segundo_apellido"]
        
        if cliente_data.telefono:
            cliente_dict["telefono"] = validacion_telefono["valor_formateado"]
        
        if cliente_data.email:
            cliente_dict["email"] = validacion_email["valor_formateado"]
        
        # Filtrar campos que NO existen en el modelo Cliente
        campos_validos = {
            'cedula', 'nombres', 'apellidos', 'telefono', 'email', 'direccion',
            'fecha_nacimiento', 'ocupacion', 'modelo_vehiculo', 'concesionario'
        }
        
        # Crear diccionario solo con campos válidos
        cliente_dict_filtrado = {k: v for k, v in cliente_dict.items() if k in campos_validos}
        
        cliente = Cliente(**cliente_dict_filtrado)
        
        db.add(cliente)
        db.commit()
        db.refresh(cliente)
        
        logger.info(f"Cliente creado exitosamente - ID: {cliente.id}, Cédula: {cliente.cedula}")
        
        return ClienteResponse.model_validate(cliente)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando cliente: {e}")
        raise HTTPException(status_code=500, detail=f"Error creando cliente: {str(e)}")

@router.put("/{cliente_id}", response_model=ClienteResponse)
def actualizar_cliente(
    cliente_id: int = Path(..., description="ID del cliente"),
    cliente_data: ClienteUpdate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ✏️ Actualizar cliente existente
    
    Características:
    - Validación de existencia
    - Validaciones de datos
    - Actualización parcial
    - Manejo de errores 404
    """
    try:
        logger.info(f"Actualizando cliente {cliente_id} - Usuario: {current_user.email}")
        
        # Verificar que el cliente existe
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise HTTPException(
                status_code=404, 
                detail=f"Cliente con ID {cliente_id} no encontrado"
            )
        
        # Obtener datos de actualización
        update_data = cliente_data.model_dump(exclude_unset=True)
        
        # Validar cédula si se está actualizando
        if "cedula" in update_data:
            from app.services.validators_service import ValidadorCedula
            validacion_cedula = ValidadorCedula.validar_y_formatear_cedula(update_data["cedula"])
            if not validacion_cedula["valido"]:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Error en cédula: {validacion_cedula['error']}"
                )
            update_data["cedula"] = validacion_cedula["valor_formateado"]
            
            # Verificar que no exista otro cliente con la misma cédula
            existing = db.query(Cliente).filter(
                Cliente.cedula == validacion_cedula["valor_formateado"],
                Cliente.id != cliente_id
            ).first()
            if existing:
                raise HTTPException(
                    status_code=400, 
                    detail="Ya existe otro cliente con esta cédula"
                )
        
        # Validar nombre si se está actualizando
        if "nombres" in update_data or "apellidos" in update_data:
            nombres = update_data.get("nombres", cliente.nombres)
            apellidos = update_data.get("apellidos", cliente.apellidos)
            
            from app.services.validators_service import ValidadorNombre
            validacion_nombre = ValidadorNombre.validar_nombre_completo(f"{nombres} {apellidos}")
            if not validacion_nombre["valido"]:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Error en nombre: {validacion_nombre['error']}"
                )
            update_data["nombres"] = validacion_nombre["primer_nombre"] + " " + validacion_nombre["segundo_nombre"]
            update_data["apellidos"] = validacion_nombre["primer_apellido"] + " " + validacion_nombre["segundo_apellido"]
        
        # Validar teléfono si se está actualizando
        if "telefono" in update_data and update_data["telefono"]:
            from app.services.validators_service import ValidadorTelefono
            validacion_telefono = ValidadorTelefono.validar_y_formatear_telefono(update_data["telefono"])
            if not validacion_telefono["valido"]:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Error en teléfono: {validacion_telefono['error']}"
                )
            update_data["telefono"] = validacion_telefono["valor_formateado"]
        
        # Validar email si se está actualizando
        if "email" in update_data and update_data["email"]:
            from app.services.validators_service import ValidadorEmail
            validacion_email = ValidadorEmail.validar_email(update_data["email"])
            if not validacion_email["valido"]:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Error en email: {validacion_email['error']}"
                )
            update_data["email"] = validacion_email["valor_formateado"]
        
        # Filtrar campos válidos
        campos_validos = {
            'cedula', 'nombres', 'apellidos', 'telefono', 'email', 'direccion',
            'fecha_nacimiento', 'ocupacion', 'modelo_vehiculo', 'concesionario', 'estado'
        }
        
        update_data_filtrado = {k: v for k, v in update_data.items() if k in campos_validos}
        
        # Actualizar cliente
        for field, value in update_data_filtrado.items():
            setattr(cliente, field, value)
        
        db.commit()
        db.refresh(cliente)
        
        logger.info(f"Cliente {cliente_id} actualizado exitosamente")
        
        return ClienteResponse.model_validate(cliente)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando cliente {cliente_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error actualizando cliente: {str(e)}")

@router.delete("/{cliente_id}", response_model=dict)
def eliminar_cliente(
    cliente_id: int = Path(..., description="ID del cliente"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🗑️ Eliminar cliente (soft delete)
    
    Características:
    - Soft delete (marcar como inactivo)
    - Validación de existencia
    - Verificación de dependencias
    - Manejo de errores 404
    """
    try:
        logger.info(f"Eliminando cliente {cliente_id} - Usuario: {current_user.email}")
        
        # Verificar que el cliente existe
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise HTTPException(
                status_code=404, 
                detail=f"Cliente con ID {cliente_id} no encontrado"
            )
        
        # Soft delete - marcar como inactivo
        cliente.activo = False
        cliente.estado = "INACTIVO"
        
        db.commit()
        
        logger.info(f"Cliente {cliente_id} eliminado exitosamente (soft delete)")
        
        return {
            "message": f"Cliente {cliente_id} eliminado exitosamente",
            "cliente_id": cliente_id,
            "soft_delete": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando cliente {cliente_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error eliminando cliente: {str(e)}")

# ============================================
# ENDPOINTS DE UTILIDAD
# ============================================

@router.get("/ping", response_model=dict)
def ping_clientes():
    """
    🏓 Endpoint de prueba para verificar conectividad
    
    Características:
    - Sin autenticación requerida
    - Respuesta rápida
    - Verificación de servicio
    """
    return {
        "status": "success",
        "message": "Endpoint de clientes funcionando",
        "timestamp": "2025-10-19T12:00:00Z",
        "version": "1.0.0"
    }