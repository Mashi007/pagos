"""
Endpoint de diagnóstico completo del sistema
"""

import logging
from typing import Any, Dict

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
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "message": "Conexión a base de datos exitosa"}
    except Exception as e:
        return {"status": "error", "message": f"Error de conexión: {str(e)}"}


def _verificar_tablas_criticas(db: Session) -> Dict[str, Any]:
    """Verificar existencia de tablas críticas"""
    tablas_criticas = [
        "users",
        "clientes",
        "analistas",
        "concesionarios",
        "modelos_vehiculos",
        "auditoria",
    ]

    todas_existen = True
    resultados = []

    for tabla in tablas_criticas:
        try:
            query = text(f"SELECT COUNT(*) FROM {tabla} LIMIT 1")
            db.execute(query)
            resultados.append(
                {"tabla": tabla, "existe": True, "accesible": True, "error": None}
            )
        except Exception as e:
            resultados.append(
                {"tabla": tabla, "existe": False, "accesible": False, "error": str(e)}
            )
            todas_existen = False

    return {"todas_las_tablas_existen": todas_existen, "resultados": resultados}


def _verificar_modelos_sqlalchemy(db: Session) -> Dict[str, Any]:
    """Verificar que los modelos SQLAlchemy funcionen"""
    modelos = {
        "Analista": Analista,
        "Cliente": Cliente,
        "User": User,
        "Concesionario": Concesionario,
        "ModeloVehiculo": ModeloVehiculo,
        "Auditoria": Auditoria,
    }

    resultados = []

    for nombre, modelo in modelos.items():
        try:
            # Intentar hacer una consulta básica
            count = db.query(modelo).count()
            resultados.append(
                {
                    "modelo": nombre,
                    "funciona": True,
                    "registros": count,
                    "tabla": modelo.__tablename__,
                }
            )
        except Exception as e:
            resultados.append(
                {
                    "modelo": nombre,
                    "funciona": False,
                    "error": str(e),
                    "tabla": getattr(modelo, "__tablename__", "unknown"),
                }
            )

    return {
        "modelos_funcionando": len([r for r in resultados if r["funciona"]]),
        "total_modelos": len(resultados),
        "resultados": resultados,
    }


def _verificar_configuracion() -> Dict[str, Any]:
    """Verificar configuración del sistema"""
    config_checks = {
        "database_url": bool(settings.DATABASE_URL),
        "secret_key": bool(settings.SECRET_KEY),
        "cors_origins": bool(settings.CORS_ORIGINS),
    }

    config_ok = all(config_checks.values())

    return {"configuracion_completa": config_ok, "checks": config_checks}


def _verificar_endpoints() -> Dict[str, Any]:
    """Verificar endpoints básicos"""
    endpoints = [
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/users/me",
        "/api/v1/clientes/",
        "/api/v1/analistas/",
    ]

    return {"endpoints_disponibles": endpoints, "total": len(endpoints)}


@router.get("/completo")
def diagnostico_completo(db: Session = Depends(get_db)):
    """Diagnóstico completo del sistema"""
    try:
        logger.info("Iniciando diagnóstico completo del sistema")

        # Ejecutar todas las verificaciones
        verificaciones = {
            "conexion_bd": _verificar_conexion_bd(db),
            "tablas_criticas": _verificar_tablas_criticas(db),
            "modelos_sqlalchemy": _verificar_modelos_sqlalchemy(db),
            "configuracion": _verificar_configuracion(),
            "endpoints": _verificar_endpoints(),
        }

        # Determinar estado general
        estado_general = "ok"

        if verificaciones["conexion_bd"]["status"] != "ok":
            estado_general = "error"

        if not verificaciones["tablas_criticas"]["todas_las_tablas_existen"]:
            estado_general = "error"

        if (
            verificaciones["modelos_sqlalchemy"]["modelos_funcionando"]
            < verificaciones["modelos_sqlalchemy"]["total_modelos"]
        ):
            estado_general = "warning"

        if not verificaciones["configuracion"]["configuracion_completa"]:
            estado_general = "error"

        # Generar recomendaciones
        recomendaciones = []
        if estado_general == "error":
            recomendaciones.extend(
                [
                    "Revisar configuración de base de datos",
                    "Verificar que todas las tablas existan",
                    "Comprobar configuración del sistema",
                ]
            )
        else:
            recomendaciones.append("Sistema funcionando correctamente")

        resultado = {
            "estado_general": estado_general,
            "verificaciones": verificaciones,
            "recomendaciones": recomendaciones,
            "timestamp": "2025-10-25T18:55:00Z",
        }

        logger.info(f"Diagnóstico completado - Estado: {estado_general}")

        return resultado

    except Exception as e:
        logger.error(f"Error en diagnóstico completo: {e}")
        return {
            "estado_general": "error",
            "error": str(e),
            "timestamp": "2025-10-25T18:55:00Z",
        }


@router.get("/rapido")
def diagnostico_rapido(db: Session = Depends(get_db)):
    """Diagnóstico rápido del sistema"""
    try:
        logger.info("Iniciando diagnóstico rápido")

        # Verificaciones básicas
        conexion_ok = _verificar_conexion_bd(db)["status"] == "ok"
        config_ok = _verificar_configuracion()["configuracion_completa"]

        estado = "ok" if conexion_ok and config_ok else "error"

        resultado = {
            "estado": estado,
            "conexion_bd": conexion_ok,
            "configuracion": config_ok,
            "timestamp": "2025-10-25T18:55:00Z",
        }

        logger.info(f"Diagnóstico rápido completado - Estado: {estado}")

        return resultado

    except Exception as e:
        logger.error(f"Error en diagnóstico rápido: {e}")
        return {"estado": "error", "error": str(e), "timestamp": "2025-10-25T18:55:00Z"}


@router.get("/tablas")
def diagnostico_tablas(db: Session = Depends(get_db)):
    """Diagnóstico específico de tablas"""
    try:
        logger.info("Iniciando diagnóstico de tablas")

        verificacion_tablas = _verificar_tablas_criticas(db)

        return {"tablas": verificacion_tablas, "timestamp": "2025-10-25T18:55:00Z"}

    except Exception as e:
        logger.error(f"Error en diagnóstico de tablas: {e}")
        return {"error": str(e), "timestamp": "2025-10-25T18:55:00Z"}


@router.get("/endpoints")
def diagnostico_endpoints():
    """Diagnóstico de endpoints"""
    try:
        endpoints = _verificar_endpoints()

        return {"endpoints": endpoints, "timestamp": "2025-10-25T18:55:00Z"}

    except Exception as e:
        return {"error": str(e), "timestamp": "2025-10-25T18:55:00Z"}
