"""
Endpoints para Notificaciones Previas
Clientes con cuotas próximas a vencer (5, 3, 1 días antes)
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.notificaciones_previas_service import NotificacionesPreviasService

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# SCHEMAS
# ============================================


class NotificacionPreviaResponse(BaseModel):
    """Schema para respuesta de notificación previa"""
    
    prestamo_id: int
    cliente_id: int
    nombre: str
    cedula: str
    modelo_vehiculo: str
    correo: str
    telefono: str
    dias_antes_vencimiento: int
    fecha_vencimiento: str
    numero_cuota: int
    monto_cuota: float
    estado: str  # ENVIADA, PENDIENTE, FALLIDA

    class Config:
        from_attributes = True


class NotificacionesPreviasListResponse(BaseModel):
    """Schema para lista de notificaciones previas"""

    items: List[NotificacionPreviaResponse]
    total: int
    dias_5: int
    dias_3: int
    dias_1: int


# ============================================
# ENDPOINTS
# ============================================


@router.get("/", response_model=NotificacionesPreviasListResponse)
def listar_notificaciones_previas(
    estado: Optional[str] = Query(None, description="Filtrar por estado: ENVIADA, PENDIENTE, FALLIDA"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Listar notificaciones previas de clientes con cuotas próximas a vencer
    
    - Clientes SIN cuotas atrasadas
    - Cuotas que vencen en 5, 3 o 1 día
    - Se actualiza cada vez que se cambia de pestaña
    - Cálculo principal se hace a las 2 AM (scheduler)
    - Filtro opcional por estado de envío (ENVIADA, PENDIENTE, FALLIDA)
    """
    try:
        service = NotificacionesPreviasService(db)
        resultados = service.obtener_notificaciones_previas_cached()
        
        # Filtrar por estado si se proporciona
        if estado:
            resultados = [r for r in resultados if r.get("estado") == estado]
        
        # Contar por categorías
        dias_5 = len([r for r in resultados if r["dias_antes_vencimiento"] == 5])
        dias_3 = len([r for r in resultados if r["dias_antes_vencimiento"] == 3])
        dias_1 = len([r for r in resultados if r["dias_antes_vencimiento"] == 1])
        
        # Convertir a response models
        items = [NotificacionPreviaResponse(**r) for r in resultados]
        
        return NotificacionesPreviasListResponse(
            items=items,
            total=len(items),
            dias_5=dias_5,
            dias_3=dias_3,
            dias_1=dias_1,
        )
        
    except Exception as e:
        logger.error(f"Error listando notificaciones previas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.post("/calcular")
def calcular_notificaciones_previas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint para calcular notificaciones previas manualmente
    Normalmente se ejecuta automáticamente a las 2 AM via scheduler
    """
    try:
        service = NotificacionesPreviasService(db)
        resultados = service.calcular_notificaciones_previas()

        return {
            "mensaje": "Notificaciones previas calculadas exitosamente",
            "total": len(resultados),
            "dias_5": len([r for r in resultados if r["dias_antes_vencimiento"] == 5]),
            "dias_3": len([r for r in resultados if r["dias_antes_vencimiento"] == 3]),
            "dias_1": len([r for r in resultados if r["dias_antes_vencimiento"] == 1]),
        }

    except Exception as e:
        logger.error(f"Error calculando notificaciones previas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")
