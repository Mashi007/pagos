# backend/scripts/probar_flujo_completo.py
"""
PRUEBA DE FLUJO COMPLETO - SEXTA AUDITORÍA
Probar flujo completo desde login hasta header para verificar corrección
"""
import os
import sys
import logging
import requests
import json
import time
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def probar_flujo_completo():
    """
    Probar flujo completo desde login hasta header
    """
    logger.info("🔄 PRUEBA DE FLUJO COMPLETO DESDE LOGIN HASTA HEADER")
    logger.info("=" * 80)
    logger.info(f"📅 Fecha y hora: {datetime.now()}")
    logger.info("🎯 Objetivo: Verificar que el flujo completo funciona después de la corrección")
    logger.info("=" * 80)
    
    backend_url = "https://pagos-f2qf.onrender.com"
    frontend_url = "https://rapicredit.onrender.com"
    
    # Credenciales exactas
    credentials = {
        "email": "itmaster@rapicreditca.com",
        "password": "R@pi_2025**",
        "remember": True
    }
    
    # 1. SIMULAR LOGIN COMPLETO
    logger.info("🔐 1. SIMULANDO LOGIN COMPLETO")
    logger.info("-" * 50)
    
    login_start_time = time.time()
    
    try:
        response = requests.post(
            f"{backend_url}/api/v1/auth/login",
            json=credentials,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        login_end_time = time.time()
        login_duration = login_end_time - login_start_time
        
        logger.info(f"📊 Login Duration: {login_duration:.3f}s")
        logger.info(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            login_data = response.json()
            access_token = login_data.get('access_token')
            user_data = login_data.get('user', {})
            
            logger.info("✅ LOGIN EXITOSO")
            logger.info(f"   🎫 Token obtenido: {bool(access_token)}")
            logger.info(f"   👤 Usuario: {user_data.get('nombre')} {user_data.get('apellido')}")
            logger.info(f"   🔑 is_admin: {user_data.get('is_admin')}")
            
            # Verificar que la corrección está aplicada
            if user_data.get('is_admin') is True:
                logger.info("   ✅ CORRECCIÓN CONFIRMADA: is_admin = True en login")
            else:
                logger.error(f"   ❌ CORRECCIÓN NO APLICADA: is_admin = {user_data.get('is_admin')}")
                return False
            
        else:
            logger.error(f"❌ LOGIN FALLÓ: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en login: {e}")
        return False
    
    # 2. SIMULAR INICIALIZACIÓN DE AUTENTICACIÓN (initializeAuth)
    logger.info("\n🚀 2. SIMULANDO INICIALIZACIÓN DE AUTENTICACIÓN")
    logger.info("-" * 50)
    
    # Simular lo que hace initializeAuth() en el frontend
    logger.info("📊 Simulando initializeAuth() del frontend:")
    logger.info("   1. Verificar si hay usuario en localStorage/sessionStorage")
    logger.info("   2. Si hay usuario, verificar con backend")
    logger.info("   3. Si no hay usuario, intentar obtener del backend")
    
    # Simular verificación con backend (refreshUser)
    logger.info("\n🔄 Simulando refreshUser() del frontend:")
    
    refresh_start_time = time.time()
    
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
        
        refresh_end_time = time.time()
        refresh_duration = refresh_end_time - refresh_start_time
        
        logger.info(f"📊 Refresh Duration: {refresh_duration:.3f}s")
        logger.info(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            me_data = response.json()
            
            logger.info("✅ REFRESH EXITOSO")
            logger.info(f"   👤 Usuario: {me_data.get('nombre')} {me_data.get('apellido')}")
            logger.info(f"   🔑 is_admin: {me_data.get('is_admin')}")
            logger.info(f"   🔐 Permisos: {len(me_data.get('permissions', []))}")
            
            # Verificar consistencia con login
            if me_data.get('is_admin') == user_data.get('is_admin'):
                logger.info("   ✅ CONSISTENCIA CONFIRMADA: Datos consistentes entre login y refresh")
            else:
                logger.error("   ❌ INCONSISTENCIA: Datos diferentes entre login y refresh")
                return False
            
        else:
            logger.error(f"❌ REFRESH FALLÓ: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en refresh: {e}")
        return False
    
    # 3. SIMULAR LÓGICA DEL HEADER
    logger.info("\n🎭 3. SIMULANDO LÓGICA DEL HEADER")
    logger.info("-" * 50)
    
    # Simular la lógica que usa el frontend para mostrar el header
    logger.info("📊 Simulando lógica del header del frontend:")
    
    # Datos que tendría el frontend después del login/refresh
    frontend_user_data = {
        "id": me_data.get('id'),
        "email": me_data.get('email'),
        "nombre": me_data.get('nombre'),
        "apellido": me_data.get('apellido'),
        "cargo": me_data.get('cargo'),
        "is_admin": me_data.get('is_admin'),
        "is_active": me_data.get('is_active')
    }
    
    logger.info("📊 Datos disponibles para el header:")
    for key, value in frontend_user_data.items():
        logger.info(f"   {key}: {value} ({type(value)})")
    
    # Simular cálculo de datos para mostrar
    logger.info("\n🎭 Calculando datos para mostrar en el header:")
    
    # Simular userInitials
    nombre = frontend_user_data.get('nombre', '')
    apellido = frontend_user_data.get('apellido', '')
    user_initials = f"{nombre[0] if nombre else ''}{apellido[0] if apellido else ''}".upper()
    logger.info(f"   🎭 userInitials: {user_initials}")
    
    # Simular userName
    user_name = f"{nombre} {apellido}".strip()
    logger.info(f"   🎭 userName: {user_name}")
    
    # Simular userRole (CRÍTICO)
    is_admin = frontend_user_data.get('is_admin')
    if is_admin is True:
        user_role = "Administrador"
        logger.info("   🎭 userRole: Administrador ✅")
    elif is_admin is False:
        user_role = "Usuario"
        logger.info("   🎭 userRole: Usuario ❌")
    else:
        user_role = "Error/Indefinido"
        logger.error(f"   🎭 userRole: {user_role} ❌")
    
    # Simular email
    email = frontend_user_data.get('email')
    logger.info(f"   🎭 email: {email}")
    
    # 4. VERIFICAR RESULTADO ESPERADO
    logger.info("\n🎯 4. VERIFICANDO RESULTADO ESPERADO")
    logger.info("-" * 50)
    
    logger.info("📊 RESULTADO ESPERADO vs ACTUAL:")
    logger.info(f"   🔑 is_admin: Esperado=True, Actual={is_admin}")
    logger.info(f"   🎭 userRole: Esperado='Administrador', Actual='{user_role}'")
    
    if is_admin is True and user_role == "Administrador":
        logger.info("✅ RESULTADO CORRECTO: El header mostraría 'Administrador'")
        logger.info("🎯 PROBLEMA RESUELTO: La corrección funcionó correctamente")
    elif is_admin is False:
        logger.error("❌ RESULTADO INCORRECTO: El header mostraría 'Usuario'")
        logger.error("🔍 CAUSA: Usuario no es admin en base de datos")
    else:
        logger.error(f"❌ RESULTADO INESPERADO: is_admin={is_admin}, userRole='{user_role}'")
        logger.error("🔍 CAUSA: Problema en la lógica o datos")
    
    # 5. SIMULAR NAVEGACIÓN A PÁGINAS ADMIN
    logger.info("\n🔐 5. SIMULANDO NAVEGACIÓN A PÁGINAS ADMIN")
    logger.info("-" * 50)
    
    # Páginas que requieren permisos de admin
    admin_pages = [
        "/usuarios",
        "/analistas", 
        "/concesionarios",
        "/modelos-vehiculos"
    ]
    
    logger.info("📊 Simulando acceso a páginas que requieren admin:")
    
    for page in admin_pages:
        logger.info(f"   🔐 Página: {page}")
        
        # Simular lógica de SimpleProtectedRoute
        require_admin = True
        user_is_admin = frontend_user_data.get('is_admin')
        
        if require_admin and not user_is_admin:
            logger.error(f"      ❌ ACCESO DENEGADO: Usuario no es admin")
            logger.error(f"      🎭 Mostraría: 'Acceso Denegado'")
        else:
            logger.info(f"      ✅ ACCESO PERMITIDO: Usuario es admin")
            logger.info(f"      🎭 Mostraría: Contenido de la página")
    
    # 6. VERIFICAR TIMING Y PERFORMANCE
    logger.info("\n⏱️ 6. VERIFICANDO TIMING Y PERFORMANCE")
    logger.info("-" * 50)
    
    total_time = refresh_end_time - login_start_time
    logger.info(f"📊 Tiempo total del flujo: {total_time:.3f}s")
    logger.info(f"📊 Tiempo de login: {login_duration:.3f}s")
    logger.info(f"📊 Tiempo de refresh: {refresh_duration:.3f}s")
    
    if total_time < 2:
        logger.info("✅ PERFORMANCE EXCELENTE: Flujo completo en menos de 2 segundos")
    elif total_time < 5:
        logger.info("✅ PERFORMANCE BUENA: Flujo completo en menos de 5 segundos")
    else:
        logger.warning("⚠️ PERFORMANCE LENTA: Flujo completo toma más de 5 segundos")
    
    # 7. CONCLUSIÓN FINAL
    logger.info("\n📊 CONCLUSIÓN FINAL DEL FLUJO COMPLETO")
    logger.info("=" * 80)
    
    logger.info("🎯 RESULTADOS DEL FLUJO COMPLETO:")
    logger.info(f"   🔐 Login exitoso: {login_data is not None}")
    logger.info(f"   🔄 Refresh exitoso: {me_data is not None}")
    logger.info(f"   🔑 is_admin consistente: {user_data.get('is_admin') == me_data.get('is_admin')}")
    logger.info(f"   🎭 Header mostraría: {user_role}")
    logger.info(f"   🔐 Acceso a páginas admin: {'Permitido' if is_admin else 'Denegado'}")
    logger.info(f"   ⏱️ Tiempo total: {total_time:.3f}s")
    
    if is_admin is True and user_role == "Administrador":
        logger.info("\n✅ FLUJO COMPLETO EXITOSO:")
        logger.info("   🎯 La corrección fue aplicada correctamente")
        logger.info("   🎯 El frontend recibirá datos consistentes")
        logger.info("   🎯 El header mostrará 'Administrador'")
        logger.info("   🎯 Las páginas admin serán accesibles")
        logger.info("   🎯 El problema 'Rol: USER' está resuelto")
    else:
        logger.error("\n❌ FLUJO COMPLETO FALLIDO:")
        logger.error("   🔍 La corrección no fue aplicada correctamente")
        logger.error("   🔍 El frontend seguirá mostrando datos incorrectos")
        logger.error("   🔍 El problema 'Rol: USER' persiste")
    
    return is_admin is True and user_role == "Administrador"

if __name__ == "__main__":
    probar_flujo_completo()
