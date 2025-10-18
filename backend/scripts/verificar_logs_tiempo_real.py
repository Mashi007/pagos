# backend/scripts/verificar_logs_tiempo_real.py
"""
VERIFICACIÓN DE LOGS EN TIEMPO REAL - TERCERA AUDITORÍA
Analizar logs de producción para encontrar la causa raíz
"""
import os
import sys
import logging
import requests
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verificar_logs_tiempo_real():
    """
    Verificar logs de producción en tiempo real
    """
    logger.info("📊 VERIFICANDO LOGS DE PRODUCCIÓN EN TIEMPO REAL")
    logger.info("=" * 60)
    
    # URLs de producción
    backend_url = "https://pagos-f2qf.onrender.com"
    frontend_url = "https://rapicredit.onrender.com"
    
    # 1. VERIFICAR HEALTH CHECK DEL BACKEND
    logger.info("🏥 1. VERIFICANDO HEALTH CHECK DEL BACKEND")
    logger.info("-" * 40)
    
    try:
        response = requests.get(f"{backend_url}/api/v1/health", timeout=10)
        if response.status_code == 200:
            logger.info("✅ Backend está funcionando")
            logger.info(f"   📊 Respuesta: {response.json()}")
        else:
            logger.error(f"❌ Backend con problemas: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Error conectando al backend: {e}")
    
    # 2. VERIFICAR ENDPOINT DE LOGS
    logger.info("\n📝 2. VERIFICANDO ENDPOINT DE LOGS")
    logger.info("-" * 40)
    
    try:
        response = requests.get(f"{backend_url}/api/v1/log-test/force-logs", timeout=10)
        if response.status_code == 200:
            logger.info("✅ Endpoint de logs funcionando")
            logger.info(f"   📊 Respuesta: {response.json()}")
        else:
            logger.error(f"❌ Endpoint de logs con problemas: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Error en endpoint de logs: {e}")
    
    # 3. VERIFICAR ENDPOINT /me SIN AUTENTICACIÓN
    logger.info("\n🔍 3. VERIFICANDO ENDPOINT /me SIN AUTENTICACIÓN")
    logger.info("-" * 40)
    
    try:
        response = requests.get(f"{backend_url}/api/v1/auth/me", timeout=10)
        logger.info(f"📊 Status Code: {response.status_code}")
        if response.status_code == 401:
            logger.info("✅ Endpoint /me requiere autenticación (correcto)")
        else:
            logger.warning(f"⚠️ Respuesta inesperada: {response.status_code}")
            logger.info(f"   📊 Respuesta: {response.text[:200]}...")
    except Exception as e:
        logger.error(f"❌ Error verificando /me: {e}")
    
    # 4. VERIFICAR ENDPOINT DE VERIFICACIÓN DE PERMISOS
    logger.info("\n🔐 4. VERIFICANDO ENDPOINT DE PERMISOS")
    logger.info("-" * 40)
    
    try:
        response = requests.get(f"{backend_url}/api/v1/verificar-permisos/verificar-permisos-completos", timeout=10)
        logger.info(f"📊 Status Code: {response.status_code}")
        if response.status_code == 401:
            logger.info("✅ Endpoint de permisos requiere autenticación (correcto)")
        else:
            logger.warning(f"⚠️ Respuesta inesperada: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Error verificando permisos: {e}")
    
    # 5. VERIFICAR FRONTEND
    logger.info("\n🌐 5. VERIFICANDO FRONTEND")
    logger.info("-" * 40)
    
    try:
        response = requests.get(frontend_url, timeout=10)
        if response.status_code == 200:
            logger.info("✅ Frontend está funcionando")
            logger.info(f"   📊 Tamaño respuesta: {len(response.text)} caracteres")
        else:
            logger.error(f"❌ Frontend con problemas: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Error conectando al frontend: {e}")
    
    # 6. VERIFICAR CONFIGURACIÓN CORS
    logger.info("\n🌐 6. VERIFICANDO CONFIGURACIÓN CORS")
    logger.info("-" * 40)
    
    try:
        headers = {
            'Origin': frontend_url,
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'Authorization'
        }
        
        response = requests.options(f"{backend_url}/api/v1/auth/me", headers=headers, timeout=10)
        logger.info(f"📊 CORS Preflight Status: {response.status_code}")
        
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers')
        }
        
        logger.info("📋 Headers CORS:")
        for key, value in cors_headers.items():
            logger.info(f"   {key}: {value}")
            
    except Exception as e:
        logger.error(f"❌ Error verificando CORS: {e}")
    
    logger.info("\n📊 RESUMEN DE VERIFICACIÓN DE LOGS")
    logger.info("=" * 60)
    logger.info("✅ Verificación completada")
    logger.info("💡 Revisar logs del servidor para más detalles")

if __name__ == "__main__":
    verificar_logs_tiempo_real()
