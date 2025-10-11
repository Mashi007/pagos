# backend/app/api/v1/endpoints/aprobaciones.py
"""
Endpoint para gestión de aprobaciones de préstamos.
Sistema de workflow con múltiples niveles de aprobación.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.db.session import get_db
from app.models.aprobacion import Aprobacion, EstadoAprobacion, NivelAprobacion
from app.models.prestamo import Prestamo, EstadoPrestamo
from app.models.user import User
from app.core.security import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Schemas
class AprobacionCreate(BaseModel):
    prestamo_id: int
    nivel: str  # GERENTE, DIRECTOR, COMITE
    comentarios: Optional[str] = None

class AprobacionResponse(BaseModel):
    id: int
    prestamo_id: int
    aprobador_id: int
    nivel: str
    estado: str
    comentarios: Optional[str]
    fecha_aprobacion: Optional[datetime]
    creada_en: datetime
    
    class Config:
        from_attributes = True

class AprobarRequest(BaseModel):
    aprobacion_id: int
    comentarios: Optional[str] = None

class RechazarRequest(BaseModel):
    aprobacion_id: int
    motivo: str


@router.post("/solicitar", response_model=AprobacionResponse)
def solicitar_aprobacion(
    solicitud: AprobacionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Solicitar aprobación de un préstamo.
    """
    # Verificar que el préstamo existe
    prestamo = db.query(Prestamo).filter(Prestamo.id == solicitud.prestamo_id).first()
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    
    # Verificar que no exista ya una aprobación pendiente para este nivel
    aprobacion_existente = db.query(Aprobacion).filter(
        and_(
            Aprobacion.prestamo_id == solicitud.prestamo_id,
            Aprobacion.nivel == solicitud.nivel,
            Aprobacion.estado == EstadoAprobacion.PENDIENTE.value
        )
    ).first()
    
    if aprobacion_existente:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe una aprobación pendiente en nivel {solicitud.nivel}"
        )
    
    # Crear solicitud de aprobación
    nueva_aprobacion = Aprobacion(
        prestamo_id=solicitud.prestamo_id,
        solicitante_id=current_user.id,
        nivel=solicitud.nivel,
        estado=EstadoAprobacion.PENDIENTE.value,
        comentarios=solicitud.comentarios
    )
    
    db.add(nueva_aprobacion)
    
    # Actualizar estado del préstamo
    prestamo.estado = EstadoPrestamo.EN_APROBACION.value
    
    db.commit()
    db.refresh(nueva_aprobacion)
    
    logger.info(f"Aprobación {nueva_aprobacion.id} solicitada para préstamo {prestamo.id} en nivel {solicitud.nivel}")
    return nueva_aprobacion


