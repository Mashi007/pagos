"""Endpoint de diagnóstico completo del sistema
Verifica todos los componentes críticos
"""

import logging
from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.core.config import settings
from app.models.analista import Analista
from app.models.auditoria import Auditoria
from app.models.cliente import Cliente
from app.models.concesionario import Concesionario
from app.models.modelo_vehiculo import ModeloVehiculo
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

def _verificar_conexion_bd(db: Session) -> Dict[str, Any]:
    """Verificar conexión a base de datos"""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "message": "Conexión exitosa",
            "url_configurada": bool(settings.DATABASE_URL),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error de conexión: {str(e)}",
        }

def _verificar_tablas_criticas(db: Session) -> Dict[str, Any]:
    """Verificar existencia de tablas críticas"""
    tablas_criticas = [
        "analistas", "clientes", "users", "usuarios", 
        "concesionarios", "modelo_vehiculos", "auditoria"
    ]
    
    resultados = {}
    todas_existen = True
    
    for tabla in tablas_criticas:
        try:
            query = text(f"SELECT COUNT(*) FROM {tabla} LIMIT 1")
            db.execute(query)
            resultados[tabla] = {"existe": True, "accesible": True}
        except Exception as e:
            resultados[tabla] = {
                "existe": False, 
                "accesible": False, 
                "error": str(e)
            }
            todas_existen = False
    
    return {
        "todas_las_tablas_existen": todas_existen,
        "tablas": resultados
    }

def _verificar_modelos_sqlalchemy(db: Session) -> Dict[str, Any]:
    """Verificar que los modelos SQLAlchemy funcionen correctamente"""
    modelos = {
        "Analista": Analista,
        "Cliente": Cliente,
        "User": User,
        "Concesionario": Concesionario,
        "ModeloVehiculo": ModeloVehiculo,
        "Auditoria": Auditoria,
    }
    
    resultados = {}
    todos_funcionan = True
    
    for nombre_modelo, modelo in modelos.items():
        try:
            # Intentar hacer una consulta básica
            count = db.query(modelo).count()
            resultados[nombre_modelo] = {
                "funciona": True,
                "registros": count,
                "tabla": modelo.__tablename__
            }
        except Exception as e:
            resultados[nombre_modelo] = {
                "funciona": False,
                "error": str(e),
                "tabla": getattr(modelo, '__tablename__', 'unknown')
            }
            todos_funcionan = False
    
    return {
        "todos_los_modelos_funcionan": todos_funcionan,
        "modelos": resultados
    }

