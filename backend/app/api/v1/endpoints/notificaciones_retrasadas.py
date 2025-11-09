"""
Endpoints para Notificaciones de Pagos Retrasados
Clientes con cuotas atrasadas (1, 3, 5 días atrasado)
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.notificaciones_retrasadas_service import NotificacionesRetrasadasService

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# SCHEMAS
# ============================================


class NotificacionRetrasadaResponse(BaseModel):
    """Schema para respuesta de notificación retrasada"""

    prestamo_id: int
    cliente_id: int
    nombre: str
    cedula: str
    modelo_vehiculo: str
    correo: str
    telefono: str
    dias_atrasado: int
    fecha_vencimiento: str
    numero_cuota: int
    monto_cuota: float
    estado: str  # ENVIADA, PENDIENTE, FALLIDA

    class Config:
        from_attributes = True


class NotificacionesRetrasadasListResponse(BaseModel):
    """Schema para lista de notificaciones retrasadas"""

    items: List[NotificacionRetrasadaResponse]
    total: int
    dias_1: int
    dias_3: int
    dias_5: int


# ============================================
# ENDPOINTS
# ============================================


@router.get("/", response_model=NotificacionesRetrasadasListResponse)
def listar_notificaciones_retrasadas(
    estado: Optional[str] = Query(None, description="Filtrar por estado: ENVIADA, PENDIENTE, FALLIDA"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Listar notificaciones de pagos retrasados

    - Préstamos con estado = 'APROBADO'
    - Cuotas que vencieron hace 1, 3 o 5 días
    - Cuotas con estado ATRASADO o PENDIENTE
    - Filtro opcional por estado de envío (ENVIADA, PENDIENTE, FALLIDA)
    """
    try:
        logger.info(f"📥 [NotificacionesRetrasadas] Solicitud GET / - estado={estado}")

        # Verificar conexión a BD
        try:
            from sqlalchemy import text

            db.execute(text("SELECT 1"))
            logger.debug("✅ [NotificacionesRetrasadas] Conexión a BD verificada")
        except Exception as e:
            logger.error(f"❌ [NotificacionesRetrasadas] Error de conexión a BD: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error de conexión a base de datos: {str(e)}")

        service = NotificacionesRetrasadasService(db)
        resultados = service.obtener_notificaciones_retrasadas_cached()
        logger.info(f"📊 [NotificacionesRetrasadas] Resultados calculados: {len(resultados)} registros")

        # Filtrar por estado si se proporciona
        if estado:
            resultados_antes = len(resultados)
            resultados = [r for r in resultados if r.get("estado") == estado]
            logger.info(
                f"🔍 [NotificacionesRetrasadas] Filtrado por estado '{estado}': {resultados_antes} -> {len(resultados)}"
            )

        # Contar por categorías
        dias_1 = len([r for r in resultados if r["dias_atrasado"] == 1])
        dias_3 = len([r for r in resultados if r["dias_atrasado"] == 3])
        dias_5 = len([r for r in resultados if r["dias_atrasado"] == 5])

        # Convertir a response models
        items = [NotificacionRetrasadaResponse(**r) for r in resultados]

        return NotificacionesRetrasadasListResponse(
            items=items,
            total=len(items),
            dias_1=dias_1,
            dias_3=dias_3,
            dias_5=dias_5,
        )

    except Exception as e:
        logger.error(f"Error listando notificaciones retrasadas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.post("/calcular")
def calcular_notificaciones_retrasadas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint para calcular notificaciones retrasadas manualmente
    """
    try:
        service = NotificacionesRetrasadasService(db)
        resultados = service.calcular_notificaciones_retrasadas()

        return {
            "mensaje": "Notificaciones retrasadas calculadas exitosamente",
            "total": len(resultados),
            "dias_1": len([r for r in resultados if r["dias_atrasado"] == 1]),
            "dias_3": len([r for r in resultados if r["dias_atrasado"] == 3]),
            "dias_5": len([r for r in resultados if r["dias_atrasado"] == 5]),
        }

    except Exception as e:
        logger.error(f"Error calculando notificaciones retrasadas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")