@router.post("/aprobar")
def aprobar_solicitud(
    request: AprobarRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Aprobar una solicitud de préstamo.
    """
    # Obtener aprobación
    aprobacion = db.query(Aprobacion).filter(Aprobacion.id == request.aprobacion_id).first()
    if not aprobacion:
        raise HTTPException(status_code=404, detail="Aprobación no encontrada")
    
    # Verificar que esté pendiente
    if aprobacion.estado != EstadoAprobacion.PENDIENTE.value:
        raise HTTPException(
            status_code=400,
            detail=f"La aprobación ya fue {aprobacion.estado}"
        )
    
    # Verificar permisos según nivel
    if not _verificar_permiso_aprobacion(current_user, aprobacion.nivel):
        raise HTTPException(
            status_code=403,
            detail="No tiene permisos para aprobar en este nivel"
        )
    
    # Aprobar
    aprobacion.estado = EstadoAprobacion.APROBADO.value
    aprobacion.aprobador_id = current_user.id
    aprobacion.fecha_aprobacion = datetime.now()
    if request.comentarios:
        aprobacion.comentarios = request.comentarios
    
    # Verificar si todas las aprobaciones necesarias están completas
    prestamo = aprobacion.prestamo
    todas_aprobadas = _verificar_aprobaciones_completas(prestamo.id, db)
    
    if todas_aprobadas:
        prestamo.estado = EstadoPrestamo.APROBADO.value
        logger.info(f"Préstamo {prestamo.id} APROBADO - Todas las aprobaciones completadas")
    
    db.commit()
    
    return {
        "aprobacion_id": aprobacion.id,
        "estado": aprobacion.estado,
        "prestamo_aprobado": todas_aprobadas,
        "mensaje": "Aprobación exitosa" if todas_aprobadas else "Aprobación registrada, faltan otros niveles"
    }


@router.post("/rechazar")
def rechazar_solicitud(
    request: RechazarRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rechazar una solicitud de préstamo.
    """
    # Obtener aprobación
    aprobacion = db.query(Aprobacion).filter(Aprobacion.id == request.aprobacion_id).first()
    if not aprobacion:
        raise HTTPException(status_code=404, detail="Aprobación no encontrada")
    
    # Verificar que esté pendiente
    if aprobacion.estado != EstadoAprobacion.PENDIENTE.value:
        raise HTTPException(
            status_code=400,
            detail=f"La aprobación ya fue {aprobacion.estado}"
        )
    
    # Verificar permisos
    if not _verificar_permiso_aprobacion(current_user, aprobacion.nivel):
        raise HTTPException(
            status_code=403,
            detail="No tiene permisos para rechazar en este nivel"
        )
    
    # Rechazar
    aprobacion.estado = EstadoAprobacion.RECHAZADO.value
    aprobacion.aprobador_id = current_user.id
    aprobacion.fecha_aprobacion = datetime.now()
    aprobacion.comentarios = request.motivo
    
    # Actualizar estado del préstamo
    prestamo = aprobacion.prestamo
    prestamo.estado = EstadoPrestamo.RECHAZADO.value
    
    db.commit()
    
    logger.info(f"Préstamo {prestamo.id} RECHAZADO por {current_user.email}")
    
    return {
        "aprobacion_id": aprobacion.id,
        "estado": aprobacion.estado,
        "prestamo_rechazado": True,
        "mensaje": "Solicitud rechazada exitosamente"
    }


@router.get("/pendientes")
def obtener_aprobaciones_pendientes(
    nivel: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener aprobaciones pendientes según permisos del usuario.
    """
    query = db.query(Aprobacion).filter(
        Aprobacion.estado == EstadoAprobacion.PENDIENTE.value
    )
    
    # Filtrar por nivel si se especifica
    if nivel:
        query = query.filter(Aprobacion.nivel == nivel)
    else:
        # Filtrar por niveles que el usuario puede aprobar
        niveles_permitidos = _obtener_niveles_aprobacion(current_user)
        query = query.filter(Aprobacion.nivel.in_(niveles_permitidos))
    
    aprobaciones = query.all()
    
    return {
        "total": len(aprobaciones),
        "aprobaciones": [
            {
                "id": a.id,
                "prestamo_id": a.prestamo_id,
                "cliente": f"{a.prestamo.cliente.nombres} {a.prestamo.cliente.apellidos}",
                "monto": float(a.prestamo.monto_total),
                "nivel": a.nivel,
                "solicitante": a.solicitante.email if a.solicitante else None,
                "creada_en": a.creada_en,
                "comentarios": a.comentarios
            }
            for a in aprobaciones
        ]
    }


@router.get("/historial/{prestamo_id}")
def historial_aprobaciones(
    prestamo_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtener historial completo de aprobaciones de un préstamo.
    """
    aprobaciones = db.query(Aprobacion).filter(
        Aprobacion.prestamo_id == prestamo_id
    ).order_by(Aprobacion.creada_en).all()
    
    return {
        "prestamo_id": prestamo_id,
        "total_aprobaciones": len(aprobaciones),
        "historial": [
            {
                "id": a.id,
                "nivel": a.nivel,
                "estado": a.estado,
                "solicitante": a.solicitante.email if a.solicitante else None,
                "aprobador": a.aprobador.email if a.aprobador else None,
                "comentarios": a.comentarios,
                "fecha_solicitud": a.creada_en,
                "fecha_aprobacion": a.fecha_aprobacion
            }
            for a in aprobaciones
        ]
    }


@router.get("/estadisticas")
def estadisticas_aprobaciones(
    db: Session = Depends(get_db)
):
    """
    Obtener estadísticas generales de aprobaciones.
    """
    from sqlalchemy import func
    
    # Totales por estado
    totales = db.query(
        Aprobacion.estado,
        func.count(Aprobacion.id).label('total')
    ).group_by(Aprobacion.estado).all()
    
    # Totales por nivel
    por_nivel = db.query(
        Aprobacion.nivel,
        func.count(Aprobacion.id).label('total')
    ).group_by(Aprobacion.nivel).all()
    
    # Tiempo promedio de aprobación
    aprobaciones_completadas = db.query(Aprobacion).filter(
        Aprobacion.fecha_aprobacion.isnot(None)
    ).all()
    
    if aprobaciones_completadas:
        tiempos = [
            (a.fecha_aprobacion - a.creada_en).total_seconds() / 3600  # horas
            for a in aprobaciones_completadas
        ]
        tiempo_promedio = sum(tiempos) / len(tiempos)
    else:
        tiempo_promedio = 0
    
    return {
        "por_estado": {estado: total for estado, total in totales},
        "por_nivel": {nivel: total for nivel, total in por_nivel},
        "tiempo_promedio_horas": round(tiempo_promedio, 2),
        "total_procesadas": len(aprobaciones_completadas)
    }


# Funciones helper
def _verificar_permiso_aprobacion(user: User, nivel: str) -> bool:
    """
    Verificar si el usuario tiene permiso para aprobar en el nivel dado.
    """
    permisos_por_rol = {
        "ADMIN": [NivelAprobacion.GERENTE.value, NivelAprobacion.DIRECTOR.value, NivelAprobacion.COMITE.value],
        "GERENTE": [NivelAprobacion.GERENTE.value],
        "DIRECTOR": [NivelAprobacion.DIRECTOR.value],
        "COMITE": [NivelAprobacion.COMITE.value]
    }
    
    niveles_permitidos = permisos_por_rol.get(user.rol, [])
    return nivel in niveles_permitidos


def _obtener_niveles_aprobacion(user: User) -> List[str]:
    """
    Obtener niveles de aprobación que el usuario puede gestionar.
    """
    permisos_por_rol = {
        "ADMIN": [NivelAprobacion.GERENTE.value, NivelAprobacion.DIRECTOR.value, NivelAprobacion.COMITE.value],
        "GERENTE": [NivelAprobacion.GERENTE.value],
        "DIRECTOR": [NivelAprobacion.DIRECTOR.value],
        "COMITE": [NivelAprobacion.COMITE.value]
    }
    
    return permisos_por_rol.get(user.rol, [])


def _verificar_aprobaciones_completas(prestamo_id: int, db: Session) -> bool:
    """
    Verificar si todas las aprobaciones necesarias están completas.
    """
    # Obtener préstamo
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        return False
    
    # Definir niveles requeridos según monto
    niveles_requeridos = []
    monto = float(prestamo.monto_total)
    
    if monto > 50000:
        niveles_requeridos = [
            NivelAprobacion.GERENTE.value,
            NivelAprobacion.DIRECTOR.value,
            NivelAprobacion.COMITE.value
        ]
    elif monto > 10000:
        niveles_requeridos = [
            NivelAprobacion.GERENTE.value,
            NivelAprobacion.DIRECTOR.value
        ]
    else:
        niveles_requeridos = [NivelAprobacion.GERENTE.value]
    
    # Verificar que todos los niveles estén aprobados
    for nivel in niveles_requeridos:
        aprobacion = db.query(Aprobacion).filter(
            and_(
                Aprobacion.prestamo_id == prestamo_id,
                Aprobacion.nivel == nivel,
                Aprobacion.estado == EstadoAprobacion.APROBADO.value
            )
        ).first()
        
        if not aprobacion:
            return False
    
    return True
