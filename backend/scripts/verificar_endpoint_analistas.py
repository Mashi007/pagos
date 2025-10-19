# backend/scripts/verificar_endpoint_analistas.py
"""
VERIFICACIÓN DIRECTA DEL ENDPOINT ANALISTAS - ENFOQUE 1
Verificar que el endpoint /api/v1/analistas funciona correctamente después de la corrección
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

def verificar_endpoint_analistas():
    """
    Verificar que el endpoint /api/v1/analistas funciona correctamente
    """
    logger.info("🔍 VERIFICACIÓN DIRECTA DEL ENDPOINT ANALISTAS")
    logger.info("=" * 80)
    logger.info(f"📅 Fecha y hora: {datetime.now()}")
    logger.info("🎯 Objetivo: Verificar que el endpoint /api/v1/analistas funciona después de la corrección")
    logger.info("=" * 80)
    
    backend_url = "https://pagos-f2qf.onrender.com"
    
    # Credenciales para autenticación
    credentials = {
        "email": "itmaster@rapicreditca.com",
        "password": "R@pi_2025**",
        "remember": True
    }
    
    # 1. OBTENER TOKEN DE AUTENTICACIÓN
    logger.info("🔐 1. OBTENIENDO TOKEN DE AUTENTICACIÓN")
    logger.info("-" * 50)
    
    access_token = None
    
    try:
        response = requests.post(
            f"{backend_url}/api/v1/auth/login",
            json=credentials,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        logger.info(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            login_data = response.json()
            access_token = login_data.get('access_token')
            
            logger.info("✅ LOGIN EXITOSO")
            logger.info(f"   🎫 Token obtenido: {bool(access_token)}")
            logger.info(f"   👤 Usuario: {login_data.get('user', {}).get('nombre')} {login_data.get('user', {}).get('apellido')}")
            logger.info(f"   🔑 is_admin: {login_data.get('user', {}).get('is_admin')}")
            
        else:
            logger.error(f"❌ LOGIN FALLÓ: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en login: {e}")
        return False
    
    # 2. PROBAR ENDPOINT ANALISTAS CON AUTENTICACIÓN
    logger.info("\n🔍 2. PROBANDO ENDPOINT ANALISTAS CON AUTENTICACIÓN")
    logger.info("-" * 50)
    
    if not access_token:
        logger.error("❌ No hay token de acceso para probar analistas")
        return False
    
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Probar endpoint principal
        response = requests.get(
            f"{backend_url}/api/v1/analistas",
            headers=headers,
            timeout=30
        )
        
        logger.info(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            analistas_data = response.json()
            
            logger.info("✅ ENDPOINT ANALISTAS EXITOSO")
            logger.info(f"   📊 Total analistas: {analistas_data.get('total', 0)}")
            logger.info(f"   📊 Items recibidos: {len(analistas_data.get('items', []))}")
            logger.info(f"   📊 Página: {analistas_data.get('page', 1)}")
            logger.info(f"   📊 Tamaño página: {analistas_data.get('size', 0)}")
            logger.info(f"   📊 Total páginas: {analistas_data.get('pages', 0)}")
            
            # Mostrar algunos analistas si existen
            items = analistas_data.get('items', [])
            if items:
                logger.info(f"\n📋 PRIMEROS ANALISTAS:")
                for i, analista in enumerate(items[:3]):  # Mostrar solo los primeros 3
                    logger.info(f"   {i+1}. ID: {analista.get('id')}, Nombre: {analista.get('nombre')} {analista.get('apellido')}")
                    logger.info(f"      Email: {analista.get('email')}, Activo: {analista.get('activo')}")
            else:
                logger.info("   📋 No hay analistas en la base de datos")
            
        elif response.status_code == 405:
            logger.error("❌ ERROR 405 METHOD NOT ALLOWED - La corrección no fue aplicada")
            logger.error("   🔍 CAUSA: El endpoint aún tiene problemas de sintaxis")
            logger.error("   💡 SOLUCIÓN: Verificar que el despliegue se completó correctamente")
            return False
        else:
            logger.error(f"❌ ENDPOINT ANALISTAS FALLÓ: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en endpoint analistas: {e}")
        return False
    
    # 3. PROBAR ENDPOINT SIN AUTENTICACIÓN (TEST)
    logger.info("\n🧪 3. PROBANDO ENDPOINT SIN AUTENTICACIÓN (TEST)")
    logger.info("-" * 50)
    
    try:
        response = requests.get(
            f"{backend_url}/api/v1/analistas/test-simple",
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        logger.info(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            test_data = response.json()
            
            logger.info("✅ ENDPOINT TEST EXITOSO")
            logger.info(f"   📊 Success: {test_data.get('success')}")
            logger.info(f"   📊 Total analistas: {test_data.get('total_analistas', 0)}")
            logger.info(f"   📊 Message: {test_data.get('message')}")
            
        else:
            logger.error(f"❌ ENDPOINT TEST FALLÓ: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Error en endpoint test: {e}")
    
    # 4. PROBAR ENDPOINT LIST-NO-AUTH
    logger.info("\n🔓 4. PROBANDO ENDPOINT LIST-NO-AUTH")
    logger.info("-" * 50)
    
    try:
        response = requests.get(
            f"{backend_url}/api/v1/analistas/list-no-auth",
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        logger.info(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            list_data = response.json()
            
            logger.info("✅ ENDPOINT LIST-NO-AUTH EXITOSO")
            logger.info(f"   📊 Total analistas: {list_data.get('total', 0)}")
            logger.info(f"   📊 Items recibidos: {len(list_data.get('items', []))}")
            
        else:
            logger.error(f"❌ ENDPOINT LIST-NO-AUTH FALLÓ: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Error en endpoint list-no-auth: {e}")
    
    # 5. CONCLUSIÓN FINAL
    logger.info("\n📊 CONCLUSIÓN FINAL DE VERIFICACIÓN DIRECTA")
    logger.info("=" * 80)
    
    logger.info("🎯 RESULTADOS DE LA VERIFICACIÓN DIRECTA:")
    logger.info(f"   🔐 Login exitoso: {access_token is not None}")
    logger.info(f"   🔍 Endpoint analistas funcional: {response.status_code == 200 if 'response' in locals() else False}")
    logger.info(f"   🧪 Endpoint test funcional: {test_data.get('success') if 'test_data' in locals() else False}")
    logger.info(f"   🔓 Endpoint list-no-auth funcional: {list_data.get('total') is not None if 'list_data' in locals() else False}")
    
    if access_token and response.status_code == 200:
        logger.info("\n✅ VERIFICACIÓN DIRECTA EXITOSA:")
        logger.info("   🎯 El endpoint /api/v1/analistas funciona correctamente")
        logger.info("   🎯 La corrección fue aplicada exitosamente")
        logger.info("   🎯 El error 405 Method Not Allowed está resuelto")
        logger.info("   🎯 El frontend podrá cargar datos de analistas")
        return True
    else:
        logger.error("\n❌ VERIFICACIÓN DIRECTA FALLIDA:")
        logger.error("   🔍 El endpoint /api/v1/analistas aún tiene problemas")
        logger.error("   🔍 La corrección no fue aplicada correctamente")
        logger.error("   🔍 El error 405 Method Not Allowed persiste")
        return False

if __name__ == "__main__":
    verificar_endpoint_analistas()
