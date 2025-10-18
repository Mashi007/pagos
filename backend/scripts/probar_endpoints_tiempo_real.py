# backend/scripts/probar_endpoints_tiempo_real.py
"""
PRUEBA DE ENDPOINTS EN TIEMPO REAL - TERCERA AUDITORÍA
Probar endpoints específicos con datos reales para confirmar la causa
"""
import os
import sys
import logging
import requests
import json
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def probar_endpoints_tiempo_real():
    """
    Probar endpoints específicos con datos reales
    """
    logger.info("🧪 PROBANDO ENDPOINTS EN TIEMPO REAL")
    logger.info("=" * 60)
    
    backend_url = "https://pagos-f2qf.onrender.com"
    
    # Credenciales de prueba (usar las reales)
    test_credentials = {
        "email": "itmaster@rapicreditca.com",
        "password": "R@pi_2025**",  # Usar la contraseña real
        "remember": True
    }
    
    access_token = None
    
    # 1. PROBAR LOGIN
    logger.info("🔑 1. PROBANDO LOGIN")
    logger.info("-" * 40)
    
    try:
        response = requests.post(
            f"{backend_url}/api/v1/auth/login",
            json=test_credentials,
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        
        logger.info(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get('access_token')
            user_data = data.get('user', {})
            
            logger.info("✅ LOGIN EXITOSO")
            logger.info(f"   🎫 Token obtenido: {bool(access_token)}")
            logger.info(f"   👤 Usuario: {user_data.get('nombre')} {user_data.get('apellido')}")
            logger.info(f"   📧 Email: {user_data.get('email')}")
            logger.info(f"   🔑 is_admin: {user_data.get('is_admin')}")
            logger.info(f"   ✅ is_active: {user_data.get('is_active')}")
            
            # Verificar si el usuario es admin en la respuesta del login
            if user_data.get('is_admin') is True:
                logger.info("✅ CONFIRMADO: Usuario ES admin en respuesta de login")
            else:
                logger.error("❌ PROBLEMA: Usuario NO es admin en respuesta de login")
                
        else:
            logger.error(f"❌ LOGIN FALLÓ: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en login: {e}")
        return False
    
    if not access_token:
        logger.error("❌ No se obtuvo token de acceso")
        return False
    
    # 2. PROBAR ENDPOINT /me
    logger.info("\n🔍 2. PROBANDO ENDPOINT /me")
    logger.info("-" * 40)
    
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f"{backend_url}/api/v1/auth/me",
            headers=headers,
            timeout=15
        )
        
        logger.info(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            user_data = response.json()
            
            logger.info("✅ ENDPOINT /me EXITOSO")
            logger.info(f"   🆔 ID: {user_data.get('id')}")
            logger.info(f"   📧 Email: {user_data.get('email')}")
            logger.info(f"   👤 Nombre: {user_data.get('nombre')} {user_data.get('apellido')}")
            logger.info(f"   🔑 is_admin: {user_data.get('is_admin')} ({type(user_data.get('is_admin'))})")
            logger.info(f"   ✅ is_active: {user_data.get('is_active')}")
            logger.info(f"   💼 Cargo: {user_data.get('cargo')}")
            logger.info(f"   📅 Creado: {user_data.get('created_at')}")
            logger.info(f"   🔄 Actualizado: {user_data.get('updated_at')}")
            logger.info(f"   🕐 Último login: {user_data.get('last_login')}")
            
            # Verificar permisos
            permissions = user_data.get('permissions', [])
            logger.info(f"   🔐 Permisos: {len(permissions)} permisos")
            
            # Verificar si el usuario es admin en la respuesta de /me
            if user_data.get('is_admin') is True:
                logger.info("✅ CONFIRMADO: Usuario ES admin en respuesta de /me")
            else:
                logger.error("❌ PROBLEMA: Usuario NO es admin en respuesta de /me")
                
        else:
            logger.error(f"❌ ENDPOINT /me FALLÓ: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Error en endpoint /me: {e}")
    
    # 3. PROBAR ENDPOINT DE VERIFICACIÓN DE PERMISOS
    logger.info("\n🔐 3. PROBANDO ENDPOINT DE PERMISOS")
    logger.info("-" * 40)
    
    try:
        response = requests.get(
            f"{backend_url}/api/v1/verificar-permisos/verificar-permisos-completos",
            headers=headers,
            timeout=15
        )
        
        logger.info(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            logger.info("✅ ENDPOINT DE PERMISOS EXITOSO")
            logger.info(f"   👤 Usuario: {data.get('usuario', {}).get('email')}")
            logger.info(f"   🔑 is_admin: {data.get('usuario', {}).get('is_admin')}")
            logger.info(f"   📊 Total permisos: {data.get('permisos', {}).get('total_permisos')}")
            logger.info(f"   ✅ Tiene todos los permisos: {data.get('estado', {}).get('tiene_todos_los_permisos')}")
            logger.info(f"   🔐 Es admin: {data.get('estado', {}).get('es_admin')}")
            logger.info(f"   🎯 Puede acceder todas las funciones: {data.get('estado', {}).get('puede_acceder_todas_las_funciones')}")
            
        else:
            logger.error(f"❌ ENDPOINT DE PERMISOS FALLÓ: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Error en endpoint de permisos: {e}")
    
    # 4. PROBAR ENDPOINT DE REFRESH USER
    logger.info("\n🔄 4. PROBANDO ENDPOINT DE REFRESH USER")
    logger.info("-" * 40)
    
    try:
        response = requests.post(
            f"{backend_url}/api/v1/force-refresh/force-refresh-user",
            headers=headers,
            timeout=15
        )
        
        logger.info(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            user_data = data.get('user', {})
            
            logger.info("✅ ENDPOINT REFRESH USER EXITOSO")
            logger.info(f"   📧 Email: {user_data.get('email')}")
            logger.info(f"   🔑 is_admin: {user_data.get('is_admin')}")
            logger.info(f"   🔐 Permisos: {len(user_data.get('permissions', []))}")
            
        else:
            logger.error(f"❌ ENDPOINT REFRESH USER FALLÓ: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Error en endpoint refresh user: {e}")
    
    # 5. RESUMEN FINAL
    logger.info("\n📊 RESUMEN FINAL DE PRUEBAS")
    logger.info("=" * 60)
    logger.info("✅ Pruebas de endpoints completadas")
    logger.info("💡 Revisar logs para identificar discrepancias")

if __name__ == "__main__":
    probar_endpoints_tiempo_real()
