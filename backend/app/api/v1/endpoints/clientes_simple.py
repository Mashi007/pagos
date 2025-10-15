"""
Endpoint simplificado para clientes - SOLUCIÓN TEMPORAL AL ERROR 503
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.user import User
from app.api.deps import get_current_user
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/simple")
def listar_clientes_simple(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100, description="Elementos por página")
):
    """
    Listar clientes - VERSIÓN ULTRA SIMPLE PARA EVITAR ERROR 503
    """
    try:
        # Query ultra simple sin relaciones
        clientes = db.query(Cliente).limit(limit).all()
        
        # Serialización ultra simple
        clientes_dict = []
        for cliente in clientes:
            try:
                cliente_data = {
                    "id": cliente.id,
                    "cedula": getattr(cliente, 'cedula', '') or '',
                    "nombres": getattr(cliente, 'nombres', '') or '',
                    "apellidos": getattr(cliente, 'apellidos', '') or '',
                    "telefono": getattr(cliente, 'telefono', '') or '',
                    "email": getattr(cliente, 'email', '') or '',
                    "estado": getattr(cliente, 'estado', 'ACTIVO') or 'ACTIVO',
                    "activo": bool(getattr(cliente, 'activo', True))
                }
                clientes_dict.append(cliente_data)
            except Exception as e:
                logger.error(f"Error serializando cliente {cliente.id}: {e}")
                clientes_dict.append({
                    "id": cliente.id,
                    "error": f"Error serializando: {str(e)}"
                })
        
        return {
            "status": "success",
            "total": len(clientes_dict),
            "clientes": clientes_dict,
            "message": "Clientes obtenidos correctamente"
        }
        
    except Exception as e:
        logger.error(f"Error en listar_clientes_simple: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

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
        return {
            "status": "success",
            "total_clientes": total,
            "message": "Conteo exitoso"
        }
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
        # Query simple
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
