#!/usr/bin/env python3
"""
Script para probar diferentes credenciales de administrador
"""

import requests
import logging
from dotenv import load_dotenv

# Constantes de configuración
REQUEST_TIMEOUT = 10
SEPARATOR_LENGTH = 60
TOKEN_PREFIX_LENGTH = 20

load_dotenv()

logging.basicConfig
logger = logging.getLogger(__name__)



def probar_credenciales_admin():
    """Probar diferentes credenciales de administrador"""
    logger.info("PROBANDO CREDENCIALES DE ADMINISTRADOR")
    logger.info("=" * SEPARATOR_LENGTH)

    # Diferentes combinaciones de credenciales
        {"email": "itmaster@rapicreditca.com", "password": "admin123"},
        {"email": "itmaster@rapicreditca.com", "password": "Admin123"},
        {"email": "itmaster@rapicreditca.com", "password": "ADMIN123"},
        {"email": "itmaster@rapicreditca.com", "password": "admin"},
        {"email": "itmaster@rapicreditca.com", "password": "password"},
        {"email": "admin@rapicreditca.com", "password": "admin123"},
        {"email": "admin@rapicreditca.com", "password": "Admin123"},
        {"email": "admin@rapicreditca.com", "password": "ADMIN123"},

        logger.info(f"📊 Intento {i}: {creds['email']} / {creds['password']}")
        try:
                f"{BASE_URL}/api/v1/auth/login",
                json={**creds, "remember": True},
            logger.info(f"   📊 Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                logger.info("   ✅ LOGIN EXITOSO!")
                logger.info(f"   📊 Usuario: {data['user']['email']}")
                logger.info
                logger.info(f"   📊 Token obtenido: {data['access_token'][:20]}...")
                return data["access_token"]
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

    for i, creds in enumerate(credenciales_usuario, 1):
        logger.info(f"📊 Intento {i}: {creds['email']} / {creds['password']}")
        try:
                f"{BASE_URL}/api/v1/auth/login",
                json={**creds, "remember": True},
            logger.info(f"   📊 Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                logger.info("   ✅ LOGIN EXITOSO!")
                logger.info(f"   📊 Usuario: {data['user']['email']}")
                logger.info
                logger.info
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
