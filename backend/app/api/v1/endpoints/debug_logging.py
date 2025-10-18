# backend/app/api/v1/endpoints/debug_logging.py
"""
Endpoint para diagnosticar y arreglar problemas de logging
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging
import sys
import os
from datetime import datetime

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.core.config import settings

router = APIRouter()

@router.get("/debug-logging-status")
def debug_logging_status(
    current_user: User = Depends(get_current_user)
):
    """
    Diagnosticar el estado del sistema de logging
    """
    try:
        # 1. Verificar configuración de logging
        root_logger = logging.getLogger()
        
        logging_info = {
            "root_logger_level": root_logger.level,
            "root_logger_level_name": logging.getLevelName(root_logger.level),
            "root_logger_handlers": len(root_logger.handlers),
            "settings_log_level": settings.LOG_LEVEL,
            "python_version": sys.version,
            "environment": settings.ENVIRONMENT,
        }
        
        # 2. Verificar handlers específicos
        handlers_info = []
        for i, handler in enumerate(root_logger.handlers):
            handlers_info.append({
                "index": i,
                "type": str(type(handler)),
                "level": handler.level,
                "level_name": logging.getLevelName(handler.level),
                "formatter": str(type(handler.formatter)) if handler.formatter else None,
                "stream": str(handler.stream) if hasattr(handler, 'stream') else None,
            })
        
        # 3. Verificar loggers específicos
        specific_loggers = [
            "app",
            "app.services.auth_service",
            "app.api.v1.endpoints.auth",
            "uvicorn",
            "uvicorn.access",
            "uvicorn.error",
            "sqlalchemy.engine",
        ]
        
        loggers_info = {}
        for logger_name in specific_loggers:
            logger = logging.getLogger(logger_name)
            loggers_info[logger_name] = {
                "level": logger.level,
                "level_name": logging.getLevelName(logger.level),
                "handlers": len(logger.handlers),
                "propagate": logger.propagate,
                "disabled": logger.disabled,
            }
        
        # 4. Probar logging
        test_messages = []
        try:
            logging.info("🔍 TEST LOGGING INFO - Debug logging status")
            test_messages.append("INFO message sent")
        except Exception as e:
            test_messages.append(f"ERROR sending INFO: {e}")
        
        try:
            logging.warning("⚠️ TEST LOGGING WARNING - Debug logging status")
            test_messages.append("WARNING message sent")
        except Exception as e:
            test_messages.append(f"ERROR sending WARNING: {e}")
        
        try:
            logging.error("❌ TEST LOGGING ERROR - Debug logging status")
            test_messages.append("ERROR message sent")
        except Exception as e:
            test_messages.append(f"ERROR sending ERROR: {e}")
        
        # 5. Verificar variables de entorno
        env_info = {
            "PYTHONUNBUFFERED": os.getenv("PYTHONUNBUFFERED"),
            "LOG_LEVEL": os.getenv("LOG_LEVEL"),
            "ENVIRONMENT": os.getenv("ENVIRONMENT"),
            "UVICORN_LOG_LEVEL": os.getenv("UVICORN_LOG_LEVEL"),
        }
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "is_admin": current_user.is_admin
            },
            "logging_configuration": logging_info,
            "handlers": handlers_info,
            "specific_loggers": loggers_info,
            "test_messages": test_messages,
            "environment_variables": env_info,
            "recommendations": [
                "Verificar que LOG_LEVEL esté configurado correctamente",
                "Asegurar que PYTHONUNBUFFERED=1 esté configurado",
                "Verificar que los handlers estén configurados",
                "Comprobar que los loggers específicos no estén deshabilitados"
            ]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.post("/fix-logging")
def fix_logging(
    current_user: User = Depends(get_current_user)
):
    """
    Arreglar la configuración de logging
    """
    try:
        # 1. Limpiar configuración existente
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        # 2. Configurar logging básico pero robusto
        log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        
        # Configurar handler para stdout
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        
        # Formatter simple pero efectivo
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # Aplicar configuración
        root_logger.setLevel(log_level)
        root_logger.addHandler(handler)
        
        # 3. Configurar loggers específicos
        specific_loggers = [
            "app",
            "app.services.auth_service",
            "app.api.v1.endpoints.auth",
            "uvicorn",
            "uvicorn.access",
            "uvicorn.error",
            "sqlalchemy.engine",
        ]
        
        for logger_name in specific_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(log_level)
            logger.handlers.clear()
            logger.addHandler(handler)
            logger.propagate = True
            logger.disabled = False
        
        # 4. Probar el logging arreglado
        logging.info("✅ LOGGING ARREGLADO - Sistema de logging configurado correctamente")
        logging.warning("⚠️ LOGGING ARREGLADO - Prueba de warning")
        logging.error("❌ LOGGING ARREGLADO - Prueba de error")
        
        return {
            "status": "success",
            "message": "Sistema de logging arreglado exitosamente",
            "timestamp": datetime.utcnow().isoformat(),
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "is_admin": current_user.is_admin
            },
            "configuration_applied": {
                "log_level": settings.LOG_LEVEL,
                "log_level_numeric": log_level,
                "handlers_count": len(root_logger.handlers),
                "specific_loggers_configured": len(specific_loggers)
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/test-logging")
def test_logging(
    current_user: User = Depends(get_current_user)
):
    """
    Probar el sistema de logging con diferentes niveles
    """
    try:
        messages = []
        
        # Probar diferentes niveles
        logging.debug("🔍 DEBUG: Mensaje de debug - Usuario: %s", current_user.email)
        messages.append("DEBUG message sent")
        
        logging.info("ℹ️ INFO: Mensaje de información - Usuario: %s", current_user.email)
        messages.append("INFO message sent")
        
        logging.warning("⚠️ WARNING: Mensaje de advertencia - Usuario: %s", current_user.email)
        messages.append("WARNING message sent")
        
        logging.error("❌ ERROR: Mensaje de error - Usuario: %s", current_user.email)
        messages.append("ERROR message sent")
        
        # Probar logging estructurado
        logging.info("📊 LOGGING TEST - Usuario ID: %d, Email: %s, Admin: %s", 
                    current_user.id, current_user.email, current_user.is_admin)
        messages.append("Structured logging test sent")
        
        return {
            "status": "success",
            "message": "Mensajes de logging enviados",
            "timestamp": datetime.utcnow().isoformat(),
            "messages_sent": messages,
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "is_admin": current_user.is_admin
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/check-logs-output")
def check_logs_output(
    current_user: User = Depends(get_current_user)
):
    """
    Verificar si los logs están apareciendo en la salida
    """
    try:
        # Enviar mensajes de prueba con timestamp
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        logging.info(f"[{timestamp}] 🔍 LOGGING CHECK - Usuario: {current_user.email}")
        logging.warning(f"[{timestamp}] ⚠️ LOGGING CHECK - Usuario: {current_user.email}")
        logging.error(f"[{timestamp}] ❌ LOGGING CHECK - Usuario: {current_user.email}")
        
        # También usar print como fallback
        print(f"[{timestamp}] 🖨️ PRINT CHECK - Usuario: {current_user.email}")
        print(f"[{timestamp}] ⚠️ PRINT WARNING - Usuario: {current_user.email}")
        print(f"[{timestamp}] ❌ PRINT ERROR - Usuario: {current_user.email}")
        
        return {
            "status": "success",
            "message": "Mensajes de prueba enviados tanto por logging como por print",
            "timestamp": timestamp,
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "is_admin": current_user.is_admin
            },
            "note": "Revisar los logs del servidor para ver si aparecen estos mensajes"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
