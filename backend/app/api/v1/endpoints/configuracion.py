# backend/app/api/v1/endpoints/configuracion.py
"""
Endpoint para configuración administrativa del sistema.
Gestión de parámetros, tasas, límites y ajustes generales.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal

from app.db.session import get_db
from app.models.user import User
from app.core.security import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# MONITOREO Y OBSERVABILIDAD
# ============================================

@router.get("/monitoreo/estado")
def obtener_estado_monitoreo(
    current_user: User = Depends(get_current_user)
):
    """
    🔍 Verificar estado del sistema de monitoreo y observabilidad
    """
    # Solo admin puede ver configuración de monitoreo
    if current_user.rol != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo administradores pueden ver configuración de monitoreo")
    
    from app.core.monitoring import get_monitoring_status
    return get_monitoring_status()


@router.post("/monitoreo/habilitar")
def habilitar_monitoreo_basico(
    current_user: User = Depends(get_current_user)
):
    """
    ⚡ Habilitar monitoreo básico sin dependencias externas
    """
    if current_user.rol != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo administradores pueden configurar monitoreo")
    
    try:
        # Configurar logging estructurado básico
        import logging
        
        # Configurar formato mejorado
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Logger específico para el sistema de financiamiento
        finance_logger = logging.getLogger("financiamiento_automotriz")
        finance_logger.setLevel(logging.INFO)
        
        return {
            "mensaje": "✅ Monitoreo básico habilitado",
            "configuracion": {
                "logging_estructurado": "✅ Habilitado",
                "nivel_log": "INFO",
                "formato": "Timestamp + Archivo + Línea + Mensaje",
                "logger_especifico": "financiamiento_automotriz"
            },
            "beneficios": [
                "📋 Logs más detallados y estructurados",
                "🔍 Mejor debugging de errores",
                "📊 Tracking básico de operaciones",
                "⚡ Sin dependencias externas adicionales"
            ],
            "siguiente_paso": "Configurar Sentry y Prometheus para monitoreo avanzado"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error habilitando monitoreo: {str(e)}")

# Schemas
class ConfiguracionTasas(BaseModel):
    tasa_interes_base: Decimal = Field(..., ge=0, le=100, description="Tasa de interés base anual (%)")
    tasa_mora: Decimal = Field(..., ge=0, le=10, description="Tasa de mora mensual (%)")
    tasa_descuento_pronto_pago: Optional[Decimal] = Field(None, ge=0, le=10)

class ConfiguracionLimites(BaseModel):
    monto_minimo_prestamo: Decimal = Field(..., gt=0)
    monto_maximo_prestamo: Decimal = Field(..., gt=0)
    plazo_minimo_meses: int = Field(..., ge=1)
    plazo_maximo_meses: int = Field(..., le=360)
    limite_prestamos_activos: int = Field(..., ge=1, le=10)

class ConfiguracionNotificaciones(BaseModel):
    dias_previos_recordatorio: int = Field(default=3, ge=1, le=30)
    dias_mora_alerta: int = Field(default=15, ge=1, le=90)
    email_notificaciones: bool = True
    whatsapp_notificaciones: bool = False
    sms_notificaciones: bool = False

class ConfiguracionGeneral(BaseModel):
    nombre_empresa: str
    ruc: str
    direccion: str
    telefono: str
    email: str
    horario_atencion: str
    zona_horaria: str = "America/Guayaquil"

# Almacenamiento temporal de configuraciones (en producción usar Redis o DB)
_config_cache: Dict[str, Any] = {
    "tasas": {
        "tasa_interes_base": 15.0,
        "tasa_mora": 2.0,
        "tasa_descuento_pronto_pago": 1.0
    },
    "limites": {
        "monto_minimo_prestamo": 100.0,
        "monto_maximo_prestamo": 50000.0,
        "plazo_minimo_meses": 1,
        "plazo_maximo_meses": 60,
        "limite_prestamos_activos": 3
    },
    "notificaciones": {
        "dias_previos_recordatorio": 3,
        "dias_mora_alerta": 15,
        "email_notificaciones": True,
        "whatsapp_notificaciones": False,
        "sms_notificaciones": False
    },
    "general": {
        "nombre_empresa": "Sistema de Préstamos y Cobranza",
        "ruc": "0000000000001",
        "direccion": "Av. Principal 123",
        "telefono": "+593 99 999 9999",
        "email": "info@prestamos.com",
        "horario_atencion": "Lunes a Viernes 9:00 - 18:00",
        "zona_horaria": "America/Guayaquil"
    }
}


@router.get("/tasas")
def obtener_configuracion_tasas(
    current_user: User = Depends(get_current_user)
):
    """
    Obtener configuración de tasas de interés.
    """
    return _config_cache["tasas"]


@router.put("/tasas")
def actualizar_configuracion_tasas(
    config: ConfiguracionTasas,
    current_user: User = Depends(get_current_user)
):
    """
    Actualizar configuración de tasas de interés.
    Solo accesible para ADMIN.
    """
    if current_user.rol != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo administradores pueden modificar tasas")
    
    _config_cache["tasas"] = {
        "tasa_interes_base": float(config.tasa_interes_base),
        "tasa_mora": float(config.tasa_mora),
        "tasa_descuento_pronto_pago": float(config.tasa_descuento_pronto_pago) if config.tasa_descuento_pronto_pago else 0.0
    }
    
    logger.info(f"Tasas actualizadas por {current_user.email}: {_config_cache['tasas']}")
    
    return {
        "mensaje": "Configuración de tasas actualizada exitosamente",
        "tasas": _config_cache["tasas"]
    }


@router.get("/limites")
def obtener_configuracion_limites(
    current_user: User = Depends(get_current_user)
):
    """
    Obtener configuración de límites de préstamos.
    """
    return _config_cache["limites"]


@router.put("/limites")
def actualizar_configuracion_limites(
    config: ConfiguracionLimites,
    current_user: User = Depends(get_current_user)
):
    """
    Actualizar configuración de límites.
    Solo accesible para ADMIN.
    """
    if current_user.rol != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo administradores pueden modificar límites")
    
    # Validar que máximo > mínimo
    if config.monto_maximo_prestamo <= config.monto_minimo_prestamo:
        raise HTTPException(
            status_code=400,
            detail="El monto máximo debe ser mayor al monto mínimo"
        )
    
    if config.plazo_maximo_meses <= config.plazo_minimo_meses:
        raise HTTPException(
            status_code=400,
            detail="El plazo máximo debe ser mayor al plazo mínimo"
        )
    
    _config_cache["limites"] = {
        "monto_minimo_prestamo": float(config.monto_minimo_prestamo),
        "monto_maximo_prestamo": float(config.monto_maximo_prestamo),
        "plazo_minimo_meses": config.plazo_minimo_meses,
        "plazo_maximo_meses": config.plazo_maximo_meses,
        "limite_prestamos_activos": config.limite_prestamos_activos
    }
    
    logger.info(f"Límites actualizados por {current_user.email}: {_config_cache['limites']}")
    
    return {
        "mensaje": "Configuración de límites actualizada exitosamente",
        "limites": _config_cache["limites"]
    }


@router.get("/notificaciones")
def obtener_configuracion_notificaciones(
    current_user: User = Depends(get_current_user)
):
    """
    Obtener configuración de notificaciones.
    """
    return _config_cache["notificaciones"]


@router.put("/notificaciones")
def actualizar_configuracion_notificaciones(
    config: ConfiguracionNotificaciones,
    current_user: User = Depends(get_current_user)
):
    """
    Actualizar configuración de notificaciones.
    Solo accesible para ADMIN y GERENTE.
    """
    if current_user.rol not in ["ADMIN", "GERENTE"]:
        raise HTTPException(status_code=403, detail="Sin permisos para modificar notificaciones")
    
    _config_cache["notificaciones"] = {
        "dias_previos_recordatorio": config.dias_previos_recordatorio,
        "dias_mora_alerta": config.dias_mora_alerta,
        "email_notificaciones": config.email_notificaciones,
        "whatsapp_notificaciones": config.whatsapp_notificaciones,
        "sms_notificaciones": config.sms_notificaciones
    }
    
    logger.info(f"Notificaciones actualizadas por {current_user.email}")
    
    return {
        "mensaje": "Configuración de notificaciones actualizada exitosamente",
        "notificaciones": _config_cache["notificaciones"]
    }


@router.get("/general")
def obtener_configuracion_general(
    current_user: User = Depends(get_current_user)
):
    """
    Obtener configuración general del sistema.
    """
    return _config_cache["general"]


@router.put("/general")
def actualizar_configuracion_general(
    config: ConfiguracionGeneral,
    current_user: User = Depends(get_current_user)
):
    """
    Actualizar configuración general.
    Solo accesible para ADMIN.
    """
    if current_user.rol != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo administradores pueden modificar configuración general")
    
    _config_cache["general"] = {
        "nombre_empresa": config.nombre_empresa,
        "ruc": config.ruc,
        "direccion": config.direccion,
        "telefono": config.telefono,
        "email": config.email,
        "horario_atencion": config.horario_atencion,
        "zona_horaria": config.zona_horaria
    }
    
    logger.info(f"Configuración general actualizada por {current_user.email}")
    
    return {
        "mensaje": "Configuración general actualizada exitosamente",
        "configuracion": _config_cache["general"]
    }


@router.get("/completa")
def obtener_configuracion_completa(
    current_user: User = Depends(get_current_user)
):
    """
    Obtener toda la configuración del sistema.
    """
    return {
        "tasas": _config_cache["tasas"],
        "limites": _config_cache["limites"],
        "notificaciones": _config_cache["notificaciones"],
        "general": _config_cache["general"]
    }


@router.post("/restablecer")
def restablecer_configuracion_defecto(
    seccion: str,  # tasas, limites, notificaciones, general, todo
    current_user: User = Depends(get_current_user)
):
    """
    Restablecer configuración a valores por defecto.
    Solo accesible para ADMIN.
    """
    if current_user.rol != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo administradores pueden restablecer configuración")
    
    defaults = {
        "tasas": {
            "tasa_interes_base": 15.0,
            "tasa_mora": 2.0,
            "tasa_descuento_pronto_pago": 1.0
        },
        "limites": {
            "monto_minimo_prestamo": 100.0,
            "monto_maximo_prestamo": 50000.0,
            "plazo_minimo_meses": 1,
            "plazo_maximo_meses": 60,
            "limite_prestamos_activos": 3
        },
        "notificaciones": {
            "dias_previos_recordatorio": 3,
            "dias_mora_alerta": 15,
            "email_notificaciones": True,
            "whatsapp_notificaciones": False,
            "sms_notificaciones": False
        },
        "general": {
            "nombre_empresa": "Sistema de Préstamos y Cobranza",
            "ruc": "0000000000001",
            "direccion": "Av. Principal 123",
            "telefono": "+593 99 999 9999",
            "email": "info@prestamos.com",
            "horario_atencion": "Lunes a Viernes 9:00 - 18:00",
            "zona_horaria": "America/Guayaquil"
        }
    }
    
    if seccion == "todo":
        _config_cache.update(defaults)
        logger.warning(f"TODA la configuración restablecida por {current_user.email}")
        return {
            "mensaje": "Toda la configuración ha sido restablecida a valores por defecto",
            "configuracion": _config_cache
        }
    
    elif seccion in defaults:
        _config_cache[seccion] = defaults[seccion]
        logger.warning(f"Configuración de {seccion} restablecida por {current_user.email}")
        return {
            "mensaje": f"Configuración de {seccion} restablecida a valores por defecto",
            "configuracion": _config_cache[seccion]
        }
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Sección inválida. Opciones: tasas, limites, notificaciones, general, todo"
        )


@router.get("/calcular-cuota")
def calcular_cuota_ejemplo(
    monto: float,
    plazo_meses: int,
    tasa_personalizada: Optional[float] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Calcular cuota mensual con la configuración actual de tasas.
    """
    # Obtener tasa
    tasa = tasa_personalizada if tasa_personalizada else _config_cache["tasas"]["tasa_interes_base"]
    
    # Validar límites
    limites = _config_cache["limites"]
    if monto < limites["monto_minimo_prestamo"] or monto > limites["monto_maximo_prestamo"]:
        raise HTTPException(
            status_code=400,
            detail=f"Monto fuera de límites permitidos: ${limites['monto_minimo_prestamo']:,.2f} - ${limites['monto_maximo_prestamo']:,.2f}"
        )
    
    if plazo_meses < limites["plazo_minimo_meses"] or plazo_meses > limites["plazo_maximo_meses"]:
        raise HTTPException(
            status_code=400,
            detail=f"Plazo fuera de límites permitidos: {limites['plazo_minimo_meses']} - {limites['plazo_maximo_meses']} meses"
        )
    
    # Cálculo de cuota (método francés)
    tasa_mensual = (tasa / 100) / 12
    
    if tasa_mensual == 0:
        cuota = monto / plazo_meses
    else:
        cuota = monto * (tasa_mensual * (1 + tasa_mensual)**plazo_meses) / ((1 + tasa_mensual)**plazo_meses - 1)
    
    total_pagar = cuota * plazo_meses
    total_interes = total_pagar - monto
    
    return {
        "monto_solicitado": monto,
        "plazo_meses": plazo_meses,
        "tasa_interes_anual": tasa,
        "cuota_mensual": round(cuota, 2),
        "total_pagar": round(total_pagar, 2),
        "total_interes": round(total_interes, 2),
        "relacion_cuota_ingreso_sugerida": "< 40%"
    }


