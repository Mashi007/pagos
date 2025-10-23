"""
Endpoint de diagnóstico completo del sistema
Verifica todos los componentes críticos
"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
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

@router.get("/sistema")
def diagnostico_completo_sistema(db: Session = Depends(get_db)):
    """
    🔍 Diagnóstico completo del sistema
    Verifica todos los componentes críticos
    """
    diagnostico = {
        "timestamp": datetime.now().isoformat(),
        "status": "checking",
        "componentes": {}
    }

    try:
        # 1. Verificar conexión a base de datos
        try:
            db.execute(text("SELECT 1"))
            diagnostico["componentes"]["base_datos"] = {
                "status": "ok",
                "message": "Conexión exitosa",
                "url_configurada": bool(settings.DATABASE_URL)
            }
        except Exception as e:
            diagnostico["componentes"]["base_datos"] = {
                "status": "error",
                "message": f"Error de conexión: {str(e)}"
            }

        # 2. Verificar tablas críticas
        tablas_criticas = [
            ("usuarios", User),
            ("clientes", Cliente),
            ("analistas", Analista),
            ("concesionarios", Concesionario),
            ("modelos_vehiculos", ModeloVehiculo),
            ("auditoria", Auditoria)
        ]

        diagnostico["componentes"]["tablas"] = {}
        for nombre_tabla, modelo in tablas_criticas:
            try:
                count = db.query(modelo).count()
                diagnostico["componentes"]["tablas"][nombre_tabla] = {
                    "status": "ok",
                    "registros": count,
                    "message": f"Tabla {nombre_tabla} accesible"
                }
            except Exception as e:
                diagnostico["componentes"]["tablas"][nombre_tabla] = {
                    "status": "error",
                    "message": f"Error en tabla {nombre_tabla}: {str(e)}"
                }

        # 3. Verificar datos de configuración
        try:
            analistas_activos = db.query(Analista).filter(Analista.activo ).count()
            concesionarios_activos = db.query(Concesionario).filter(Concesionario.activo ).count()
            modelos_activos = db.query(ModeloVehiculo).filter(ModeloVehiculo.activo ).count()

            diagnostico["componentes"]["configuracion"] = {
                "status": "ok",
                "analistas_activos": analistas_activos,
                "concesionarios_activos": concesionarios_activos,
                "modelos_activos": modelos_activos,
                "message": "Datos de configuración disponibles"
            }
        except Exception as e:
            diagnostico["componentes"]["configuracion"] = {
                "status": "error",
                "message": f"Error en configuración: {str(e)}"
            }

        # 4. Verificar usuario administrador
        try:
            admin_count = db.query(User).filter(User.is_admin).count()
            admin_activo = db.query(User).filter(
                User.is_admin,
                User.is_active
            ).count()

            diagnostico["componentes"]["administradores"] = {
                "status": "ok",
                "total_admins": admin_count,
                "admins_activos": admin_activo,
                "message": "Usuarios administradores verificados"
            }
        except Exception as e:
            diagnostico["componentes"]["administradores"] = {
                "status": "error",
                "message": f"Error verificando administradores: {str(e)}"
            }

        # 5. Verificar configuración de la aplicación
        diagnostico["componentes"]["configuracion_app"] = {
            "status": "ok",
            "environment": settings.ENVIRONMENT,
            "log_level": settings.LOG_LEVEL,
            "cors_origins": len(settings.CORS_ORIGINS),
            "secret_key_configurado": bool(settings.SECRET_KEY),
            "database_url_configurado": bool(settings.DATABASE_URL)
        }

        # 6. Determinar estado general
        errores = []
        for componente, info in diagnostico["componentes"].items():
            if info.get("status") == "error":
                errores.append(f"{componente}: {info.get('message', 'Error desconocido')}")

        if errores:
            diagnostico["status"] = "error"
            diagnostico["errores"] = errores
            diagnostico["message"] = f"Sistema con {len(errores)} errores críticos"
        else:
            diagnostico["status"] = "ok"
            diagnostico["message"] = "Sistema funcionando correctamente"

        return diagnostico

    except Exception as e:
        logger.error(f"Error en diagnóstico completo: {str(e)}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "message": f"Error crítico en diagnóstico: {str(e)}",
            "componentes": {}
        }

@router.get("/endpoints")
def verificar_endpoints_criticos():
    """
    🔗 Verificar estado de endpoints críticos
    """
    endpoints_criticos = [
        "/api/v1/auth/login",
        "/api/v1/auth/me", 
        "/api/v1/auth/refresh",
        "/api/v1/clientes/",
        "/api/v1/usuarios/",
        "/api/v1/analistas/activos",
        "/api/v1/concesionarios/activos",
        "/api/v1/modelos-vehiculos/activos"
    ]

    return {
        "timestamp": datetime.now().isoformat(),
        "endpoints_criticos": endpoints_criticos,
        "total_endpoints": len(endpoints_criticos),
        "message": "Lista de endpoints críticos para verificar",
        "nota": "Usar herramientas como Postman o curl para verificar cada endpoint"
    }

@router.get("/configuracion")
def verificar_configuracion_sistema():
    """
    ⚙️ Verificar configuración del sistema
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "configuracion": {
            "environment": settings.ENVIRONMENT,
            "log_level": settings.LOG_LEVEL,
            "cors_origins_count": len(settings.CORS_ORIGINS),
            "secret_key_length": len(settings.SECRET_KEY) if settings.SECRET_KEY else 0,
            "database_url_configured": bool(settings.DATABASE_URL),
            "app_name": settings.APP_NAME,
            "app_version": settings.APP_VERSION
        },
        "status": "ok",
        "message": "Configuración del sistema verificada"
    }

@router.get("/monitoreo")
def monitoreo_tiempo_real(db: Session = Depends(get_db)):
    """
    📊 Monitoreo en tiempo real del sistema
    """
    try:
        # Métricas de rendimiento
        start_time = datetime.now()

        # Verificar conexión DB
        db.execute(text("SELECT 1"))
        db_response_time = (datetime.now() - start_time).total_seconds() * 1000

        # Contar registros en tiempo real
        usuarios_count = db.query(User).count()
        clientes_count = db.query(Cliente).count()
        analistas_count = db.query(Analista).count()
        concesionarios_count = db.query(Concesionario).count()
        modelos_count = db.query(ModeloVehiculo).count()

        # Verificar usuarios activos
        usuarios_activos = db.query(User).filter(User.is_active ).count()
        usuarios_admin = db.query(User).filter(User.is_admin ).count()

        # Verificar datos de configuración activos
        analistas_activos = db.query(Analista).filter(Analista.activo ).count()
        concesionarios_activos = db.query(Concesionario).filter(Concesionario.activo ).count()
        modelos_activos = db.query(ModeloVehiculo).filter(ModeloVehiculo.activo ).count()

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "rendimiento": {
                "db_response_time_ms": round(db_response_time, 2),
                "db_status": "connected"
            },
            "metricas": {
                "usuarios": {
                    "total": usuarios_count,
                    "activos": usuarios_activos,
                    "administradores": usuarios_admin,
                    "porcentaje_activos": round((usuarios_activos / usuarios_count * 100) if usuarios_count > 0 else 0, 2)
                },
                "clientes": {
                    "total": clientes_count
                },
                "configuracion": {
                    "analistas_activos": analistas_activos,
                    "concesionarios_activos": concesionarios_activos,
                    "modelos_activos": modelos_activos,
                    "total_analistas": analistas_count,
                    "total_concesionarios": concesionarios_count,
                    "total_modelos": modelos_count
                }
            },
            "alertas": [],
            "message": "Sistema funcionando correctamente"
        }

    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
            "message": "Error en monitoreo del sistema"
        }

@router.get("/logs")
def obtener_logs_sistema():
    """
    📝 Obtener información de logs del sistema
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "log_level": settings.LOG_LEVEL,
        "environment": settings.ENVIRONMENT,
        "message": "Información de configuración de logs",
        "nota": "Los logs detallados están disponibles en los logs del servidor"
    }
