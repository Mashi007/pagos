"""
Endpoints para Notificaciones del Día de Pago
Clientes con cuotas que vencen HOY
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.notificaciones_dia_pago_service import NotificacionesDiaPagoService

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# SCHEMAS
# ============================================


class NotificacionDiaPagoResponse(BaseModel):
    """Schema para respuesta de notificación del día de pago"""

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
    estado: str  # ENVIADA, PENDIENTE, FALLIDA

    class Config:
        from_attributes = True


class NotificacionesDiaPagoListResponse(BaseModel):
    """Schema para lista de notificaciones del día de pago"""

    items: List[NotificacionDiaPagoResponse]
    total: int


# ============================================
# ENDPOINTS
# ============================================


@router.get("/", response_model=NotificacionesDiaPagoListResponse)
def listar_notificaciones_dia_pago(
    estado: Optional[str] = Query(None, description="Filtrar por estado: ENVIADA, PENDIENTE, FALLIDA"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Listar notificaciones del día de pago

    - Préstamos con estado = 'APROBADO'
    - Cuotas con fecha_vencimiento = HOY
    - Cuotas con estado PENDIENTE o ATRASADO
    - Ordenado alfabéticamente por nombre del cliente
    - Filtro opcional por estado de envío (ENVIADA, PENDIENTE, FALLIDA)
    """
    try:
        logger.info(f"📥 [NotificacionesDiaPago] Solicitud GET / - estado={estado}")

        # Verificar conexión a BD
        try:
            from sqlalchemy import text

            db.execute(text("SELECT 1"))
            logger.debug("✅ [NotificacionesDiaPago] Conexión a BD verificada")
        except Exception as e:
            logger.error(f"❌ [NotificacionesDiaPago] Error de conexión a BD: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error de conexión a base de datos: {str(e)}")

        service = NotificacionesDiaPagoService(db)
        resultados = service.obtener_notificaciones_dia_pago_cached()
        logger.info(f"📊 [NotificacionesDiaPago] Resultados calculados: {len(resultados)} registros")

        # Filtrar por estado si se proporciona
        if estado:
            resultados_antes = len(resultados)
            resultados = [r for r in resultados if r.get("estado") == estado]
            logger.info(f"🔍 [NotificacionesDiaPago] Filtrado por estado '{estado}': {resultados_antes} -> {len(resultados)}")

        # Convertir a response models
        items = [NotificacionDiaPagoResponse(**r) for r in resultados]

        return NotificacionesDiaPagoListResponse(
            items=items,
            total=len(items),
        )

    except Exception as e:
        logger.error(f"Error listando notificaciones del día de pago: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.post("/calcular")
def calcular_notificaciones_dia_pago(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint para calcular notificaciones del día de pago manualmente
    """
    try:
        service = NotificacionesDiaPagoService(db)
        resultados = service.calcular_notificaciones_dia_pago()

        return {
            "mensaje": "Notificaciones del día de pago calculadas exitosamente",
            "total": len(resultados),
        }

    except Exception as e:
        logger.error(f"Error calculando notificaciones del día de pago: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")