@router.get("/validar-limites/{cliente_id}")
def validar_limites_cliente(
    cliente_id: int,
    monto_solicitado: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Validar si un cliente puede solicitar un nuevo préstamo según límites configurados.
    """
    from app.models.prestamo import Prestamo
    
    # Contar préstamos activos del cliente
    prestamos_activos = db.query(Prestamo).filter(
        Prestamo.cliente_id == cliente_id,
        Prestamo.estado == "ACTIVO"
    ).count()
    
    limite_prestamos = _config_cache["limites"]["limite_prestamos_activos"]
    limites_monto = _config_cache["limites"]
    
    # Validaciones
    validaciones = {
        "puede_solicitar": True,
        "mensajes": []
    }
    
    if prestamos_activos >= limite_prestamos:
        validaciones["puede_solicitar"] = False
        validaciones["mensajes"].append(
            f"El cliente ya tiene {prestamos_activos} préstamos activos (límite: {limite_prestamos})"
        )
    
    if monto_solicitado < limites_monto["monto_minimo_prestamo"]:
        validaciones["puede_solicitar"] = False
        validaciones["mensajes"].append(
            f"Monto mínimo permitido: ${limites_monto['monto_minimo_prestamo']:,.2f}"
        )
    
    if monto_solicitado > limites_monto["monto_maximo_prestamo"]:
        validaciones["puede_solicitar"] = False
        validaciones["mensajes"].append(
            f"Monto máximo permitido: ${limites_monto['monto_maximo_prestamo']:,.2f}"
        )
    
    return {
        "cliente_id": cliente_id,
        "prestamos_activos": prestamos_activos,
        "limite_prestamos": limite_prestamos,
        "monto_solicitado": monto_solicitado,
        **validaciones
    }
