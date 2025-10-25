﻿"""Endpoint de diagnÃ³stico completo del sistemaVerifica todos los componentes crÃ­ticos"""
import logging
from datetime 
import datetime
from typing 
import Dict, Any, List
from fastapi 
import APIRouter, Depends
from sqlalchemy 
import text
from sqlalchemy.orm 
import Session
from app.api.deps 
import get_db
from app.core.config 
import settings
from app.models.analista 
import Analista
from app.models.auditoria 
import Auditoria
from app.models.cliente 
import Cliente
from app.models.concesionario 
import Concesionario
from app.models.modelo_vehiculo 
import ModeloVehiculo
from app.models.user 
import Userlogger = logging.getLogger(__name__)router = APIRouter()
def _verificar_conexion_bd(db:
 Session) -> Dict[str, Any]:
    """Verificar conexiÃ³n a base de datos"""    try:
        db.execute(text("SELECT 1"))        return {            "status":
 "ok",            "message":
 "ConexiÃ³n exitosa",            "url_configurada":
 bool(settings.DATABASE_URL),        }    except Exception as e:
        return {            "status":
 "error",            "message":
 f"Error de conexiÃ³n:
 {str(e)}",        }
def _verificar_tablas_criticas(db:
 Session) -> Dict[str, Any]:
    """Verificar tablas crÃ­ticas"""    tablas_criticas = [        ("usuarios", User),        ("clientes", Cliente),        ("analistas", Analista),        ("concesionarios", Concesionario),        ("modelos_vehiculos", ModeloVehiculo),        ("auditoria", Auditoria),    ]    resultado = {}    for nombre_tabla, modelo in tablas_criticas:
        try:
            count = db.query(modelo).count()            resultado[nombre_tabla] = {                "status":
 "ok",                "registros":
 count,                "message":
 f"Tabla {nombre_tabla} accesible",            }        except Exception as e:
            resultado[nombre_tabla] = {                "status":
 "error",                "message":
 f"Error en tabla {nombre_tabla}:
 {str(e)}",            }    return resultado
def _verificar_configuracion_datos(db:
 Session) -> Dict[str, Any]:
    """Verificar datos de configuraciÃ³n"""    try:
        analistas_activos = db.query(Analista).filter(Analista.activo).count()        concesionarios_activos = (            db.query(Concesionario).filter(Concesionario.activo).count()        )        modelos_activos = (            db.query(ModeloVehiculo).filter(ModeloVehiculo.activo).count()        )        return {            "status":
 "ok",            "analistas_activos":
 analistas_activos,            "concesionarios_activos":
 concesionarios_activos,            "modelos_activos":
 modelos_activos,            "message":
 "Datos de configuraciÃ³n disponibles",        }    except Exception as e:
        return {            "status":
 "error",            "message":
 f"Error en configuraciÃ³n:
 {str(e)}",        }
def _verificar_administradores(db:
 Session) -> Dict[str, Any]:
    """Verificar usuario administrador"""    try:
        admin_count = db.query(User).filter(User.is_admin).count()        admin_activo = (            db.query(User).filter(User.is_admin, User.is_active).count()        )        return {            "status":
 "ok",            "total_admins":
 admin_count,            "admins_activos":
 admin_activo,            "message":
 "Usuarios administradores verificados",        }    except Exception as e:
        return {            "status":
 "error",            "message":
 f"Error verificando administradores:
 {str(e)}",        }
def _verificar_configuracion_app() -> Dict[str, Any]:
    """Verificar configuraciÃ³n de la aplicaciÃ³n"""    return {        "status":
 "ok",        "environment":
 settings.ENVIRONMENT,        "log_level":
 settings.LOG_LEVEL,        "cors_origins":
 len(settings.CORS_ORIGINS),        "secret_key_configurado":
 bool(settings.SECRET_KEY),        "database_url_configurado":
 bool(settings.DATABASE_URL),    }
def _determinar_estado_general(    componentes:
 Dict[str, Any],) -> tuple[str, List[str], str]:
    """Determinar estado general del sistema"""    errores = []    for componente, info in componentes.items():
        if info.get("status") == "error":
            errores.append(                f"{componente}:
 {info.get('message', 'Error desconocido')}"            )    if errores:
        return "error", errores, f"Sistema con {len(errores)} errores crÃ­ticos"    else:
        return "ok", [], "Sistema funcionando correctamente"@router.get("/sistema")
def diagnostico_completo_sistema(db:
 Session = Depends(get_db)):
    """    ðŸ” DiagnÃ³stico completo del sistema (VERSIÃ“N REFACTORIZADA)    Verifica todos los componentes crÃ­ticos    """    diagnostico = {        "timestamp":
 datetime.now().isoformat(),        "status":
 "checking",        "componentes":
 {},    }    try:
        # Verificar componentes individuales        diagnostico["componentes"]["base_datos"] = _verificar_conexion_bd(db)        diagnostico["componentes"]["tablas"] = _verificar_tablas_criticas(db)        diagnostico["componentes"]["configuracion"] = (            _verificar_configuracion_datos(db)        )        diagnostico["componentes"]["administradores"] = (            _verificar_administradores(db)        )        diagnostico["componentes"][            "configuracion_app"        ] = _verificar_configuracion_app()        # Determinar estado general        status, errores, message = _determinar_estado_general(            diagnostico["componentes"]        )        diagnostico["status"] = status        diagnostico["message"] = message        if errores:
            diagnostico["errores"] = errores        return diagnostico    except Exception as e:
        logger.error(f"Error en diagnÃ³stico completo:
 {str(e)}")        return {            "timestamp":
 datetime.now().isoformat(),            "status":
 "error",            "message":
 f"Error crÃ­tico en diagnÃ³stico:
 {str(e)}",            "componentes":
 {},        }@router.get("/endpoints")
def verificar_endpoints_criticos():
    """    ðŸ”— Verificar estado de endpoints crÃ­ticos    """    endpoints_criticos = [        "/api/v1/auth/login",        "/api/v1/auth/me",        "/api/v1/auth/refresh",        "/api/v1/clientes/",        "/api/v1/usuarios/",        "/api/v1/analistas/activos",        "/api/v1/concesionarios/activos",        "/api/v1/modelos-vehiculos/activos",    ]    return {        "timestamp":
 datetime.now().isoformat(),        "endpoints_criticos":
 endpoints_criticos,        "total_endpoints":
 len(endpoints_criticos),        "message":
 "Lista de endpoints crÃ­ticos para verificar",        "nota":
 "Usar herramientas como Postman o curl para verificar cada \        endpoint",    }@router.get("/configuracion")
def verificar_configuracion_sistema():
    """    âš™ï¸ Verificar configuraciÃ³n del sistema    """    return {        "timestamp":
 datetime.now().isoformat(),        "configuracion":
 {            "environment":
 settings.ENVIRONMENT,            "log_level":
 settings.LOG_LEVEL,            "cors_origins_count":
 len(settings.CORS_ORIGINS),            "secret_key_length":
 (                len(settings.SECRET_KEY) if settings.SECRET_KEY else 0            ),            "database_url_configured":
 bool(settings.DATABASE_URL),            "app_name":
 settings.APP_NAME,            "app_version":
 settings.APP_VERSION,        },        "status":
 "ok",        "message":
 "ConfiguraciÃ³n del sistema verificada",    }@router.get("/monitoreo")
def monitoreo_tiempo_real(db:
 Session = Depends(get_db)):
    """    ðŸ“Š Monitoreo en tiempo real del sistema    """    try:
        # MÃ©tricas de rendimiento        start_time = datetime.now()        # Verificar conexiÃ³n DB        db.execute(text("SELECT 1"))        db_response_time = (datetime.now() - start_time).total_seconds() * 1000        # Contar registros en tiempo real        usuarios_count = db.query(User).count()        clientes_count = db.query(Cliente).count()        analistas_count = db.query(Analista).count()        concesionarios_count = db.query(Concesionario).count()        modelos_count = db.query(ModeloVehiculo).count()        # Verificar usuarios activos        usuarios_activos = db.query(User).filter(User.is_active).count()        usuarios_admin = db.query(User).filter(User.is_admin).count()        # Verificar datos de configuraciÃ³n activos        analistas_activos = db.query(Analista).filter(Analista.activo).count()        concesionarios_activos = (            db.query(Concesionario).filter(Concesionario.activo).count()        )        modelos_activos = (            db.query(ModeloVehiculo).filter(ModeloVehiculo.activo).count()        )        return {            "timestamp":
 datetime.now().isoformat(),            "status":
 "healthy",            "rendimiento":
 {                "db_response_time_ms":
 round(db_response_time, 2),                "db_status":
 "connected",            },            "metricas":
 {                "usuarios":
 {                    "total":
 usuarios_count,                    "activos":
 usuarios_activos,                    "administradores":
 usuarios_admin,                    "porcentaje_activos":
 round(                        (                            (usuarios_activos / usuarios_count * 100)                            if usuarios_count > 0                            else 0                        ),                        2,                    ),                },                "clientes":
 {"total":
 clientes_count},                "configuracion":
 {                    "analistas_activos":
 analistas_activos,                    "concesionarios_activos":
 concesionarios_activos,                    "modelos_activos":
 modelos_activos,                    "total_analistas":
 analistas_count,                    "total_concesionarios":
 concesionarios_count,                    "total_modelos":
 modelos_count,                },            },            "alertas":
 [],            "message":
 "Sistema funcionando correctamente",        }    except Exception as e:
        return {            "timestamp":
 datetime.now().isoformat(),            "status":
 "error",            "error":
 str(e),            "message":
 "Error en monitoreo del sistema",        }@router.get("/logs")
def obtener_logs_sistema():
    """    ðŸ“ Obtener informaciÃ³n de logs del sistema    """    return {        "timestamp":
 datetime.now().isoformat(),        "log_level":
 settings.LOG_LEVEL,        "environment":
 settings.ENVIRONMENT,        "message":
 "InformaciÃ³n de configuraciÃ³n de logs",        "nota":
 "Los logs detallados estÃ¡n disponibles en los logs del \        servidor",    }





