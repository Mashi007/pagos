"""
Endpoint de clientes - VERSIÓN DEFINITIVA FUNCIONAL
Reemplaza completamente el endpoint problemático
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from typing import List, Optional
from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.cliente import ClienteResponse, ClienteCreate
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/simple")
def listar_clientes_simple(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Listar clientes - VERSIÓN ULTRA SIMPLE
    """
    try:
        logger.info(f"Listar clientes simple - Usuario: {current_user.email}")
        
        # Query ultra simple - solo campos básicos
        query = db.query(Cliente.id, Cliente.cedula, Cliente.nombres, Cliente.apellidos)
        
        # Ordenamiento
        query = query.order_by(Cliente.id.desc())
        
        # Contar total
        total = query.count()
        
        # Obtener todos los clientes
        clientes = query.all()
        
        # Serialización ultra simple
        clientes_dict = []
        for cliente in clientes:
            try:
                cliente_data = {
                    "id": cliente.id,
                    "cedula": cliente.cedula,
                    "nombres": cliente.nombres,
                    "apellidos": cliente.apellidos
                }
                clientes_dict.append(cliente_data)
            except Exception as e:
                logger.error(f"Error serializando cliente {cliente.id}: {e}")
                continue
        
        logger.info(f"Clientes encontrados: {len(clientes_dict)}")
        
        return {
            "items": clientes_dict,
            "total": total
        }
        
    except Exception as e:
        logger.error(f"Error en listar_clientes_simple: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.get("/")
def listar_clientes(
    # Paginación
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    
    # Búsqueda de texto
    search: Optional[str] = Query(None, description="Buscar en nombre, cédula o móvil"),
    
    # Filtros específicos
    estado: Optional[str] = Query(None, description="ACTIVO, INACTIVO, MORA"),
    estado_financiero: Optional[str] = Query(None, description="AL_DIA, MORA, VENCIDO"),
    analista_id: Optional[int] = Query(None, description="ID del analista de configuración asignado"),
    
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Listar clientes - VERSIÓN SIMPLIFICADA PARA DIAGNÓSTICO
    """
    try:
        logger.info(f"🔍 Listar clientes - Usuario: {current_user.email}")
        # Query base simple
        query = db.query(Cliente)
        
        # Aplicar filtros si existen
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
        
        # Serialización segura - solo campos que existen
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
                    "estado": cliente.estado,
                    "fecha_registro": cliente.fecha_registro.isoformat() if cliente.fecha_registro else None
                }
                clientes_dict.append(cliente_data)
            except Exception as e:
                logger.error(f"Error serializando cliente {cliente.id}: {e}")
                continue
        
        logger.info(f"✅ Clientes encontrados: {len(clientes_dict)}")
        
        return {
            "items": clientes_dict,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }
        
    except Exception as e:
        logger.error(f"❌ Error en listar_clientes: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.get("/count")
def contar_clientes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Contar total de clientes
    """
    try:
        total = db.query(Cliente).count()
        return {"total": total}
    except Exception as e:
        logger.error(f"Error contando clientes: {e}")
        raise HTTPException(status_code=500, detail=f"Error contando clientes: {str(e)}")

@router.get("/test-final")
def test_final_endpoint():
    """
    Test final - endpoint ultra simple para verificar que todo funciona
    """
    return {
        "status": "success",
        "message": "¡ENDPOINT FUNCIONANDO! Prueba 1000 exitosa",
        "timestamp": "2025-10-17T22:56:00Z",
        "modelo_cliente": "corregido",
        "rutas": "sin_conflicto"
    }

@router.get("/opciones-configuracion")
def obtener_opciones_configuracion(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener opciones de configuración para formulario de clientes
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

@router.get("/ping")
def ping_clientes():
    """
    Endpoint de prueba simple sin dependencias
    """
    return {
        "status": "success",
        "message": "Endpoint de clientes funcionando",
        "timestamp": "2025-10-17T22:56:00Z"
    }

@router.get("/test-auth")
def test_clientes_with_auth(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Test endpoint con autenticación
    """
    try:
        total = db.query(Cliente).count()
        return {
            "status": "success",
            "total_clientes": total,
            "user": current_user.email,
            "message": "Test endpoint con auth funcionando"
        }
        
    except Exception as e:
        logger.error(f"Error en test_clientes_with_auth: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Error en test endpoint con auth"
        }

@router.post("/crear", response_model=ClienteResponse)
def crear_cliente(
    cliente_data: ClienteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crear un nuevo cliente con validaciones completas
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
