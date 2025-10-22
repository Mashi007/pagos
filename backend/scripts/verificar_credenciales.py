#!/usr/bin/env python3
"""
Script para probar diferentes credenciales de administrador
"""

import requests
import os
import logging
from dotenv import load_dotenv

# Constantes de configuración
REQUEST_TIMEOUT = 10
SEPARATOR_LENGTH = 60
TOKEN_PREFIX_LENGTH = 20

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = os.getenv("FRONTEND_URL", "https://pagos-f2qf.onrender.com")

def probar_credenciales_admin():
    """Probar diferentes credenciales de administrador"""
    logger.info("PROBANDO CREDENCIALES DE ADMINISTRADOR")
    logger.info("=" * SEPARATOR_LENGTH)

    # Diferentes combinaciones de credenciales
    credenciales_posibles = [
        {"email": "itmaster@rapicreditca.com", "password": "admin123"},
        {"email": "itmaster@rapicreditca.com", "password": "Admin123"},
        {"email": "itmaster@rapicreditca.com", "password": "ADMIN123"},
        {"email": "itmaster@rapicreditca.com", "password": "admin"},
        {"email": "itmaster@rapicreditca.com", "password": "password"},
        {"email": "admin@rapicreditca.com", "password": "admin123"},
        {"email": "admin@rapicreditca.com", "password": "Admin123"},
        {"email": "admin@rapicreditca.com", "password": "ADMIN123"},
    ]

    for i, creds in enumerate(credenciales_posibles, 1):
        logger.info(f"📊 Intento {i}: {creds['email']} / {creds['password']}")
        try:
            response = requests.post(f"{BASE_URL}/api/v1/auth/login", 
                                   json={**creds, "remember": True}, 
                                   timeout=REQUEST_TIMEOUT)
            logger.info(f"   📊 Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                logger.info(f"   ✅ LOGIN EXITOSO!")
                logger.info(f"   📊 Usuario: {data['user']['email']}")
                logger.info(f"   📊 Rol: {'Administrador' if data['user']['is_admin'] else 'Usuario'}")
                logger.info(f"   📊 Token obtenido: {data['access_token'][:20]}...")
                return data['access_token']
            else:
                logger.info(f"   ❌ Error: {response.status_code}")
                logger.info(f"   📊 Respuesta: {response.text}")

        except Exception as e:
            logger.error(f"   ❌ Error: {e}")

    logger.error("❌ No se encontraron credenciales válidas")
    return None

def probar_login_usuario_prueba():
    """Probar login con usuario prueba2@gmail.com"""
    logger.info("")
    logger.info("👤 PROBANDO LOGIN CON USUARIO PRUEBA")
    logger.info("=" * 60)

    credenciales_usuario = [
        {"email": "prueba2@gmail.com", "password": "Casa1803"},
        {"email": "prueba2@gmail.com", "password": "casa1803"},
        {"email": "prueba2@gmail.com", "password": "CASA1803"},
        {"email": "prueba2@gmail.com", "password": "Prueba123"},
        {"email": "prueba2@gmail.com", "password": "prueba123"},
    ]

    for i, creds in enumerate(credenciales_usuario, 1):
        logger.info(f"📊 Intento {i}: {creds['email']} / {creds['password']}")
        try:
            response = requests.post(f"{BASE_URL}/api/v1/auth/login", 
                                   json={**creds, "remember": True}, 
                                   timeout=REQUEST_TIMEOUT)
            logger.info(f"   📊 Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                logger.info(f"   ✅ LOGIN EXITOSO!")
                logger.info(f"   📊 Usuario: {data['user']['email']}")
                logger.info(f"   📊 Rol: {'Administrador' if data['user']['is_admin'] else 'Usuario'}")
                logger.info(f"   📊 Estado: {'Activo' if data['user']['is_active'] else 'Inactivo'}")
                return True
            else:
                logger.info(f"   ❌ Error: {response.status_code}")
                logger.info(f"   📊 Respuesta: {response.text}")

        except Exception as e:
            logger.error(f"   ❌ Error: {e}")

    logger.error("❌ No se pudo hacer login con usuario prueba")
    return False

def main():
    logger.info("🔍 VERIFICACIÓN DE CREDENCIALES")
    logger.info("=" * 60)
    logger.info(f"🌐 Servidor: {BASE_URL}")
    logger.info("")

    # Probar credenciales de admin
    admin_token = probar_credenciales_admin()

    # Probar credenciales de usuario
    usuario_ok = probar_login_usuario_prueba()

    # Resumen
    logger.info("")
    logger.info("📊 RESUMEN")
    logger.info("=" * 60)
    if admin_token:
        logger.info("✅ Credenciales de administrador encontradas")
    else:
        logger.error("❌ No se encontraron credenciales de administrador válidas")

    if usuario_ok:
        logger.info("✅ Usuario prueba puede hacer login")
    else:
        logger.error("❌ Usuario prueba no puede hacer login")

if __name__ == "__main__":
    main()
