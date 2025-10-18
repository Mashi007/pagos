#!/usr/bin/env python3
"""
Script para verificar y arreglar el logging en producción
"""
import os
import sys
import logging
from datetime import datetime

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

def verificar_logging():
    """Verificar el sistema de logging"""
    logger.info("🔍 Verificando sistema de logging...")
    
    # 1. Verificar configuración básica
    root_logger = logging.getLogger()
    logger.info(f"📊 Root logger level: {root_logger.level}")
    logger.info(f"📊 Root logger handlers: {len(root_logger.handlers)}")
    
    # 2. Probar diferentes niveles
    logger.debug("🔍 DEBUG: Mensaje de debug")
    logger.info("ℹ️ INFO: Mensaje de información")
    logger.warning("⚠️ WARNING: Mensaje de advertencia")
    logger.error("❌ ERROR: Mensaje de error")
    
    # 3. Probar print como fallback
    print(f"[{datetime.now()}] 🖨️ PRINT: Mensaje de prueba")
    
    # 4. Verificar variables de entorno
    env_vars = [
        "LOG_LEVEL",
        "ENVIRONMENT", 
        "PYTHONUNBUFFERED",
        "UVICORN_LOG_LEVEL"
    ]
    
    logger.info("🌍 Variables de entorno:")
    for var in env_vars:
        value = os.getenv(var)
        logger.info(f"  - {var}: {value}")
    
    # 5. Verificar configuración de uvicorn
    logger.info("🚀 Configuración de uvicorn:")
    logger.info(f"  - Python version: {sys.version}")
    logger.info(f"  - Platform: {sys.platform}")
    
    logger.info("✅ Verificación de logging completada")

def arreglar_logging():
    """Arreglar la configuración de logging"""
    logger.info("🔧 Arreglando configuración de logging...")
    
    # Limpiar configuración existente
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Configurar logging robusto
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)
    
    # Configurar loggers específicos
    loggers_to_fix = [
        "app",
        "app.services.auth_service",
        "app.api.v1.endpoints.auth",
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
    ]
    
    for logger_name in loggers_to_fix:
        logger_obj = logging.getLogger(logger_name)
        logger_obj.setLevel(logging.INFO)
        logger_obj.handlers.clear()
        logger_obj.addHandler(handler)
        logger_obj.propagate = True
        logger_obj.disabled = False
    
    logger.info("✅ Logging arreglado exitosamente")
    
    # Probar el logging arreglado
    logger.info("🧪 Probando logging arreglado...")
    logger.warning("⚠️ Prueba de warning")
    logger.error("❌ Prueba de error")

if __name__ == "__main__":
    try:
        verificar_logging()
        print("\n" + "="*50)
        arreglar_logging()
        print("\n" + "="*50)
        verificar_logging()
        
        logger.info("🎉 Script de logging completado exitosamente")
        
    except Exception as e:
        logger.error(f"💥 Error en script de logging: {e}")
        print(f"💥 Error: {e}")
        sys.exit(1)
