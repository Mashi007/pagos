# backend/scripts/verificar_flujo_frontend.py
"""
VERIFICACIÓN DE FLUJO FRONTEND - CUARTA AUDITORÍA
Verificar flujo completo frontend desde login hasta header para confirmar causa raíz
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

def verificar_flujo_frontend():
    """
    Verificar flujo completo frontend desde login hasta header
    """
    logger.info("🌐 VERIFICACIÓN DE FLUJO FRONTEND COMPLETO")
    logger.info("=" * 80)
    logger.info(f"📅 Fecha y hora: {datetime.now()}")
    logger.info("🎯 Objetivo: Verificar flujo frontend desde login hasta header")
    logger.info("=" * 80)
    
    backend_url = "https://pagos-f2qf.onrender.com"
    frontend_url = "https://rapicredit.onrender.com"
    
    # Credenciales exactas
    credentials = {
        "email": "itmaster@rapicreditca.com",
        "password": "R@pi_2025**",
        "remember": True
    }
    
    # 1. VERIFICAR FRONTEND ESTÁ FUNCIONANDO
    logger.info("🌐 1. VERIFICANDO FRONTEND")
    logger.info("-" * 50)
    
    try:
        response = requests.get(frontend_url, timeout=30)
        logger.info(f"📊 Frontend Status: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("✅ Frontend está funcionando")
            logger.info(f"   📊 Tamaño respuesta: {len(response.text)} caracteres")
            
            # Verificar si hay errores JavaScript en el HTML
            if "error" in response.text.lower():
                logger.warning("⚠️ Posibles errores detectados en HTML del frontend")
            else:
                logger.info("✅ No se detectaron errores obvios en HTML")
        else:
            logger.error(f"❌ Frontend con problemas: {response.status_code}")
            
    except Exception as e:
        logger.error(f"❌ Error verificando frontend: {e}")
    
    # 2. SIMULAR LOGIN Y OBTENER TOKEN
    logger.info("\n🔐 2. SIMULANDO LOGIN PARA OBTENER TOKEN")
    logger.info("-" * 50)
    
    access_token = None
    
    try:
        response = requests.post(
            f"{backend_url}/api/v1/auth/login",
            json=credentials,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            login_data = response.json()
            access_token = login_data.get('access_token')
            user_data = login_data.get('user', {})
            
            logger.info("✅ Login exitoso")
            logger.info(f"   🔑 Token obtenido: {bool(access_token)}")
            logger.info(f"   👤 Usuario: {user_data.get('nombre')} {user_data.get('apellido')}")
            logger.info(f"   🔑 is_admin: {user_data.get('is_admin')}")
            
        else:
            logger.error(f"❌ Login falló: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en login: {e}")
        return False
    
    # 3. VERIFICAR ENDPOINT /me (lo que usa el frontend)
    logger.info("\n🔍 3. VERIFICANDO ENDPOINT /me (USADO POR FRONTEND)")
    logger.info("-" * 50)
    
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        response = requests.get(
            f"{backend_url}/api/v1/auth/me",
            headers=headers,
            timeout=30
        )
        
        logger.info(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            me_data = response.json()
            
            logger.info("✅ Endpoint /me exitoso")
            logger.info(f"   📧 Email: {me_data.get('email')}")
            logger.info(f"   👤 Nombre: {me_data.get('nombre')} {me_data.get('apellido')}")
            logger.info(f"   🔑 is_admin: {me_data.get('is_admin')} ({type(me_data.get('is_admin'))})")
            logger.info(f"   🔐 Permisos: {len(me_data.get('permissions', []))}")
            
            # Verificar campos críticos
            critical_fields = ['id', 'email', 'nombre', 'apellido', 'is_admin', 'is_active', 'permissions']
            missing_fields = []
            
            for field in critical_fields:
                if field not in me_data:
                    missing_fields.append(field)
            
            if missing_fields:
                logger.error(f"❌ Campos faltantes en /me: {missing_fields}")
            else:
                logger.info("✅ Todos los campos críticos están presentes")
            
        else:
            logger.error(f"❌ Endpoint /me falló: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Error en endpoint /me: {e}")
    
    # 4. VERIFICAR CONFIGURACIÓN CORS
    logger.info("\n🌐 4. VERIFICANDO CONFIGURACIÓN CORS")
    logger.info("-" * 50)
    
    try:
        # Simular preflight request
        headers = {
            'Origin': frontend_url,
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'Authorization, Content-Type'
        }
        
        response = requests.options(
            f"{backend_url}/api/v1/auth/me",
            headers=headers,
            timeout=30
        )
        
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
        
        # Verificar si CORS está configurado correctamente
        if cors_headers['Access-Control-Allow-Origin'] in ['*', frontend_url]:
            logger.info("✅ CORS configurado correctamente")
        else:
            logger.warning(f"⚠️ CORS puede tener problemas: {cors_headers['Access-Control-Allow-Origin']}")
            
    except Exception as e:
        logger.error(f"❌ Error verificando CORS: {e}")
    
    # 5. SIMULAR ALMACENAMIENTO FRONTEND
    logger.info("\n💾 5. SIMULANDO ALMACENAMIENTO FRONTEND")
    logger.info("-" * 50)
    
    # Simular lo que haría el frontend con los datos
    if me_data:
        logger.info("📊 Datos que el frontend recibiría:")
        logger.info(f"   🆔 ID: {me_data.get('id')}")
        logger.info(f"   📧 Email: {me_data.get('email')}")
        logger.info(f"   👤 Nombre: {me_data.get('nombre')}")
        logger.info(f"   👤 Apellido: {me_data.get('apellido')}")
        logger.info(f"   🔑 is_admin: {me_data.get('is_admin')}")
        logger.info(f"   ✅ is_active: {me_data.get('is_active')}")
        
        # Simular lógica del header
        is_admin = me_data.get('is_admin')
        user_role = "Administrador" if is_admin else "Usuario"
        
        logger.info(f"\n🎭 SIMULACIÓN DE LÓGICA DEL HEADER:")
        logger.info(f"   🔑 is_admin: {is_admin}")
        logger.info(f"   🎭 user_role calculado: {user_role}")
        
        if is_admin is True:
            logger.info("✅ LÓGICA CORRECTA: Debería mostrar 'Administrador'")
        elif is_admin is False:
            logger.error("❌ LÓGICA CORRECTA: Debería mostrar 'Usuario'")
        else:
            logger.error(f"❌ LÓGICA PROBLEMÁTICA: Valor inválido {is_admin}")
    
    # 6. VERIFICAR ENDPOINTS DE DEBUG
    logger.info("\n🔧 6. VERIFICANDO ENDPOINTS DE DEBUG")
    logger.info("-" * 50)
    
    debug_endpoints = [
        "/api/v1/log-test/force-logs",
        "/api/v1/verificar-permisos/verificar-permisos-completos",
        "/api/v1/force-refresh/force-refresh-user"
    ]
    
    for endpoint in debug_endpoints:
        try:
            response = requests.get(
                f"{backend_url}{endpoint}",
                headers=headers if access_token else {},
                timeout=15
            )
            
            logger.info(f"   🔧 {endpoint}: {response.status_code}")
            
        except Exception as e:
            logger.error(f"   ❌ {endpoint}: Error - {e}")
    
    # 7. CONCLUSIÓN FINAL
    logger.info("\n📊 CONCLUSIÓN FINAL DEL FLUJO FRONTEND")
    logger.info("=" * 80)
    
    logger.info("🎯 RESULTADOS DE LA VERIFICACIÓN:")
    logger.info(f"   🌐 Frontend funcionando: {response.status_code == 200}")
    logger.info(f"   🔐 Login exitoso: {access_token is not None}")
    logger.info(f"   🔍 Endpoint /me funcional: {me_data is not None}")
    logger.info(f"   🔑 is_admin en datos: {me_data.get('is_admin') if me_data else 'N/A'}")
    
    if me_data and me_data.get('is_admin') is True:
        logger.info("✅ DIAGNÓSTICO: Backend retorna datos correctos")
        logger.info("🔍 CAUSA PROBABLE: Problema en frontend o caché")
        logger.info("💡 SOLUCIÓN: Verificar frontend y limpiar caché")
    elif me_data and me_data.get('is_admin') is False:
        logger.error("❌ DIAGNÓSTICO: Backend retorna datos incorrectos")
        logger.error("🔍 CAUSA PROBABLE: Problema en backend/BD")
        logger.error("💡 SOLUCIÓN: Corregir datos en backend/BD")
    else:
        logger.error("❌ DIAGNÓSTICO: Datos inconsistentes o faltantes")
        logger.error("🔍 CAUSA: Problema en comunicación frontend-backend")
        logger.error("💡 SOLUCIÓN: Verificar comunicación y endpoints")
    
    return True

if __name__ == "__main__":
    verificar_flujo_frontend()
