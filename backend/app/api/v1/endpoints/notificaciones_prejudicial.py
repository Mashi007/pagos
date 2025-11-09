"""
Endpoints para Notificaciones Prejudiciales
Clientes con 3 o más cuotas atrasadas
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
    - Clientes con 3 o más cuotas atrasadas
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
            logger.info(
                f"🔍 [NotificacionesPrejudicial] Filtrado por estado '{estado}': {resultados_antes} -> {len(resultados)}"
            )

        # Convertir a response models
        try:
            items = []
            for r in resultados:
                try:
                    # Asegurar que todos los campos requeridos estén presentes
                    fecha_vencimiento = r.get("fecha_vencimiento") or ""
                    # Convertir a string si es una fecha
                    if fecha_vencimiento and not isinstance(fecha_vencimiento, str):
                        if hasattr(fecha_vencimiento, 'isoformat'):
                            fecha_vencimiento = fecha_vencimiento.isoformat()
                        else:
                            fecha_vencimiento = str(fecha_vencimiento)
                    elif not fecha_vencimiento:
                        fecha_vencimiento = ""
                    
                    item_data = {
                        "prestamo_id": int(r.get("prestamo_id", 0)),
                        "cliente_id": int(r.get("cliente_id", 0)),
                        "nombre": str(r.get("nombre", "")),
                        "cedula": str(r.get("cedula", "")),
                        "modelo_vehiculo": str(r.get("modelo_vehiculo", "")),
                        "correo": str(r.get("correo", "")),
                        "telefono": str(r.get("telefono", "")),
                        "fecha_vencimiento": fecha_vencimiento,
                        "numero_cuota": int(r.get("numero_cuota", 0)),
                        "monto_cuota": float(r.get("monto_cuota", 0.0)),
                        "total_cuotas_atrasadas": int(r.get("total_cuotas_atrasadas", 0)),
                        "estado": str(r.get("estado", "PENDIENTE")),
                    }
                    items.append(NotificacionPrejudicialResponse(**item_data))
                except Exception as e:
                    logger.warning(f"⚠️ [NotificacionesPrejudicial] Error convirtiendo item: {e}, datos: {r}")
                    continue

            logger.info(f"✅ [NotificacionesPrejudicial] Respuesta preparada: {len(items)} items")
            return NotificacionesPrejudicialesListResponse(
                items=items,
                total=len(items),
            )
        except Exception as conversion_error:
            logger.error(f"❌ [NotificacionesPrejudicial] Error en conversión: {conversion_error}", exc_info=True)
            # Devolver respuesta vacía en lugar de fallar
            return NotificacionesPrejudicialesListResponse(
                items=[],
                total=0,
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
