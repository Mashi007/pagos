#!/usr/bin/env python3
"""
Script para probar la actualización de usuario y verificar el problema del 404
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

def probar_endpoint_usuarios(token: str):
    """Probar diferentes endpoints de usuarios"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Probar endpoint de listar usuarios
    logger.info("   🔍 Probando endpoint: GET /api/v1/usuarios/")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/usuarios/", headers=headers)
        logger.info(f"   📊 Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"   ✅ Lista de usuarios obtenida: {data['total']} usuarios")
            return True
        else:
            logger.error(f"   ❌ Error: {response.text}")
            return False
    except Exception as e:
        logger.error(f"   ❌ Error: {e}")
        return False

def probar_obtener_usuario(token: str, user_id: int):
    """Probar obtener usuario específico"""
    headers = {"Authorization": f"Bearer {token}"}
    
    logger.info(f"   🔍 Probando endpoint: GET /api/v1/usuarios/{user_id}")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/usuarios/{user_id}", headers=headers)
        logger.info(f"   📊 Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"   ✅ Usuario obtenido: {data['email']}")
            return data
        else:
            logger.error(f"   ❌ Error: {response.text}")
            return None
    except Exception as e:
        logger.error(f"   ❌ Error: {e}")
        return None

def probar_actualizar_usuario(token: str, user_id: int, datos_actualizacion: dict):
    """Probar actualizar usuario"""
    headers = {"Authorization": f"Bearer {token}"}
    
    logger.info(f"   🔍 Probando endpoint: PUT /api/v1/usuarios/{user_id}")
    logger.info(f"   📊 Datos a actualizar: {datos_actualizacion}")
    try:
        response = requests.put(f"{BASE_URL}/api/v1/usuarios/{user_id}", json=datos_actualizacion, headers=headers)
        logger.info(f"   📊 Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"   ✅ Usuario actualizado: {data['email']}")
            return data
        else:
            logger.error(f"   ❌ Error: {response.text}")
            return None
    except Exception as e:
        logger.error(f"   ❌ Error: {e}")
        return None

def main():
    logger.info("🔍 PRUEBA DE ACTUALIZACIÓN DE USUARIO")
    logger.info("================================================================================")
    logger.info(f"📊 Fecha y hora: {datetime.now()}")
    logger.info("🎯 Objetivo: Identificar por qué falla la actualización de usuario")
    logger.info("================================================================================")
    logger.info("")

    # 1. Login como administrador
    logger.info("🔑 1. REALIZANDO LOGIN")
    logger.info("--------------------------------------------------")
    admin_token = login_admin()
    if not admin_token:
        logger.error("❌ No se pudo iniciar sesión como administrador. Abortando.")
        return

    # 2. Probar endpoint de listar usuarios
    logger.info("")
    logger.info("📋 2. PROBANDO ENDPOINT DE LISTAR USUARIOS")
    logger.info("--------------------------------------------------")
    if not probar_endpoint_usuarios(admin_token):
        logger.error("❌ No se pudo listar usuarios. Abortando.")
        return

    # 3. Probar obtener usuario específico
    logger.info("")
    logger.info("👤 3. PROBANDO OBTENER USUARIO ESPECÍFICO")
    logger.info("--------------------------------------------------")
    user_id = 5  # Usuario Prueba 2
    usuario = probar_obtener_usuario(admin_token, user_id)
    if not usuario:
        logger.error("❌ No se pudo obtener el usuario. Abortando.")
        return

    # 4. Probar actualizar usuario
    logger.info("")
    logger.info("🔄 4. PROBANDO ACTUALIZAR USUARIO")
    logger.info("--------------------------------------------------")
    datos_actualizacion = {
        "is_active": False  # Cambiar estado a inactivo
    }
    usuario_actualizado = probar_actualizar_usuario(admin_token, user_id, datos_actualizacion)
    if not usuario_actualizado:
        logger.error("❌ No se pudo actualizar el usuario.")
        return

    # 5. Verificar cambio
    logger.info("")
    logger.info("🔍 5. VERIFICANDO CAMBIO")
    logger.info("--------------------------------------------------")
    usuario_verificado = probar_obtener_usuario(admin_token, user_id)
    if usuario_verificado:
        logger.info(f"   📊 Estado actual: {'Activo' if usuario_verificado['is_active'] else 'Inactivo'}")
        if usuario_verificado['is_active'] == False:
            logger.info("   ✅ Usuario desactivado correctamente")
        else:
            logger.error("   ❌ El usuario sigue activo")

    logger.info("")
    logger.info("📊 RESUMEN FINAL")
    logger.info("================================================================================")
    logger.info("🎉 PRUEBA COMPLETADA")

if __name__ == "__main__":
    main()
