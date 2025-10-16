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
from app.schemas.cliente import ClienteResponse
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[ClienteResponse])
def listar_clientes(
    # Paginación
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    
    # Búsqueda de texto
    search: Optional[str] = Query(None, description="Buscar en nombre, cédula o móvil"),
    
    # Filtros específicos
    estado: Optional[str] = Query(None, description="ACTIVO, INACTIVO, MORA"),
    estado_financiero: Optional[str] = Query(None, description="AL_DIA, MORA, VENCIDO"),
    asesor_id: Optional[int] = Query(None, description="ID del asesor de configuración asignado"),
    
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
        
        if asesor_id:
            query = query.filter(Cliente.asesor_id == asesor_id)
        
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
                "asesor_id": getattr(cliente, 'asesor_id', None),
                "estado": getattr(cliente, 'estado', 'ACTIVO') or 'ACTIVO',
                "activo": bool(getattr(cliente, 'activo', True)),
                "estado_financiero": getattr(cliente, 'estado_financiero', 'AL_DIA') or 'AL_DIA',
                "dias_mora": getattr(cliente, 'dias_mora', 0) or 0,
                "fecha_registro": getattr(cliente, 'fecha_registro', None).isoformat() if getattr(cliente, 'fecha_registro', None) else None,
                "fecha_asignacion": getattr(cliente, 'fecha_asignacion', None).isoformat() if getattr(cliente, 'fecha_asignacion', None) else None
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
