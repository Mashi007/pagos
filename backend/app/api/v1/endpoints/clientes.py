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
    asesor_config_id: Optional[int] = Query(None, description="ID del asesor de configuración asignado"),
    
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Listar clientes - VERSIÓN DEFINITIVA FUNCIONAL
    """
    try:
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
        
        if estado_financiero:
            query = query.filter(Cliente.estado_financiero == estado_financiero)
        
        if asesor_config_id:
            query = query.filter(Cliente.asesor_config_id == asesor_config_id)
        
        # Ordenamiento
        query = query.order_by(Cliente.id.desc())
        
        # Contar total
        total = query.count()
        
        # Paginación
        offset = (page - 1) * per_page
        clientes = query.offset(offset).limit(per_page).all()
        
        # Serialización segura - usar Pydantic para consistencia
        clientes_dict = []
        for cliente in clientes:
            try:
                # Usar Pydantic para serialización consistente
                cliente_response = ClienteResponse.model_validate(cliente)
                clientes_dict.append(cliente_response.model_dump())
            except Exception as e:
                # Fallback a serialización manual si Pydantic falla
                logger.warning(f"Error serializando cliente {cliente.id}: {e}")
                cliente_data = {
                    "id": cliente.id,
                    "cedula": getattr(cliente, 'cedula', '') or '',
                    "nombres": getattr(cliente, 'nombres', '') or '',
                    "apellidos": getattr(cliente, 'apellidos', '') or '',
                    "telefono": getattr(cliente, 'telefono', '') or '',
                    "email": getattr(cliente, 'email', '') or '',
                    "direccion": getattr(cliente, 'direccion', '') or '',
                    "ocupacion": getattr(cliente, 'ocupacion', '') or '',
                    "modelo_vehiculo": getattr(cliente, 'modelo_vehiculo', '') or '',
                    "marca_vehiculo": getattr(cliente, 'marca_vehiculo', '') or '',
                    "anio_vehiculo": getattr(cliente, 'anio_vehiculo', None),
                    "color_vehiculo": getattr(cliente, 'color_vehiculo', '') or '',
                    "concesionario": getattr(cliente, 'concesionario', '') or '',
                    "total_financiamiento": float(getattr(cliente, 'total_financiamiento', 0) or 0),
                    "cuota_inicial": float(getattr(cliente, 'cuota_inicial', 0) or 0),
                    "monto_financiado": float(getattr(cliente, 'monto_financiado', 0) or 0),
                    "modalidad_pago": getattr(cliente, 'modalidad_pago', 'MENSUAL') or 'MENSUAL',
                    "numero_amortizaciones": getattr(cliente, 'numero_amortizaciones', 0) or 0,
                    "asesor_config_id": getattr(cliente, 'asesor_config_id', None),
                    "estado": getattr(cliente, 'estado', 'ACTIVO') or 'ACTIVO',
                    "activo": bool(getattr(cliente, 'activo', True)),
                    "estado_financiero": getattr(cliente, 'estado_financiero', 'AL_DIA') or 'AL_DIA',
                    "dias_mora": getattr(cliente, 'dias_mora', 0) or 0,
                    "fecha_registro": cliente.fecha_registro.isoformat() if cliente.fecha_registro else None,
                    "fecha_asignacion": cliente.fecha_asignacion.isoformat() if cliente.fecha_asignacion else None
                }
                clientes_dict.append(cliente_data)
        
        return {
            "clientes": clientes_dict,
            "total": total,
            "page": page,
            "limit": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }
        
    except Exception as e:
        logger.error(f"Error en listar_clientes: {e}")
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

@router.get("/test")
def test_clientes_endpoint(
    db: Session = Depends(get_db)
):
    """
    Test endpoint sin autenticación
    """
    try:
        total = db.query(Cliente).count()
        sample = db.query(Cliente).limit(3).all()
        
        sample_data = []
        for cliente in sample:
            sample_data.append({
                "id": cliente.id,
                "cedula": getattr(cliente, 'cedula', ''),
                "nombres": getattr(cliente, 'nombres', '')
            })
        
        return {
            "status": "success",
            "total_clientes": total,
            "sample": sample_data,
            "message": "Test endpoint funcionando"
        }
        
    except Exception as e:
        logger.error(f"Error en test_clientes_endpoint: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Error en test endpoint"
        }

@router.post("", response_model=ClienteResponse)
def crear_cliente(
    cliente_data: ClienteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crear un nuevo cliente
    """
    try:
        # Verificar que no exista un cliente con la misma cédula
        existing = db.query(Cliente).filter(Cliente.cedula == cliente_data.cedula).first()
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe un cliente con esta cédula")
        
        # Crear nuevo cliente - SOLO campos que existen en el modelo
        cliente_dict = cliente_data.model_dump()
        
        # Filtrar campos que NO existen en el modelo Cliente
        campos_validos = {
            'cedula', 'nombres', 'apellidos', 'telefono', 'email', 'direccion',
            'fecha_nacimiento', 'ocupacion', 'modelo_vehiculo', 'marca_vehiculo',
            'anio_vehiculo', 'color_vehiculo', 'chasis', 'motor', 'concesionario',
            'vendedor_concesionario', 'total_financiamiento', 'cuota_inicial',
            'fecha_entrega', 'numero_amortizaciones', 'modalidad_pago',
            'asesor_config_id', 'notas'
        }
        
        # Crear diccionario solo con campos válidos
        cliente_dict_filtrado = {k: v for k, v in cliente_dict.items() if k in campos_validos}
        
        # Calcular monto_financiado si no se proporciona
        if 'total_financiamiento' in cliente_dict_filtrado and 'cuota_inicial' in cliente_dict_filtrado:
            total = cliente_dict_filtrado.get('total_financiamiento', 0) or 0
            inicial = cliente_dict_filtrado.get('cuota_inicial', 0) or 0
            cliente_dict_filtrado['monto_financiado'] = total - inicial
        
        cliente = Cliente(**cliente_dict_filtrado)
        
        db.add(cliente)
        db.commit()
        db.refresh(cliente)
        
        return ClienteResponse.model_validate(cliente)
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando cliente: {e}")
        raise HTTPException(status_code=500, detail=f"Error creando cliente: {str(e)}")
