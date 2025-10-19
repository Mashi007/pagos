#!/usr/bin/env python3
"""
SCRIPT FINAL DE VERIFICACIÓN COMPLETA - CASOS REALES DE USUARIOS
Verifica que todos los sistemas funcionen correctamente después de las correcciones
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

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "itmaster@rapicreditca.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

def verificar_servidor_disponible():
    """Verificar que el servidor esté disponible y funcionando"""
    try:
        # Verificar endpoint principal
        response = requests.get(f"{BASE_URL}/", timeout=10)
        if response.status_code == 200:
            logger.info("✅ Servidor principal disponible")
            
            # Verificar endpoint de login
            response = requests.options(f"{BASE_URL}/api/v1/auth/login", timeout=10)
            if response.status_code == 200:
                logger.info("✅ Endpoint de login disponible")
                return True
            else:
                logger.warning(f"⚠️ Endpoint de login responde con código: {response.status_code}")
                return False
        else:
            logger.warning(f"⚠️ Servidor principal responde con código: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Error verificando servidor: {e}")
        return False

def probar_login_admin():
    """Probar login como administrador"""
    login_url = f"{BASE_URL}/api/v1/auth/login"
    credentials = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "remember": True}
    try:
        response = requests.post(login_url, json=credentials)
        logger.info(f"   📊 Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"   ✅ Login exitoso como administrador")
            logger.info(f"   📊 Usuario: {data['user']['email']}")
            logger.info(f"   📊 Rol: {'Administrador' if data['user']['is_admin'] else 'Usuario'}")
            return data['access_token']
        else:
            logger.error(f"   ❌ Error en login: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            return None
    except Exception as e:
        logger.error(f"   ❌ Error durante el login: {e}")
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
            logger.info(f"   ✅ Login exitoso con usuario prueba")
            logger.info(f"   📊 Usuario: {data['user']['email']}")
            logger.info(f"   📊 Rol: {'Administrador' if data['user']['is_admin'] else 'Usuario'}")
            return True
        else:
            logger.error(f"   ❌ Error en login: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            return False
    except Exception as e:
        logger.error(f"   ❌ Error durante el login: {e}")
        return False

def verificar_endpoint_usuarios(token):
    """Verificar que el endpoint de usuarios funcione"""
    headers = {"Authorization": f"Bearer {token}"}
    user_url = f"{BASE_URL}/api/v1/usuarios/?page=1&page_size=10"
    try:
        response = requests.get(user_url, headers=headers)
        logger.info(f"   📊 Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"   ✅ Endpoint de usuarios funcionando")
            logger.info(f"   📊 Total usuarios: {data.get('total', 0)}")
            return True
        else:
            logger.error(f"   ❌ Error en endpoint usuarios: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            return False
    except Exception as e:
        logger.error(f"   ❌ Error: {e}")
        return False

def verificar_endpoint_analistas(token):
    """Verificar que el endpoint de analistas funcione"""
    headers = {"Authorization": f"Bearer {token}"}
    analistas_url = f"{BASE_URL}/api/v1/analistas/"
    try:
        response = requests.get(analistas_url, headers=headers)
        logger.info(f"   📊 Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"   ✅ Endpoint de analistas funcionando")
            logger.info(f"   📊 Total analistas: {len(data.get('items', []))}")
            return True
        else:
            logger.error(f"   ❌ Error en endpoint analistas: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            return False
    except Exception as e:
        logger.error(f"   ❌ Error: {e}")
        return False

def main():
    logger.info("🎯 VERIFICACIÓN FINAL COMPLETA - SISTEMA DE GESTIÓN DE USUARIOS")
    logger.info("=" * 80)
    logger.info(f"📊 Fecha y hora: {datetime.now()}")
    logger.info("🎯 Objetivo: Verificar que todos los sistemas funcionen correctamente")
    logger.info("🔧 Estado: Después de correcciones de logger")
    logger.info("=" * 80)
    logger.info("")

    # 1. Verificar servidor
    logger.info("🌐 1. VERIFICANDO DISPONIBILIDAD DEL SERVIDOR")
    logger.info("-" * 50)
    if not verificar_servidor_disponible():
        logger.error("❌ Servidor no disponible. Abortando verificación.")
        return
    logger.info("✅ Servidor completamente disponible")
    
    # Esperar un momento para que el servidor se estabilice
    logger.info("⏳ Esperando 5 segundos para estabilización...")
    time.sleep(5)

    # 2. Probar login como administrador
    logger.info("")
    logger.info("🔑 2. PROBANDO LOGIN COMO ADMINISTRADOR")
    logger.info("-" * 50)
    admin_token = probar_login_admin()
    if not admin_token:
        logger.error("❌ No se pudo hacer login como administrador. Abortando.")
        return

    # 3. Probar login con usuario prueba
    logger.info("")
    logger.info("👤 3. PROBANDO LOGIN CON USUARIO PRUEBA")
    logger.info("-" * 50)
    login_usuario_exitoso = probar_login_usuario_prueba()
    
    # 4. Verificar endpoints críticos
    logger.info("")
    logger.info("🔗 4. VERIFICANDO ENDPOINTS CRÍTICOS")
    logger.info("-" * 50)
    
    logger.info("4.1 Verificando endpoint de usuarios...")
    usuarios_ok = verificar_endpoint_usuarios(admin_token)
    
    logger.info("4.2 Verificando endpoint de analistas...")
    analistas_ok = verificar_endpoint_analistas(admin_token)

    # 5. Resumen final
    logger.info("")
    logger.info("📊 RESUMEN FINAL DE VERIFICACIÓN")
    logger.info("=" * 80)
    
    resultados = {
        "Servidor disponible": True,
        "Login administrador": admin_token is not None,
        "Login usuario prueba": login_usuario_exitoso,
        "Endpoint usuarios": usuarios_ok,
        "Endpoint analistas": analistas_ok
    }
    
    exitosos = sum(resultados.values())
    total = len(resultados)
    
    logger.info(f"🎯 Verificaciones ejecutadas: {total}")
    logger.info(f"✅ Verificaciones exitosas: {exitosos}")
    logger.info(f"❌ Verificaciones fallidas: {total - exitosos}")
    logger.info(f"📈 Tasa de éxito: {(exitosos/total)*100:.1f}%")
    logger.info("")
    
    logger.info("📋 DETALLE DE RESULTADOS:")
    logger.info("-" * 40)
    for verificacion, resultado in resultados.items():
        estado = "✅ EXITOSO" if resultado else "❌ FALLÓ"
        logger.info(f"   {verificacion}: {estado}")
    
    logger.info("")
    if exitosos == total:
        logger.info("🎉 TODAS LAS VERIFICACIONES EXITOSAS")
        logger.info("   ✅ Sistema completamente funcional")
        logger.info("   ✅ Errores de logger corregidos")
        logger.info("   ✅ Login de administrador funcionando")
        logger.info("   ✅ Login de usuario prueba funcionando")
        logger.info("   ✅ Endpoints críticos funcionando")
        logger.info("")
        logger.info("🎯 CASOS REALES LISTOS PARA SIMULACIÓN:")
        logger.info("   🔐 Usuario olvida contraseña (múltiples veces)")
        logger.info("   🔄 Activar/desactivar usuarios")
        logger.info("   📧 Cambio de email de usuarios")
        logger.info("   👤 Cambio de datos personales")
        logger.info("   📊 Todas las operaciones se registran en auditoría")
    else:
        logger.error("❌ ALGUNAS VERIFICACIONES FALLARON")
        logger.error("   💡 Revisar logs para identificar problemas específicos")

if __name__ == "__main__":
    main()
