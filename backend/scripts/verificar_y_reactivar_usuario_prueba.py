#!/usr/bin/env python3
"""
Script para verificar y reactivar usuario prueba2@gmail.com
"""

import requests
import os
import logging
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = os.getenv("FRONTEND_URL", "https://pagos-f2qf.onrender.com")

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "itmaster@rapicreditca.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

def login_admin():
    """Realizar login como administrador"""
    login_url = f"{BASE_URL}/api/v1/auth/login"
    credentials = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "remember": True}
    try:
        response = requests.post(login_url, json=credentials)
        logger.info(f"   📊 Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"   ✅ Login exitoso")
            logger.info(f"   📊 Usuario: {data['user']['email']}")
            logger.info(f"   📊 Rol: {'Administrador' if data['user']['is_admin'] else 'Usuario'}")
            return data['access_token']
        else:
            logger.error(f"   ❌ Error en login: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"   ❌ Error durante el login: {e}")
        return None

def verificar_usuario_prueba(token: str):
    """Verificar estado del usuario prueba2@gmail.com"""
    headers = {"Authorization": f"Bearer {token}"}
    user_url = f"{BASE_URL}/api/v1/usuarios/5"  # ID del usuario Prueba Dos
    try:
        response = requests.get(user_url, headers=headers)
        logger.info(f"   📊 Status Code: {response.status_code}")
        if response.status_code == 200:
            user_data = response.json()
            logger.info(f"   ✅ USUARIO OBTENIDO:")
            logger.info(f"   📊 ID: {user_data['id']}")
            logger.info(f"   📊 Email: {user_data['email']}")
            logger.info(f"   📊 Nombre: {user_data['nombre']}")
            logger.info(f"   📊 Apellido: {user_data['apellido']}")
            logger.info(f"   📊 Estado: {'Activo' if user_data['is_active'] else 'Inactivo'}")
            logger.info(f"   📊 Rol: {'Administrador' if user_data['is_admin'] else 'Usuario'}")
            return user_data
        else:
            logger.error(f"   ❌ Error obteniendo usuario: {response.text}")
            return None
    except Exception as e:
        logger.error(f"   ❌ Error: {e}")
        return None

def reactivar_usuario_prueba(token: str):
    """Reactivar usuario prueba2@gmail.com"""
    headers = {"Authorization": f"Bearer {token}"}
    update_url = f"{BASE_URL}/api/v1/usuarios/5"
    update_data = {"is_active": True}
    try:
        response = requests.put(update_url, json=update_data, headers=headers)
        logger.info(f"   📊 Status Code: {response.status_code}")
        if response.status_code == 200:
            updated_data = response.json()
            logger.info(f"   ✅ USUARIO REACTIVADO:")
            logger.info(f"   📊 Email: {updated_data['email']}")
            logger.info(f"   📊 Estado: {'Activo' if updated_data['is_active'] else 'Inactivo'}")
            return updated_data
        else:
            logger.error(f"   ❌ Error reactivando usuario: {response.text}")
            return None
    except Exception as e:
        logger.error(f"   ❌ Error: {e}")
        return None

def probar_login_usuario_prueba():
    """Probar login con usuario prueba2@gmail.com"""
    login_url = f"{BASE_URL}/api/v1/auth/login"
    credentials = {"email": "prueba2@gmail.com", "password": "Casa1803", "remember": True}
    try:
        response = requests.post(login_url, json=credentials)
        logger.info(f"   📊 Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"   ✅ LOGIN EXITOSO CON USUARIO PRUEBA:")
            logger.info(f"   📊 Usuario: {data['user']['email']}")
            logger.info(f"   📊 Rol: {'Administrador' if data['user']['is_admin'] else 'Usuario'}")
            return True
        else:
            logger.error(f"   ❌ Error en login: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            return False
    except Exception as e:
        logger.error(f"   ❌ Error: {e}")
        return False

def main():
    logger.info("🔍 VERIFICACIÓN Y REACTIVACIÓN DE USUARIO PRUEBA")
    logger.info("================================================================================")
    logger.info(f"📊 Fecha y hora: {datetime.now()}")
    logger.info("🎯 Objetivo: Verificar estado y reactivar usuario prueba2@gmail.com")
    logger.info("================================================================================")
    logger.info("")

    # 1. Login como administrador
    logger.info("🔑 1. REALIZANDO LOGIN COMO ADMINISTRADOR")
    logger.info("--------------------------------------------------")
    admin_token = login_admin()
    if not admin_token:
        logger.error("❌ No se pudo iniciar sesión como administrador. Abortando.")
        return

    # 2. Verificar estado del usuario prueba
    logger.info("")
    logger.info("👤 2. VERIFICANDO ESTADO DEL USUARIO PRUEBA")
    logger.info("--------------------------------------------------")
    usuario_prueba = verificar_usuario_prueba(admin_token)
    if not usuario_prueba:
        logger.error("❌ No se pudo obtener datos del usuario. Abortando.")
        return

    # 3. Reactivar si está inactivo
    if not usuario_prueba['is_active']:
        logger.info("")
        logger.info("🔄 3. REACTIVANDO USUARIO INACTIVO")
        logger.info("--------------------------------------------------")
        usuario_reactivado = reactivar_usuario_prueba(admin_token)
        if not usuario_reactivado:
            logger.error("❌ No se pudo reactivar el usuario. Abortando.")
            return
    else:
        logger.info("✅ Usuario ya está activo")

    # 4. Probar login con usuario prueba
    logger.info("")
    logger.info("🧪 4. PROBANDO LOGIN CON USUARIO PRUEBA")
    logger.info("--------------------------------------------------")
    login_exitoso = probar_login_usuario_prueba()

    # 5. Resumen final
    logger.info("")
    logger.info("📊 RESUMEN FINAL")
    logger.info("================================================================================")
    if login_exitoso:
        logger.info("🎉 USUARIO PRUEBA REACTIVADO Y FUNCIONANDO")
        logger.info("   ✅ Usuario activo en base de datos")
        logger.info("   ✅ Login funcionando correctamente")
        logger.info("   ✅ Puede acceder al sistema")
    else:
        logger.error("❌ PROBLEMAS PERSISTENTES CON USUARIO PRUEBA")
        logger.error("   💡 Revisar credenciales o estado del servidor")

if __name__ == "__main__":
    main()
