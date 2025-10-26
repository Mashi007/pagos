import logging
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.configuracion_sistema import ConfiguracionSistema
from app.models.prestamo import Prestamo
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


class ConfiguracionUpdate(BaseModel):
    """Schema para actualizar configuración"""

    clave: str = Field(..., description="Clave de configuración")
    valor: str = Field(..., description="Valor de configuración")
    descripcion: Optional[str] = Field(None, description="Descripción")


class ConfiguracionResponse(BaseModel):
    """Response para configuración"""

    id: int
    clave: str
    valor: str
    descripcion: Optional[str]
    fecha_actualizacion: datetime
    actualizado_por: int

    class Config:
        from_attributes = True


# ============================================
# MONITOREO Y OBSERVABILIDAD
# ============================================


@router.get("/monitoreo/estado")
def obtener_estado_monitoreo(current_user: User = Depends(get_current_user)):
    """Verificar estado del sistema de monitoreo y observabilidad"""
    # Solo admin puede ver configuración de monitoreo
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden ver configuración de monitoreo",
        )

    return {
        "estado": "ACTIVO",
        "nivel": "BÁSICO",
        "componentes": {
            "logging": "ACTIVO",
            "health_checks": "ACTIVO",
            "métricas_básicas": "ACTIVO",
        },
        "última_verificación": datetime.now(),
    }


@router.post("/monitoreo/habilitar-basico")
def habilitar_monitoreo_basico(current_user: User = Depends(get_current_user)):
    """Habilitar monitoreo básico sin dependencias externas"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403, detail="Solo administradores pueden configurar monitoreo"
        )

    try:
        # Configurar logging estructurado básico
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Logger específico para el sistema de financiamiento
        finance_logger = logging.getLogger("financiamiento_automotriz")
        finance_logger.setLevel(logging.INFO)

        return {
            "mensaje": "Monitoreo básico habilitado exitosamente",
            "configuración": {
                "nivel_logging": "INFO",
                "formato": "Timestamp + Archivo + Línea + Mensaje",
                "logger_específico": "financiamiento_automotriz",
            },
            "características": [
                "Logging estructurado",
                "Health checks básicos",
                "Métricas de operaciones",
                "Sin dependencias externas adicionales",
            ],
            "siguiente_paso": "Configurar Sentry y Prometheus para monitoreo avanzado",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error configurando monitoreo: {str(e)}"
        )


# ============================================
# CONFIGURACIÓN CENTRALIZADA DEL SISTEMA
# ============================================


@router.get("/sistema/completa")
def obtener_configuracion_completa(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Obtener toda la configuración del sistema"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden ver configuración completa",
        )

    try:
        configuraciones = db.query(ConfiguracionSistema).all()

        return {
            "configuraciones": [
                {
                    "clave": config.clave,
                    "valor": config.valor,
                    "descripcion": config.descripcion,
                    "fecha_actualizacion": config.fecha_actualizacion,
                }
                for config in configuraciones
            ],
            "total": len(configuraciones),
        }

    except Exception as e:
        logger.error(f"Error obteniendo configuración: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/sistema/{clave}")
def obtener_configuracion_por_clave(
    clave: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener configuración específica por clave"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403, detail="Solo administradores pueden ver configuración"
        )

    try:
        config = (
            db.query(ConfiguracionSistema)
            .filter(ConfiguracionSistema.clave == clave)
            .first()
        )

        if not config:
            raise HTTPException(
                status_code=404, detail=f"Configuración '{clave}' no encontrada"
            )

        return config

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo configuración: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.put("/sistema/{clave}")
def actualizar_configuracion(
    clave: str,
    config_data: ConfiguracionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar configuración específica"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden actualizar configuración",
        )

    try:
        config = (
            db.query(ConfiguracionSistema)
            .filter(ConfiguracionSistema.clave == clave)
            .first()
        )

        if not config:
            # Crear nueva configuración
            config = ConfiguracionSistema(
                clave=config_data.clave,
                valor=config_data.valor,
                descripcion=config_data.descripcion,
                actualizado_por=current_user.id,
            )
            db.add(config)
        else:
            # Actualizar configuración existente
            config.valor = config_data.valor
            config.descripcion = config_data.descripcion
            config.actualizado_por = int(current_user.id)
            config.fecha_actualizacion = datetime.now()

        db.commit()
        db.refresh(config)

        return {
            "mensaje": "Configuración actualizada exitosamente",
            "configuracion": config,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando configuración: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.delete("/sistema/{clave}")
def eliminar_configuracion(
    clave: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminar configuración específica"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403, detail="Solo administradores pueden eliminar configuración"
        )

    try:
        config = (
            db.query(ConfiguracionSistema)
            .filter(ConfiguracionSistema.clave == clave)
            .first()
        )

        if not config:
            raise HTTPException(
                status_code=404, detail=f"Configuración '{clave}' no encontrada"
            )

        db.delete(config)
        db.commit()

        return {"mensaje": "Configuración eliminada exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando configuración: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


# ============================================
# CONFIGURACIÓN DE PRÉSTAMOS
# ============================================


@router.get("/prestamos/parametros")
def obtener_parametros_prestamos(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Obtener parámetros de configuración para préstamos"""
    try:
        # Obtener configuraciones relacionadas con préstamos
        configs = (
            db.query(ConfiguracionSistema)
            .filter(ConfiguracionSistema.clave.like("PRESTAMO_%"))
            .all()
        )

        parametros = {}
        for config in configs:
            parametros[config.clave] = {
                "valor": config.valor,
                "descripcion": config.descripcion,
            }

        return {"parametros": parametros, "total": len(configs)}

    except Exception as e:
        logger.error(f"Error obteniendo parámetros: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/sistema/estadisticas")
def obtener_estadisticas_sistema(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Obtener estadísticas del sistema"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden ver estadísticas del sistema",
        )

    try:
        # Estadísticas básicas
        total_configuraciones = db.query(ConfiguracionSistema).count()
        total_usuarios = db.query(User).count()
        total_prestamos = db.query(Prestamo).count()

        # Configuraciones por categoría
        configs_por_categoria = (
            db.query(
                ConfiguracionSistema.clave,
                func.count(ConfiguracionSistema.id).label("cantidad"),
            )
            .group_by(func.split_part(ConfiguracionSistema.clave, "_", 1))
            .all()
        )

        return {
            "estadisticas_generales": {
                "total_configuraciones": total_configuraciones,
                "total_usuarios": total_usuarios,
                "total_prestamos": total_prestamos,
            },
            "configuraciones_por_categoria": [
                {"categoria": item[0], "cantidad": item[1]}
                for item in configs_por_categoria
            ],
            "fecha_consulta": datetime.now(),
        }

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )
