# backend/scripts/simular_login_completo.py
"""
SIMULACIÓN COMPLETA DE LOGIN - CUARTA AUDITORÍA
Simular login completo y capturar respuesta exacta para verificar causa raíz
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

def simular_login_completo():
    """
    Simular login completo y capturar respuesta exacta
    """
    logger.info("🔐 SIMULACIÓN COMPLETA DE LOGIN")
    logger.info("=" * 80)
    logger.info(f"📅 Fecha y hora: {datetime.now()}")
    logger.info("🎯 Objetivo: Capturar respuesta exacta del login")
    logger.info("=" * 80)
    
    backend_url = "https://pagos-f2qf.onrender.com"
    
    # Credenciales exactas del usuario reportado
    credentials = {
        "email": "itmaster@rapicreditca.com",
        "password": "R@pi_2025**",
        "remember": True
    }
    
    logger.info(f"🔑 Credenciales a usar:")
    logger.info(f"   📧 Email: {credentials['email']}")
    logger.info(f"   🔐 Password: {'*' * len(credentials['password'])}")
    logger.info(f"   💾 Remember: {credentials['remember']}")
    
    # 1. SIMULAR LOGIN
    logger.info("\n🔐 1. SIMULANDO LOGIN")
    logger.info("-" * 50)
    
    try:
        response = requests.post(
            f"{backend_url}/api/v1/auth/login",
            json=credentials,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            timeout=30
        )
        
        logger.info(f"📊 Status Code: {response.status_code}")
        logger.info(f"📊 Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            login_data = response.json()
            
            logger.info("✅ LOGIN EXITOSO - DATOS RECIBIDOS:")
            logger.info(f"   🎫 Access Token: {login_data.get('access_token', 'N/A')[:20]}...")
            logger.info(f"   🔄 Refresh Token: {login_data.get('refresh_token', 'N/A')[:20]}...")
            logger.info(f"   🏷️ Token Type: {login_data.get('token_type', 'N/A')}")
            
            # Analizar datos del usuario en la respuesta de login
            user_data = login_data.get('user', {})
            logger.info("\n👤 DATOS DEL USUARIO EN RESPUESTA DE LOGIN:")
            logger.info(f"   🆔 ID: {user_data.get('id')} ({type(user_data.get('id'))})")
            logger.info(f"   📧 Email: {user_data.get('email')} ({type(user_data.get('email'))})")
            logger.info(f"   👤 Nombre: {user_data.get('nombre')} ({type(user_data.get('nombre'))})")
            logger.info(f"   👤 Apellido: {user_data.get('apellido')} ({type(user_data.get('apellido'))})")
            logger.info(f"   💼 Cargo: {user_data.get('cargo')} ({type(user_data.get('cargo'))})")
            logger.info(f"   🔑 is_admin: {user_data.get('is_admin')} ({type(user_data.get('is_admin'))})")
            logger.info(f"   ✅ is_active: {user_data.get('is_active')} ({type(user_data.get('is_active'))})")
            logger.info(f"   📅 Creado: {user_data.get('created_at')} ({type(user_data.get('created_at'))})")
            logger.info(f"   🔄 Actualizado: {user_data.get('updated_at')} ({type(user_data.get('updated_at'))})")
            logger.info(f"   🕐 Último login: {user_data.get('last_login')} ({type(user_data.get('last_login'))})")
            
            # Verificar is_admin en respuesta de login
            is_admin_login = user_data.get('is_admin')
            logger.info(f"\n🔑 ANÁLISIS CRÍTICO DE is_admin EN LOGIN:")
            logger.info(f"   📊 Valor: {is_admin_login}")
            logger.info(f"   📊 Tipo: {type(is_admin_login)}")
            
            if is_admin_login is True:
                logger.info("✅ CONFIRMADO: Usuario ES admin en respuesta de login")
            elif is_admin_login is False:
                logger.error("❌ PROBLEMA: Usuario NO es admin en respuesta de login")
            else:
                logger.error(f"❌ PROBLEMA: Valor is_admin inválido en login: {is_admin_login}")
            
            # Guardar token para pruebas adicionales
            access_token = login_data.get('access_token')
            
        else:
            logger.error(f"❌ LOGIN FALLÓ: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en login: {e}")
        return False
    
    # 2. VERIFICAR ENDPOINT /me CON TOKEN OBTENIDO
    logger.info("\n🔍 2. VERIFICANDO ENDPOINT /me")
    logger.info("-" * 50)
    
    if not access_token:
        logger.error("❌ No hay token de acceso para probar /me")
        return False
    
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
            
            logger.info("✅ ENDPOINT /me EXITOSO - DATOS RECIBIDOS:")
            logger.info(f"   🆔 ID: {me_data.get('id')} ({type(me_data.get('id'))})")
            logger.info(f"   📧 Email: {me_data.get('email')} ({type(me_data.get('email'))})")
            logger.info(f"   👤 Nombre: {me_data.get('nombre')} ({type(me_data.get('nombre'))})")
            logger.info(f"   👤 Apellido: {me_data.get('apellido')} ({type(me_data.get('apellido'))})")
            logger.info(f"   💼 Cargo: {me_data.get('cargo')} ({type(me_data.get('cargo'))})")
            logger.info(f"   🔑 is_admin: {me_data.get('is_admin')} ({type(me_data.get('is_admin'))})")
            logger.info(f"   ✅ is_active: {me_data.get('is_active')} ({type(me_data.get('is_active'))})")
            logger.info(f"   📅 Creado: {me_data.get('created_at')} ({type(me_data.get('created_at'))})")
            logger.info(f"   🔄 Actualizado: {me_data.get('updated_at')} ({type(me_data.get('updated_at'))})")
            logger.info(f"   🕐 Último login: {me_data.get('last_login')} ({type(me_data.get('last_login'))})")
            
            # Verificar permisos
            permissions = me_data.get('permissions', [])
            logger.info(f"   🔐 Permisos: {len(permissions)} permisos")
            logger.info(f"   📋 Lista permisos: {permissions}")
            
            # Verificar is_admin en respuesta de /me
            is_admin_me = me_data.get('is_admin')
            logger.info(f"\n🔑 ANÁLISIS CRÍTICO DE is_admin EN /me:")
            logger.info(f"   📊 Valor: {is_admin_me}")
            logger.info(f"   📊 Tipo: {type(is_admin_me)}")
            
            if is_admin_me is True:
                logger.info("✅ CONFIRMADO: Usuario ES admin en respuesta de /me")
            elif is_admin_me is False:
                logger.error("❌ PROBLEMA: Usuario NO es admin en respuesta de /me")
            else:
                logger.error(f"❌ PROBLEMA: Valor is_admin inválido en /me: {is_admin_me}")
            
            # Comparar datos entre login y /me
            logger.info(f"\n🔄 COMPARACIÓN LOGIN vs /me:")
            logger.info(f"   🔑 is_admin login: {is_admin_login}")
            logger.info(f"   🔑 is_admin /me: {is_admin_me}")
            logger.info(f"   ✅ Coinciden: {is_admin_login == is_admin_me}")
            
        else:
            logger.error(f"❌ ENDPOINT /me FALLÓ: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Error en endpoint /me: {e}")
    
    # 3. CONCLUSIÓN FINAL
    logger.info("\n📊 CONCLUSIÓN FINAL DE SIMULACIÓN")
    logger.info("=" * 80)
    
    logger.info("🎯 RESULTADOS DE LA SIMULACIÓN:")
    logger.info(f"   🔐 Login exitoso: {response.status_code == 200}")
    logger.info(f"   🔑 is_admin en login: {is_admin_login}")
    logger.info(f"   🔑 is_admin en /me: {is_admin_me}")
    
    if is_admin_login is True and is_admin_me is True:
        logger.info("✅ DIAGNÓSTICO: Backend retorna datos correctos")
        logger.info("🔍 CAUSA CONFIRMADA: Problema en frontend")
        logger.info("💡 SOLUCIÓN: Verificar frontend y caché")
    elif is_admin_login is False or is_admin_me is False:
        logger.error("❌ DIAGNÓSTICO: Backend retorna datos incorrectos")
        logger.error("🔍 CAUSA CONFIRMADA: Problema en backend/BD")
        logger.error("💡 SOLUCIÓN: Corregir datos en backend/BD")
    else:
        logger.error("❌ DIAGNÓSTICO: Datos inconsistentes")
        logger.error("🔍 CAUSA: Inconsistencia entre endpoints")
        logger.error("💡 SOLUCIÓN: Verificar lógica de endpoints")
    
    return True

if __name__ == "__main__":
    simular_login_completo()
