#!/usr/bin/env python3
"""
Script para verificar estado del servidor y ejecutar simulación cuando esté disponible
"""

import requests
import os
import logging
import time
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = os.getenv("FRONTEND_URL", "https://pagos-f2qf.onrender.com")

def verificar_estado_servidor():
    """Verificar si el servidor está disponible"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=10)
        logger.info(f"   📊 Status Code: {response.status_code}")
        if response.status_code == 200:
            logger.info("   ✅ Servidor disponible")
            return True
        else:
            logger.warning(f"   ⚠️ Servidor responde con código: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"   ❌ Error conectando al servidor: {e}")
        return False

def verificar_endpoint_login():
    """Verificar si el endpoint de login está funcionando"""
    try:
        # Probar OPTIONS primero
        response = requests.options(f"{BASE_URL}/api/v1/auth/login", timeout=10)
        logger.info(f"   📊 OPTIONS Status: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("   ✅ Endpoint de login disponible")
            return True
        else:
            logger.warning(f"   ⚠️ Endpoint de login responde con código: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"   ❌ Error verificando endpoint de login: {e}")
        return False

def esperar_servidor_disponible(max_intentos=10, intervalo=30):
    """Esperar hasta que el servidor esté disponible"""
    logger.info("🔄 ESPERANDO A QUE EL SERVIDOR ESTÉ DISPONIBLE")
    logger.info("=" * 60)
    
    for intento in range(1, max_intentos + 1):
        logger.info(f"📊 Intento {intento}/{max_intentos}")
        logger.info("-" * 30)
        
        # Verificar estado general del servidor
        logger.info("1️⃣ Verificando estado general del servidor...")
        servidor_ok = verificar_estado_servidor()
        
        if servidor_ok:
            # Verificar endpoint específico
            logger.info("2️⃣ Verificando endpoint de login...")
            endpoint_ok = verificar_endpoint_login()
            
            if endpoint_ok:
                logger.info("✅ SERVIDOR COMPLETAMENTE DISPONIBLE")
                return True
        
        if intento < max_intentos:
            logger.info(f"⏳ Esperando {intervalo} segundos antes del siguiente intento...")
            time.sleep(intervalo)
        else:
            logger.error("❌ Servidor no disponible después de todos los intentos")
            return False
    
    return False

def ejecutar_simulacion_cuando_disponible():
    """Ejecutar la simulación cuando el servidor esté disponible"""
    logger.info("🎭 SIMULACIÓN DE CASOS REALES - VERIFICACIÓN DE SERVIDOR")
    logger.info("=" * 80)
    logger.info(f"📊 Fecha y hora: {datetime.now()}")
    logger.info(f"🌐 URL del servidor: {BASE_URL}")
    logger.info("=" * 80)
    logger.info("")
    
    # Esperar a que el servidor esté disponible
    if esperar_servidor_disponible():
        logger.info("")
        logger.info("🚀 SERVIDOR DISPONIBLE - EJECUTANDO SIMULACIÓN")
        logger.info("=" * 60)
        
        # Importar y ejecutar el script de simulación
        try:
            import subprocess
            result = subprocess.run([
                "py", "backend/scripts/simulacion_casos_reales_usuarios.py"
            ], capture_output=True, text=True, timeout=300)
            
            logger.info("📊 RESULTADO DE LA SIMULACIÓN:")
            logger.info("-" * 40)
            logger.info(result.stdout)
            
            if result.stderr:
                logger.error("❌ ERRORES EN LA SIMULACIÓN:")
                logger.error("-" * 40)
                logger.error(result.stderr)
            
            if result.returncode == 0:
                logger.info("✅ SIMULACIÓN COMPLETADA EXITOSAMENTE")
            else:
                logger.error(f"❌ SIMULACIÓN FALLÓ CON CÓDIGO: {result.returncode}")
                
        except subprocess.TimeoutExpired:
            logger.error("❌ SIMULACIÓN TIMEOUT - Tardó más de 5 minutos")
        except Exception as e:
            logger.error(f"❌ ERROR EJECUTANDO SIMULACIÓN: {e}")
    else:
        logger.error("❌ NO SE PUDO EJECUTAR LA SIMULACIÓN - SERVIDOR NO DISPONIBLE")

if __name__ == "__main__":
    ejecutar_simulacion_cuando_disponible()
