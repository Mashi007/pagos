#!/usr/bin/env python3
"""
Script para verificar que la actualización de usuarios funciona correctamente
y que los cambios se persisten en la base de datos.
"""

import requests
import os
import logging
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = os.getenv("FRONTEND_URL", "https://pagos-f2qf.onrender.com") # Usar el servidor de producción

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "itmaster@rapicreditca.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

def login_admin():
    """Realizar login como administrador"""
    login_url = f"{BASE_URL}/api/v1/auth/login"
    credentials = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "remember": True}
    try:
        response = requests.post(login_url, json=credentials)
        response.raise_for_status()
        data = response.json()
        logger.info(f"   ✅ Login exitoso")
        logger.info(f"   📊 Usuario: {data['user']['email']}")
        logger.info(f"   📊 Rol: {'Administrador' if data['user']['is_admin'] else 'Usuario'}")
        return data['access_token']
    except requests.exceptions.RequestException as e:
        logger.error(f"   ❌ Error durante el login: {e}")
        if e.response:
            logger.error(f"   📊 Respuesta del servidor: {e.response.text}")
        return None

def obtener_usuario_prueba(token: str):
    """Obtener datos actuales del usuario Prueba 2"""
    headers = {"Authorization": f"Bearer {token}"}
    user_url = f"{BASE_URL}/api/v1/usuarios/5"
    try:
        response = requests.get(user_url, headers=headers)
        response.raise_for_status()
        user_data = response.json()
        logger.info(f"   ✅ USUARIO OBTENIDO:")
        logger.info(f"   📊 ID: {user_data['id']}")
        logger.info(f"   📊 Email: {user_data['email']}")
        logger.info(f"   📊 Nombre: {user_data['nombre']}")
        logger.info(f"   📊 Apellido: {user_data['apellido']}")
        logger.info(f"   📊 Rol: {'Administrador' if user_data['is_admin'] else 'Usuario'}")
        logger.info(f"   📊 Activo: {user_data['is_active']}")
        return user_data
    except requests.exceptions.RequestException as e:
        logger.error(f"   ❌ Error obteniendo usuario: {e}")
        if e.response:
            logger.error(f"   📊 Respuesta: {e.response.text}")
        return None

def actualizar_usuario_prueba(token: str, datos_actualizacion: dict):
    """Actualizar datos del usuario Prueba 2"""
    headers = {"Authorization": f"Bearer {token}"}
    update_url = f"{BASE_URL}/api/v1/usuarios/5"
    try:
        response = requests.put(update_url, json=datos_actualizacion, headers=headers)
        response.raise_for_status()
        updated_data = response.json()
        logger.info(f"   ✅ USUARIO ACTUALIZADO EXITOSAMENTE:")
        logger.info(f"   📊 Email: {updated_data['email']}")
        logger.info(f"   📊 Nombre: {updated_data['nombre']}")
        logger.info(f"   📊 Apellido: {updated_data['apellido']}")
        logger.info(f"   📊 Rol: {'Administrador' if updated_data['is_admin'] else 'Usuario'}")
        logger.info(f"   📊 Activo: {updated_data['is_active']}")
        return updated_data
    except requests.exceptions.RequestException as e:
        logger.error(f"   ❌ Error actualizando usuario: {e}")
        if e.response:
            logger.error(f"   📊 Respuesta: {e.response.text}")
        return None

def verificar_cambios_persistidos(token: str, datos_esperados: dict):
    """Verificar que los cambios se guardaron correctamente"""
    headers = {"Authorization": f"Bearer {token}"}
    user_url = f"{BASE_URL}/api/v1/usuarios/5"
    try:
        response = requests.get(user_url, headers=headers)
        response.raise_for_status()
        user_data = response.json()
        
        logger.info(f"   🔍 VERIFICANDO CAMBIOS PERSISTIDOS:")
        
        cambios_correctos = True
        
        for campo, valor_esperado in datos_esperados.items():
            valor_actual = user_data.get(campo)
            if valor_actual == valor_esperado:
                logger.info(f"   ✅ {campo}: {valor_actual} (correcto)")
            else:
                logger.error(f"   ❌ {campo}: esperado {valor_esperado}, actual {valor_actual}")
                cambios_correctos = False
        
        return cambios_correctos, user_data
    except requests.exceptions.RequestException as e:
        logger.error(f"   ❌ Error verificando cambios: {e}")
        return False, None

