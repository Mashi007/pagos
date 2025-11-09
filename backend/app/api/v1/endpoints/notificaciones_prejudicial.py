"""
Endpoints para Notificaciones Prejudiciales
Clientes con 2 o más cuotas atrasadas
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.notificaciones_prejudicial_service import NotificacionesPrejudicialService

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# SCHEMAS
# ============================================


class NotificacionPrejudicialResponse(BaseModel):
    """Schema para respuesta de notificación prejudicial"""

    prestamo_id: int
    cliente_id: int
    nombre: str
    cedula: str
    modelo_vehiculo: str
    correo: str
    telefono: str
    fecha_vencimiento: str
    numero_cuota: int
    monto_cuota: float
    total_cuotas_atrasadas: int
    estado: str  # ENVIADA, PENDIENTE, FALLIDA

    class Config:
        from_attributes = True


class NotificacionesPrejudicialesListResponse(BaseModel):
    """Schema para lista de notificaciones prejudiciales"""

    items: List[NotificacionPrejudicialResponse]
    total: int


# ============================================
# ENDPOINTS
# ============================================


@router.get("/", response_model=NotificacionesPrejudicialesListResponse)
def listar_notificaciones_prejudiciales(
    estado: Optional[str] = Query(None, description="Filtrar por estado: ENVIADA, PENDIENTE, FALLIDA"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Listar notificaciones prejudiciales

    - Préstamos con estado = 'APROBADO'
    - Clientes con 2 o más cuotas atrasadas
    - Cuotas con estado ATRASADO
    - Ordenado por fecha de vencimiento más antigua primero
    - Filtro opcional por estado de envío (ENVIADA, PENDIENTE, FALLIDA)
    """
    try:
        logger.info(f"📥 [NotificacionesPrejudicial] Solicitud GET / - estado={estado}")

        # Verificar conexión a BD
        try:
            from sqlalchemy import text

            db.execute(text("SELECT 1"))
            logger.debug("✅ [NotificacionesPrejudicial] Conexión a BD verificada")
        except Exception as e:
            logger.error(f"❌ [NotificacionesPrejudicial] Error de conexión a BD: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error de conexión a base de datos: {str(e)}")

        service = NotificacionesPrejudicialService(db)
        resultados = service.obtener_notificaciones_prejudiciales_cached()
        logger.info(f"📊 [NotificacionesPrejudicial] Resultados calculados: {len(resultados)} registros")

        # Filtrar por estado si se proporciona
        if estado:
            resultados_antes = len(resultados)
            resultados = [r for r in resultados if r.get("estado") == estado]
            logger.info(f"🔍 [NotificacionesPrejudicial] Filtrado por estado '{estado}': {resultados_antes} -> {len(resultados)}")

        # Convertir a response models
        items = [NotificacionPrejudicialResponse(**r) for r in resultados]

        return NotificacionesPrejudicialesListResponse(
            items=items,
            total=len(items),
        )

    except Exception as e:
        logger.error(f"Error listando notificaciones prejudiciales: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.post("/calcular")
def calcular_notificaciones_prejudiciales(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint para calcular notificaciones prejudiciales manualmente
    """
    try:
        service = NotificacionesPrejudicialService(db)
        resultados = service.calcular_notificaciones_prejudiciales()

        return {
            "mensaje": "Notificaciones prejudiciales calculadas exitosamente",
            "total": len(resultados),
        }

    except Exception as e:
        logger.error(f"Error calculando notificaciones prejudiciales: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

