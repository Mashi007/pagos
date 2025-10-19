# backend/scripts/verificar_consistencia_endpoints.py
"""
VERIFICACIÓN DE CONSISTENCIA ENTRE ENDPOINTS - SEXTA AUDITORÍA
Verificar que /login y /me retornan datos consistentes después de la corrección
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

def verificar_consistencia_endpoints():
    """
    Verificar consistencia entre endpoints /login y /me
    """
    logger.info("🔄 VERIFICACIÓN DE CONSISTENCIA ENTRE ENDPOINTS")
    logger.info("=" * 80)
    logger.info(f"📅 Fecha y hora: {datetime.now()}")
    logger.info("🎯 Objetivo: Verificar que /login y /me retornan datos consistentes")
    logger.info("=" * 80)
    
    backend_url = "https://pagos-f2qf.onrender.com"
    
    # Credenciales exactas
    credentials = {
        "email": "itmaster@rapicreditca.com",
        "password": "R@pi_2025**",
        "remember": True
    }
    
    # 1. REALIZAR LOGIN Y CAPTURAR RESPUESTA
    logger.info("🔐 1. REALIZANDO LOGIN Y CAPTURANDO RESPUESTA")
    logger.info("-" * 50)
    
    login_data = None
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
            
            # Analizar datos del usuario en respuesta de login
            user_login = login_data.get('user', {})
            logger.info("\n👤 DATOS DEL USUARIO EN RESPUESTA DE LOGIN:")
            logger.info(f"   🆔 ID: {user_login.get('id')} ({type(user_login.get('id'))})")
            logger.info(f"   📧 Email: {user_login.get('email')} ({type(user_login.get('email'))})")
            logger.info(f"   👤 Nombre: {user_login.get('nombre')} ({type(user_login.get('nombre'))})")
            logger.info(f"   👤 Apellido: {user_login.get('apellido')} ({type(user_login.get('apellido'))})")
            logger.info(f"   💼 Cargo: {user_login.get('cargo')} ({type(user_login.get('cargo'))})")
            logger.info(f"   🔑 is_admin: {user_login.get('is_admin')} ({type(user_login.get('is_admin'))})")
            logger.info(f"   ✅ is_active: {user_login.get('is_active')} ({type(user_login.get('is_active'))})")
            logger.info(f"   📅 Creado: {user_login.get('created_at')} ({type(user_login.get('created_at'))})")
            logger.info(f"   🔄 Actualizado: {user_login.get('updated_at')} ({type(user_login.get('updated_at'))})")
            logger.info(f"   🕐 Último login: {user_login.get('last_login')} ({type(user_login.get('last_login'))})")
            
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
    
    me_data = None
    
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
            
            logger.info("✅ ENDPOINT /me EXITOSO")
            logger.info("\n👤 DATOS DEL USUARIO EN RESPUESTA DE /me:")
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
            
        else:
            logger.error(f"❌ ENDPOINT /me FALLÓ: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Error en endpoint /me: {e}")
    
    # 3. COMPARAR DATOS ENTRE /login Y /me
    logger.info("\n🔄 3. COMPARANDO DATOS ENTRE /login Y /me")
    logger.info("-" * 50)
    
    if login_data and me_data:
        user_login = login_data.get('user', {})
        
        # Campos críticos a comparar
        campos_criticos = [
            'id', 'email', 'nombre', 'apellido', 'cargo', 
            'is_admin', 'is_active', 'created_at', 'updated_at', 'last_login'
        ]
        
        inconsistencias = []
        coincidencias = []
        
        logger.info("📊 COMPARACIÓN CAMPO POR CAMPO:")
        
        for campo in campos_criticos:
            valor_login = user_login.get(campo)
            valor_me = me_data.get(campo)
            
            if valor_login == valor_me:
                coincidencias.append(campo)
                logger.info(f"   ✅ {campo}: COINCIDE ({valor_login})")
            else:
                inconsistencias.append({
                    'campo': campo,
                    'login': valor_login,
                    'me': valor_me
                })
                logger.error(f"   ❌ {campo}: NO COINCIDE")
                logger.error(f"      Login: {valor_login}")
                logger.error(f"      /me: {valor_me}")
        
        # Resumen de consistencia
        logger.info(f"\n📊 RESUMEN DE CONSISTENCIA:")
        logger.info(f"   ✅ Campos coincidentes: {len(coincidencias)}/{len(campos_criticos)}")
        logger.info(f"   ❌ Campos inconsistentes: {len(inconsistencias)}")
        logger.info(f"   📊 Porcentaje de consistencia: {len(coincidencias)/len(campos_criticos)*100:.1f}%")
        
        # Análisis específico de is_admin
        logger.info(f"\n🔑 ANÁLISIS ESPECÍFICO DE is_admin:")
        is_admin_login = user_login.get('is_admin')
        is_admin_me = me_data.get('is_admin')
        
        logger.info(f"   🔐 /login is_admin: {is_admin_login} ({type(is_admin_login)})")
        logger.info(f"   🔐 /me is_admin: {is_admin_me} ({type(is_admin_me)})")
        
        if is_admin_login == is_admin_me:
            logger.info("   ✅ CONSISTENCIA PERFECTA: Ambos endpoints retornan el mismo valor")
            if is_admin_login is True:
                logger.info("   🎯 RESULTADO: Usuario ES administrador en ambos endpoints")
            elif is_admin_login is False:
                logger.info("   🎯 RESULTADO: Usuario NO es administrador en ambos endpoints")
            else:
                logger.warning(f"   ⚠️ VALOR INESPERADO: {is_admin_login}")
        else:
            logger.error("   ❌ INCONSISTENCIA CRÍTICA: Los endpoints retornan valores diferentes")
            logger.error("   🔍 CAUSA: La corrección no fue aplicada correctamente")
    
    # 4. VERIFICAR CORRECCIÓN ESPECÍFICA
    logger.info("\n🔧 4. VERIFICANDO CORRECCIÓN ESPECÍFICA")
    logger.info("-" * 50)
    
    if login_data:
        user_login = login_data.get('user', {})
        
        # Verificar que la corrección fue aplicada
        correcciones_aplicadas = []
        correcciones_faltantes = []
        
        # Verificar campo is_admin
        if 'is_admin' in user_login:
            correcciones_aplicadas.append("Campo is_admin presente")
            if user_login.get('is_admin') is True:
                correcciones_aplicadas.append("Campo is_admin con valor correcto (True)")
            else:
                correcciones_faltantes.append(f"Campo is_admin con valor incorrecto: {user_login.get('is_admin')}")
        else:
            correcciones_faltantes.append("Campo is_admin completamente faltante")
        
        # Verificar campo cargo
        if 'cargo' in user_login:
            correcciones_aplicadas.append("Campo cargo presente")
        else:
            correcciones_faltantes.append("Campo cargo faltante")
        
        # Verificar campos de timestamp
        timestamp_fields = ['created_at', 'updated_at', 'last_login']
        for field in timestamp_fields:
            if field in user_login:
                correcciones_aplicadas.append(f"Campo {field} presente")
            else:
                correcciones_faltantes.append(f"Campo {field} faltante")
        
        # Verificar que campo rol obsoleto fue removido
        if 'rol' not in user_login:
            correcciones_aplicadas.append("Campo rol obsoleto removido correctamente")
        else:
            correcciones_faltantes.append("Campo rol obsoleto aún presente")
        
        logger.info("📊 ESTADO DE LAS CORRECCIONES:")
        logger.info(f"   ✅ Correcciones aplicadas: {len(correcciones_aplicadas)}")
        for correccion in correcciones_aplicadas:
            logger.info(f"      ✅ {correccion}")
        
        if correcciones_faltantes:
            logger.info(f"   ❌ Correcciones faltantes: {len(correcciones_faltantes)}")
            for correccion in correcciones_faltantes:
                logger.error(f"      ❌ {correccion}")
        else:
            logger.info("   ✅ Todas las correcciones fueron aplicadas correctamente")
    
    # 5. CONCLUSIÓN FINAL
    logger.info("\n📊 CONCLUSIÓN FINAL DE CONSISTENCIA")
    logger.info("=" * 80)
    
    if login_data and me_data:
        user_login = login_data.get('user', {})
        is_admin_login = user_login.get('is_admin')
        is_admin_me = me_data.get('is_admin')
        
        if is_admin_login == is_admin_me and is_admin_login is True:
            logger.info("✅ CORRECCIÓN CONFIRMADA: Problema resuelto exitosamente")
            logger.info("🎯 RESULTADO: Ambos endpoints retornan is_admin: True")
            logger.info("💡 IMPACTO: Frontend recibirá datos consistentes desde el login")
            logger.info("🚀 PRÓXIMO PASO: Verificar que el frontend muestra 'Administrador'")
        elif is_admin_login == is_admin_me and is_admin_login is False:
            logger.error("❌ PROBLEMA PERSISTENTE: Usuario no es admin en ambos endpoints")
            logger.error("🔍 CAUSA: Problema en base de datos, no en endpoints")
            logger.error("💡 SOLUCIÓN: Actualizar is_admin en base de datos")
        else:
            logger.error("❌ INCONSISTENCIA PERSISTENTE: Los endpoints aún son inconsistentes")
            logger.error("🔍 CAUSA: La corrección no fue aplicada correctamente")
            logger.error("💡 SOLUCIÓN: Revisar y reaplicar la corrección")
    else:
        logger.error("❌ NO SE PUDO VERIFICAR: Datos insuficientes")
        logger.error("💡 SOLUCIÓN: Revisar conectividad y endpoints")
    
    return True

if __name__ == "__main__":
    verificar_consistencia_endpoints()
