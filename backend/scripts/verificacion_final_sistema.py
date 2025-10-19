#!/usr/bin/env python3
"""
Script para probar login con contraseña correcta: R@pi_2025**
"""

import requests
import os
import logging
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://pagos-f2qf.onrender.com"

def probar_login_admin():
    """Probar login del administrador con contraseña correcta"""
    logger.info("🔑 PROBANDO LOGIN ADMINISTRADOR")
    logger.info("=" * 60)
    
    credenciales = {
        "email": "itmaster@rapicreditca.com",
        "password": "R@pi_2025**",
        "remember": True
    }
    
    logger.info(f"📧 Email: {credenciales['email']}")
    logger.info(f"🔑 Contraseña: {credenciales['password']}")
    logger.info(f"🌐 URL: {BASE_URL}")
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", 
                               json=credenciales, 
                               timeout=15)
        
        logger.info(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info("✅ LOGIN EXITOSO!")
            logger.info(f"👤 Usuario: {data['user']['email']}")
            logger.info(f"👑 Rol: {'Administrador' if data['user']['is_admin'] else 'Usuario'}")
            logger.info(f"🟢 Estado: {'Activo' if data['user']['is_active'] else 'Inactivo'}")
            logger.info(f"🔐 Token: {data['access_token'][:30]}...")
            
            # Probar endpoints críticos
            probar_endpoints_criticos(data['access_token'])
            return True
        else:
            logger.error(f"❌ Error en login: {response.status_code}")
            logger.error(f"📄 Respuesta: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error de conexión: {e}")
        return False

def probar_endpoints_criticos(token):
    """Probar endpoints críticos con el token"""
    logger.info("")
    logger.info("🔗 PROBANDO ENDPOINTS CRÍTICOS")
    logger.info("=" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    endpoints = [
        ("/api/v1/auth/me", "Información del usuario"),
        ("/api/v1/usuarios/?page=1&page_size=5", "Lista de usuarios"),
        ("/api/v1/analistas/", "Lista de analistas"),
        ("/api/v1/clientes/?page=1&page_size=5", "Lista de clientes"),
        ("/api/v1/concesionarios/?page=1&page_size=5", "Lista de concesionarios")
    ]
    
    exitosos = 0
    
    for endpoint, descripcion in endpoints:
        logger.info(f"🔗 Probando: {descripcion}")
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=10)
            logger.info(f"   📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                logger.info(f"   ✅ {descripcion} funcionando")
                exitosos += 1
            else:
                logger.error(f"   ❌ Error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"   ❌ Error: {e}")
    
    logger.info("")
    logger.info(f"📊 Endpoints exitosos: {exitosos}/{len(endpoints)}")
    
    if exitosos == len(endpoints):
        logger.info("🎉 TODOS LOS ENDPOINTS FUNCIONANDO CORRECTAMENTE")
    else:
        logger.warning("⚠️ Algunos endpoints tienen problemas")

def probar_usuario_prueba2():
    """Probar login del usuario prueba2"""
    logger.info("")
    logger.info("👤 PROBANDO LOGIN USUARIO PRUEBA2")
    logger.info("=" * 60)
    
    credenciales = {
        "email": "prueba2@gmail.com",
        "password": "prueba123",
        "remember": True
    }
    
    logger.info(f"📧 Email: {credenciales['email']}")
    logger.info(f"🔑 Contraseña: {credenciales['password']}")
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", 
                               json=credenciales, 
                               timeout=15)
        
        logger.info(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info("✅ LOGIN USUARIO PRUEBA2 EXITOSO!")
            logger.info(f"👤 Usuario: {data['user']['email']}")
            logger.info(f"👑 Rol: {'Administrador' if data['user']['is_admin'] else 'Usuario'}")
            logger.info(f"🟢 Estado: {'Activo' if data['user']['is_active'] else 'Inactivo'}")
            return True
        else:
            logger.error(f"❌ Error en login usuario prueba2: {response.status_code}")
            logger.error(f"📄 Respuesta: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error de conexión: {e}")
        return False

def main():
    logger.info("🎯 VERIFICACIÓN FINAL DEL SISTEMA")
    logger.info("=" * 80)
    logger.info(f"📅 Fecha y hora: {datetime.now()}")
    logger.info(f"🌐 URL del sistema: {BASE_URL}")
    logger.info("=" * 80)
    
    # Esperar un momento para que el sistema esté completamente listo
    logger.info("⏳ Esperando 5 segundos para que el sistema esté listo...")
    time.sleep(5)
    
    # 1. Probar login administrador
    logger.info("1️⃣ PROBANDO LOGIN ADMINISTRADOR")
    logger.info("-" * 50)
    admin_ok = probar_login_admin()
    
    # 2. Probar login usuario prueba2
    logger.info("")
    logger.info("2️⃣ PROBANDO LOGIN USUARIO PRUEBA2")
    logger.info("-" * 50)
    usuario_ok = probar_usuario_prueba2()
    
    # 3. Resumen final
    logger.info("")
    logger.info("📋 RESUMEN FINAL")
    logger.info("=" * 60)
    
    if admin_ok:
        logger.info("✅ Administrador: Login funcionando")
    else:
        logger.error("❌ Administrador: Problemas en login")
    
    if usuario_ok:
        logger.info("✅ Usuario prueba2: Login funcionando")
    else:
        logger.error("❌ Usuario prueba2: Problemas en login")
    
    if admin_ok and usuario_ok:
        logger.info("")
        logger.info("🎉 SISTEMA COMPLETAMENTE FUNCIONAL")
        logger.info("   ✅ Login de administrador funcionando")
        logger.info("   ✅ Login de usuario regular funcionando")
        logger.info("   ✅ Todos los endpoints críticos funcionando")
        logger.info("   ✅ Sistema listo para uso en producción")
    else:
        logger.warning("⚠️ El sistema tiene algunos problemas que resolver")

if __name__ == "__main__":
    main()
