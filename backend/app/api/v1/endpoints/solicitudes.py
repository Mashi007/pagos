import logging
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.aprobacion import Aprobacion
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# SCHEMAS PARA SOLICITUDES
# ============================================


class SolicitudAprobacionCompleta(BaseModel):
    """Schema completo para crear solicitud de aprobación"""

    tipo_solicitud: str = Field(
        ...,
        description="MODIFICAR_PAGO, ANULAR_PAGO, EDITAR_CLIENTE, MODIFICAR_AMORTIZACION",
    )
    entidad_tipo: str = Field(..., description="cliente, pago, prestamo")
    entidad_id: int = Field(..., description="ID de la entidad a modificar")
    justificacion: str = Field(..., min_length=10, max_length=1000, description="Justificación detallada")
    prioridad: str = Field(default="NORMAL", description="BAJA, NORMAL, ALTA, URGENTE")
    fecha_limite: Optional[date] = Field(None, description="Fecha límite para respuesta")

    class Config:
        json_schema_extra = {
            "example": {
                "tipo_solicitud": "MODIFICAR_PAGO",
                "entidad_tipo": "pago",
                "entidad_id": 123,
                "justificacion": "Error en el registro del pago",
                "prioridad": "ALTA",
                "fecha_limite": "2025-10-15",
            }
        }


class FormularioModificarPago(BaseModel):
    """Formulario específico para modificar pago"""

    pago_id: int = Field(..., description="ID del pago a modificar")
    motivo_modificacion: str = Field(..., description="ERROR_REGISTRO, CAMBIO_CLIENTE, AJUSTE_MONTO, OTRO")
    nuevo_monto: Optional[float] = Field(None, gt=0, description="Nuevo monto del pago")
    nuevo_metodo_pago: Optional[str] = Field(None, description="EFECTIVO, TRANSFERENCIA, TARJETA, CHEQUE")
    nueva_fecha_pago: Optional[date] = Field(None, description="Nueva fecha del pago")


class FormularioAnularPago(BaseModel):
    """Formulario específico para anular pago"""

    pago_id: int = Field(..., description="ID del pago a anular")
    motivo_anulacion: str = Field(..., description="ERROR_REGISTRO, DUPLICADO, FRAUDE, OTRO")
    devolver_dinero: bool = Field(default=True, description="Si se debe devolver el dinero")


class FormularioEditarCliente(BaseModel):
    """Formulario específico para editar cliente"""

    cliente_id: int = Field(..., description="ID del cliente a editar")
    campos_modificar: Dict[str, Any] = Field(..., description="Campos específicos a modificar")
    motivo_edicion: str = Field(..., description="ACTUALIZACION_DATOS, CORRECCION_ERROR, OTRO")


class FormularioModificarAmortizacion(BaseModel):
    """Formulario específico para modificar amortización"""

    prestamo_id: int = Field(..., description="ID del préstamo")
    tipo_modificacion: str = Field(..., description="CAMBIO_PLAZO, AJUSTE_TASA, REESTRUCTURACION")
    nuevos_parametros: Dict[str, Any] = Field(..., description="Nuevos parámetros de la amortización")


class SolicitudResponse(BaseModel):
    """Response para solicitudes"""

    id: int
    tipo_solicitud: str
    entidad_tipo: str
    entidad_id: int
    justificacion: str
    prioridad: str
    estado: str
    fecha_creacion: date
    fecha_limite: Optional[date]
    solicitante_id: int
    revisor_id: Optional[int]
    fecha_revision: Optional[date]
    comentarios_revisor: Optional[str]

    class Config:
        from_attributes = True


# ============================================
# ENDPOINTS PARA SOLICITUDES
# ============================================


@router.post("/crear", response_model=SolicitudResponse)
async def crear_solicitud(
    solicitud: SolicitudAprobacionCompleta,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crear una nueva solicitud de aprobación"""
    try:
        logger.info(f"Creando solicitud - Usuario: {current_user.email}")

        # Crear la solicitud
        nueva_solicitud = Aprobacion(
            tipo_solicitud=solicitud.tipo_solicitud,
            entidad_tipo=solicitud.entidad_tipo,
            entidad_id=solicitud.entidad_id,
            justificacion=solicitud.justificacion,
            prioridad=solicitud.prioridad,
            fecha_limite=solicitud.fecha_limite,
            solicitante_id=current_user.id,
            estado="PENDIENTE",
        )

        db.add(nueva_solicitud)
        db.commit()
        db.refresh(nueva_solicitud)

        return nueva_solicitud

    except Exception as e:
        db.rollback()
        logger.error(f"Error creando solicitud: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get("/")
def listar_solicitudes(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Registros por página"),
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Listar solicitudes con filtros y paginación
    """
    from app.utils.pagination import calculate_pagination_params, create_paginated_response

    try:
        # Calcular paginación
        skip, limit = calculate_pagination_params(page=page, per_page=per_page, max_per_page=100)

        # Query base
        query = db.query(Aprobacion)

        if estado:
            query = query.filter(Aprobacion.estado == estado)

        # Contar total
        total = query.count()

        # Aplicar paginación con ordenamiento
        solicitudes = query.order_by(Aprobacion.created_at.desc()).offset(skip).limit(limit).all()

        # Retornar respuesta paginada
        return create_paginated_response(items=solicitudes, total=total, page=page, page_size=limit)

    except Exception as e:
        logger.error(f"Error listando solicitudes: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get("/{solicitud_id}", response_model=SolicitudResponse)
def obtener_solicitud(
    solicitud_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener solicitud específica"""
    try:
        solicitud = db.query(Aprobacion).filter(Aprobacion.id == solicitud_id).first()

        if not solicitud:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")

        return solicitud

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo solicitud: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.put("/{solicitud_id}/aprobar")
def aprobar_solicitud(
    solicitud_id: int,
    comentarios: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aprobar una solicitud"""
    try:
        solicitud = db.query(Aprobacion).filter(Aprobacion.id == solicitud_id).first()

        if not solicitud:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")

        if solicitud.estado != "PENDIENTE":
            raise HTTPException(status_code=400, detail="La solicitud ya fue procesada")

        # Actualizar estado
        solicitud.estado = "APROBADA"
        solicitud.revisor_id = int(current_user.id)
        solicitud.comentarios_revisor = comentarios

        db.commit()

        return {"message": "Solicitud aprobada exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error aprobando solicitud: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.put("/{solicitud_id}/rechazar")
def rechazar_solicitud(
    solicitud_id: int,
    comentarios: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rechazar una solicitud"""
    try:
        solicitud = db.query(Aprobacion).filter(Aprobacion.id == solicitud_id).first()

        if not solicitud:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")

        if solicitud.estado != "PENDIENTE":
            raise HTTPException(status_code=400, detail="La solicitud ya fue procesada")

        # Actualizar estado
        solicitud.estado = "RECHAZADA"
        solicitud.revisor_id = int(current_user.id)
        solicitud.comentarios_revisor = comentarios

        db.commit()

        return {"message": "Solicitud rechazada exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error rechazando solicitud: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get("/pendientes/count")
def contar_solicitudes_pendientes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Contar solicitudes pendientes"""
    try:
        count = db.query(Aprobacion).filter(Aprobacion.estado == "PENDIENTE").count()
        return {"count": count}

    except Exception as e:
        logger.error(f"Error contando solicitudes: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")