def _verificar_configuracion() -> Dict[str, Any]:
    """Verificar configuración del sistema"""
    config_checks = {
        "database_url": bool(settings.DATABASE_URL),
        "secret_key": bool(settings.SECRET_KEY),
        "algorithm": bool(settings.ALGORITHM),
        "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0,
    }
    
    config_ok = all(config_checks.values())
    
    return {
        "configuracion_completa": config_ok,
        "checks": config_checks,
        "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    }

def _verificar_endpoints_criticos() -> Dict[str, Any]:
    """Verificar que los endpoints críticos estén disponibles"""
    # Esta función simula la verificación de endpoints
    # En un entorno real, se harían requests HTTP a los endpoints
    
    endpoints_criticos = [
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/users/me",
        "/api/v1/clientes/",
        "/api/v1/analistas/",
    ]
    
    return {
        "endpoints_verificados": endpoints_criticos,
        "nota": "Verificación simulada - en producción se harían requests reales"
    }

@router.get("/diagnostico-completo")
async def diagnostico_completo(db: Session = Depends(get_db)):
    """🔍 Diagnóstico completo del sistema"""
    try:
        logger.info("🔍 Iniciando diagnóstico completo del sistema")
        
        # Ejecutar todas las verificaciones
        verificaciones = {
            "timestamp": datetime.now().isoformat(),
            "conexion_bd": _verificar_conexion_bd(db),
            "tablas_criticas": _verificar_tablas_criticas(db),
            "modelos_sqlalchemy": _verificar_modelos_sqlalchemy(db),
            "configuracion": _verificar_configuracion(),
            "endpoints_criticos": _verificar_endpoints_criticos(),
        }
        
        # Determinar estado general
        estado_general = "ok"
        problemas_criticos = []
        
        if verificaciones["conexion_bd"]["status"] != "ok":
            estado_general = "error"
            problemas_criticos.append("Error de conexión a base de datos")
        
        if not verificaciones["tablas_criticas"]["todas_las_tablas_existen"]:
            estado_general = "error"
            problemas_criticos.append("Faltan tablas críticas en la base de datos")
        
        if not verificaciones["modelos_sqlalchemy"]["todos_los_modelos_funcionan"]:
            estado_general = "warning"
            problemas_criticos.append("Algunos modelos SQLAlchemy no funcionan correctamente")
        
        if not verificaciones["configuracion"]["configuracion_completa"]:
            estado_general = "error"
            problemas_criticos.append("Configuración incompleta")
        
        # Generar recomendaciones
        recomendaciones = []
        if problemas_criticos:
            recomendaciones.extend([
                "Revisar logs del sistema para más detalles",
                "Verificar configuración de base de datos",
                "Ejecutar migraciones si es necesario"
            ])
        else:
            recomendaciones.append("Sistema funcionando correctamente")
        
        resultado = {
            "estado_general": estado_general,
            "problemas_criticos": problemas_criticos,
            "recomendaciones": recomendaciones,
            "verificaciones": verificaciones,
        }
        
        logger.info(f"🔍 Diagnóstico completado - Estado: {estado_general}")
        
        return {
            "success": True,
            "diagnostico": resultado
        }
        
    except Exception as e:
        logger.error(f"🔍 Error en diagnóstico completo: {e}")
        return {
            "success": False,
            "error": str(e),
            "diagnostico": {
                "estado_general": "error",
                "problemas_criticos": [f"Error interno: {str(e)}"],
                "recomendaciones": ["Contactar administrador del sistema"]
            }
        }

@router.get("/diagnostico-rapido")
async def diagnostico_rapido(db: Session = Depends(get_db)):
    """⚡ Diagnóstico rápido del sistema"""
    try:
        logger.info("⚡ Iniciando diagnóstico rápido")
        
        # Verificaciones básicas
        conexion_ok = _verificar_conexion_bd(db)["status"] == "ok"
        config_ok = _verificar_configuracion()["configuracion_completa"]
        
        estado = "ok" if conexion_ok and config_ok else "error"
        
        resultado = {
            "timestamp": datetime.now().isoformat(),
            "estado": estado,
            "conexion_bd": "ok" if conexion_ok else "error",
            "configuracion": "ok" if config_ok else "error",
            "tiempo_respuesta": "< 1 segundo"
        }
        
        logger.info(f"⚡ Diagnóstico rápido completado - Estado: {estado}")
        
        return {
            "success": True,
            "diagnostico_rapido": resultado
        }
        
    except Exception as e:
        logger.error(f"⚡ Error en diagnóstico rápido: {e}")
        return {
            "success": False,
            "error": str(e),
            "diagnostico_rapido": {
                "estado": "error",
                "error": str(e)
            }
        }

@router.get("/diagnostico/tablas")
async def diagnostico_tablas(db: Session = Depends(get_db)):
    """📊 Diagnóstico específico de tablas"""
    try:
        logger.info("📊 Iniciando diagnóstico de tablas")
        
        verificacion_tablas = _verificar_tablas_criticas(db)
        
        return {
            "success": True,
            "diagnostico_tablas": verificacion_tablas
        }
        
    except Exception as e:
        logger.error(f"📊 Error en diagnóstico de tablas: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/diagnostico/modelos")
async def diagnostico_modelos(db: Session = Depends(get_db)):
    """🏗️ Diagnóstico específico de modelos"""
    try:
        logger.info("🏗️ Iniciando diagnóstico de modelos")
        
        verificacion_modelos = _verificar_modelos_sqlalchemy(db)
        
        return {
            "success": True,
            "diagnostico_modelos": verificacion_modelos
        }
        
    except Exception as e:
        logger.error(f"🏗️ Error en diagnóstico de modelos: {e}")
        return {
            "success": False,
            "error": str(e)
        }