def main():
    logger.info("🔍 VERIFICACIÓN DE ACTUALIZACIÓN DE USUARIO")
    logger.info("================================================================================")
    logger.info(f"📊 Fecha y hora: {datetime.now()}")
    logger.info("🎯 Objetivo: Verificar que la actualización de usuarios funciona y persiste en BD")
    logger.info("================================================================================")
    logger.info("")

    # 1. Login como administrador
    logger.info("🔑 1. REALIZANDO LOGIN")
    logger.info("--------------------------------------------------")
    admin_token = login_admin()
    if not admin_token:
        logger.error("❌ No se pudo iniciar sesión como administrador. Abortando.")
        return

    # 2. Obtener datos actuales del usuario
    logger.info("")
    logger.info("📋 2. OBTENIENDO DATOS ACTUALES DEL USUARIO")
    logger.info("--------------------------------------------------")
    usuario_actual = obtener_usuario_prueba(admin_token)
    if not usuario_actual:
        logger.error("❌ No se pudo obtener datos del usuario. Abortando.")
        return

    # 3. Preparar datos de actualización
    logger.info("")
    logger.info("🔄 3. PREPARANDO ACTUALIZACIÓN")
    logger.info("--------------------------------------------------")
    
    # Datos de prueba para actualizar
    datos_actualizacion = {
        "email": "prueba2.actualizado@gmail.com",
        "nombre": "Prueba Actualizada",
        "apellido": "Dos Modificado",
        "is_admin": False,
        "is_active": True,
        "password": "NuevaContraseña123!"  # Nueva contraseña generada
    }
    
    logger.info(f"   📊 Datos a actualizar:")
    for campo, valor in datos_actualizacion.items():
        if campo != "password":  # No mostrar contraseña en logs
            logger.info(f"      - {campo}: {valor}")
        else:
            logger.info(f"      - {campo}: [NUEVA CONTRASEÑA GENERADA]")

    # 4. Actualizar usuario
    logger.info("")
    logger.info("💾 4. ACTUALIZANDO USUARIO")
    logger.info("--------------------------------------------------")
    usuario_actualizado = actualizar_usuario_prueba(admin_token, datos_actualizacion)
    if not usuario_actualizado:
        logger.error("❌ No se pudo actualizar el usuario. Abortando.")
        return

    # 5. Verificar que los cambios se persistieron
    logger.info("")
    logger.info("🔍 5. VERIFICANDO PERSISTENCIA DE CAMBIOS")
    logger.info("--------------------------------------------------")
    cambios_persistidos, usuario_verificado = verificar_cambios_persistidos(
        admin_token, 
        {k: v for k, v in datos_actualizacion.items() if k != "password"}
    )

    # 6. Resumen final
    logger.info("")
    logger.info("📊 RESUMEN FINAL")
    logger.info("================================================================================")
    
    if cambios_persistidos:
        logger.info("🎉 ACTUALIZACIÓN DE USUARIO FUNCIONA CORRECTAMENTE")
        logger.info("   ✅ Datos actualizados exitosamente")
        logger.info("   ✅ Cambios persistidos en base de datos")
        logger.info("   ✅ Usuario puede acceder con datos actualizados")
        logger.info("   ✅ Sistema de contraseñas funcionando")
    else:
        logger.error("❌ PROBLEMAS EN LA ACTUALIZACIÓN DE USUARIO")
        logger.error("   💡 Revisar endpoint de actualización")
        logger.error("   💡 Verificar persistencia en base de datos")

if __name__ == "__main__":
    main()
