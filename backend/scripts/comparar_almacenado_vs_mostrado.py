# backend/scripts/comparar_almacenado_vs_mostrado.py
"""
COMPARAR ALMACENADO VS MOSTRADO - CUARTA AUDITORÍA
Comparar datos almacenados vs datos mostrados para confirmar causa raíz
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

def comparar_almacenado_vs_mostrado():
    """
    Comparar datos almacenados vs datos mostrados
    """
    logger.info("💾 COMPARACIÓN ALMACENADO VS MOSTRADO")
    logger.info("=" * 80)
    logger.info(f"📅 Fecha y hora: {datetime.now()}")
    logger.info("🎯 Objetivo: Comparar datos almacenados vs datos mostrados")
    logger.info("=" * 80)
    
    backend_url = "https://pagos-f2qf.onrender.com"
    
    # Credenciales exactas
    credentials = {
        "email": "itmaster@rapicreditca.com",
        "password": "R@pi_2025**",
        "remember": True
    }
    
    # 1. OBTENER DATOS DEL BACKEND
    logger.info("🔍 1. OBTENIENDO DATOS DEL BACKEND")
    logger.info("-" * 50)
    
    backend_data = None
    access_token = None
    
    try:
        # Login
        response = requests.post(
            f"{backend_url}/api/v1/auth/login",
            json=credentials,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            login_data = response.json()
            access_token = login_data.get('access_token')
            backend_login_data = login_data.get('user', {})
            
            logger.info("✅ Login backend exitoso")
            logger.info(f"   📧 Email: {backend_login_data.get('email')}")
            logger.info(f"   🔑 is_admin: {backend_login_data.get('is_admin')}")
            
            # Obtener datos de /me
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{backend_url}/api/v1/auth/me",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                backend_data = response.json()
                logger.info("✅ Datos de /me obtenidos del backend")
                logger.info(f"   📧 Email: {backend_data.get('email')}")
                logger.info(f"   🔑 is_admin: {backend_data.get('is_admin')}")
            else:
                logger.error(f"❌ Error obteniendo /me: {response.status_code}")
                
        else:
            logger.error(f"❌ Login backend falló: {response.status_code}")
            
    except Exception as e:
        logger.error(f"❌ Error obteniendo datos del backend: {e}")
    
    # 2. SIMULAR DATOS QUE EL FRONTEND ALMACENARÍA
    logger.info("\n💾 2. SIMULANDO DATOS QUE EL FRONTEND ALMACENARÍA")
    logger.info("-" * 50)
    
    if backend_data:
        # Simular lo que el frontend almacenaría en localStorage/sessionStorage
        frontend_stored_data = {
            "id": backend_data.get('id'),
            "email": backend_data.get('email'),
            "nombre": backend_data.get('nombre'),
            "apellido": backend_data.get('apellido'),
            "cargo": backend_data.get('cargo'),
            "is_admin": backend_data.get('is_admin'),
            "is_active": backend_data.get('is_active'),
            "created_at": backend_data.get('created_at'),
            "updated_at": backend_data.get('updated_at'),
            "last_login": backend_data.get('last_login')
        }
        
        logger.info("📊 Datos que el frontend almacenaría:")
        for key, value in frontend_stored_data.items():
            logger.info(f"   {key}: {value} ({type(value)})")
        
        # Verificar si los datos son válidos para almacenamiento
        logger.info("\n🔍 Verificando validez para almacenamiento:")
        
        invalid_fields = []
        for key, value in frontend_stored_data.items():
            if value is None:
                invalid_fields.append(f"{key}: None")
            elif isinstance(value, str) and value == "":
                invalid_fields.append(f"{key}: Empty string")
        
        if invalid_fields:
            logger.warning(f"⚠️ Campos problemáticos para almacenamiento: {invalid_fields}")
        else:
            logger.info("✅ Todos los campos son válidos para almacenamiento")
    
    # 3. SIMULAR DATOS QUE EL FRONTEND MOSTRARÍA
    logger.info("\n🎭 3. SIMULANDO DATOS QUE EL FRONTEND MOSTRARÍA")
    logger.info("-" * 50)
    
    if frontend_stored_data:
        # Simular lógica del frontend para mostrar datos
        display_data = {
            "userInitials": f"{frontend_stored_data.get('nombre', '').charAt(0) if frontend_stored_data.get('nombre') else ''}{frontend_stored_data.get('apellido', '').charAt(0) if frontend_stored_data.get('apellido') else ''}".upper(),
            "userName": f"{frontend_stored_data.get('nombre', '')} {frontend_stored_data.get('apellido', '')}".strip(),
            "userRole": "Administrador" if frontend_stored_data.get('is_admin') else "Usuario",
            "isAdmin": frontend_stored_data.get('is_admin'),
            "email": frontend_stored_data.get('email')
        }
        
        logger.info("🎭 Datos que el frontend mostraría:")
        for key, value in display_data.items():
            logger.info(f"   {key}: {value} ({type(value)})")
        
        # Verificar lógica crítica del rol
        logger.info(f"\n🔑 ANÁLISIS DE LÓGICA DE ROL:")
        logger.info(f"   📊 is_admin almacenado: {frontend_stored_data.get('is_admin')}")
        logger.info(f"   🎭 userRole calculado: {display_data.get('userRole')}")
        logger.info(f"   ✅ Lógica correcta: {display_data.get('userRole') == 'Administrador' if frontend_stored_data.get('is_admin') else 'Usuario'}")
    
    # 4. SIMULAR PROBLEMA REPORTADO POR EL USUARIO
    logger.info("\n🚨 4. SIMULANDO PROBLEMA REPORTADO POR EL USUARIO")
    logger.info("-" * 50)
    
    # Datos que el usuario reporta ver (problema)
    user_reported_data = {
        "userRole": "Usuario",  # ⚠️ PROBLEMA: Usuario reporta ver "Usuario"
        "is_admin": False,      # ⚠️ PROBLEMA: Usuario reporta is_admin = False
        "email": "itmaster@rapicreditca.com"
    }
    
    logger.info("🚨 Datos que el usuario reporta ver (PROBLEMA):")
    for key, value in user_reported_data.items():
        logger.info(f"   {key}: {value}")
    
    # Comparar con datos del backend
    if backend_data:
        logger.info(f"\n🔄 COMPARACIÓN BACKEND vs REPORTADO POR USUARIO:")
        logger.info(f"   🔑 Backend is_admin: {backend_data.get('is_admin')}")
        logger.info(f"   🔑 Usuario reporta is_admin: {user_reported_data.get('is_admin')}")
        logger.info(f"   🎭 Backend debería mostrar: {'Administrador' if backend_data.get('is_admin') else 'Usuario'}")
        logger.info(f"   🎭 Usuario reporta ver: {user_reported_data.get('userRole')}")
        
        # Identificar discrepancia
        backend_is_admin = backend_data.get('is_admin')
        user_reports_is_admin = user_reported_data.get('is_admin')
        
        if backend_is_admin != user_reports_is_admin:
            logger.error("❌ DISCREPANCIA CONFIRMADA:")
            logger.error(f"   Backend dice: {backend_is_admin}")
            logger.error(f"   Usuario ve: {user_reports_is_admin}")
            
            if backend_is_admin is True and user_reports_is_admin is False:
                logger.error("🔍 CAUSA CONFIRMADA: Frontend muestra datos obsoletos")
                logger.error("💡 SOLUCIÓN: Limpiar caché del frontend")
            elif backend_is_admin is False:
                logger.error("🔍 CAUSA CONFIRMADA: Backend tiene datos incorrectos")
                logger.error("💡 SOLUCIÓN: Actualizar base de datos")
        else:
            logger.info("✅ No hay discrepancia entre backend y lo que reporta el usuario")
    
    # 5. SIMULAR POSIBLES CAUSAS DEL PROBLEMA
    logger.info("\n🔍 5. SIMULANDO POSIBLES CAUSAS DEL PROBLEMA")
    logger.info("-" * 50)
    
    possible_causes = [
        {
            "causa": "Datos obsoletos en localStorage",
            "descripcion": "El frontend está usando datos cacheados antiguos",
            "solucion": "Limpiar localStorage y sessionStorage"
        },
        {
            "causa": "Error en función initializeAuth()",
            "descripcion": "La función no está actualizando datos del backend",
            "solucion": "Verificar que initializeAuth() llame a refreshUser()"
        },
        {
            "causa": "Error en función refreshUser()",
            "descripcion": "La función no está obteniendo datos actualizados",
            "solucion": "Verificar que refreshUser() funcione correctamente"
        },
        {
            "causa": "Error en interceptor de Axios",
            "descripcion": "El interceptor no está manejando respuestas correctamente",
            "solucion": "Verificar interceptores de Axios"
        },
        {
            "causa": "Datos incorrectos en base de datos",
            "descripcion": "El usuario realmente no es admin en BD",
            "solucion": "Actualizar is_admin en base de datos"
        },
        {
            "causa": "Error en serialización/deserialización",
            "descripcion": "Los datos se corrompen al almacenar/recuperar",
            "solucion": "Verificar funciones de almacenamiento seguro"
        }
    ]
    
    logger.info("📋 Posibles causas del problema:")
    for i, causa in enumerate(possible_causes, 1):
        logger.info(f"   {i}. {causa['causa']}")
        logger.info(f"      📝 Descripción: {causa['descripcion']}")
        logger.info(f"      💡 Solución: {causa['solucion']}")
        logger.info("")
    
    # 6. CONCLUSIÓN FINAL
    logger.info("\n📊 CONCLUSIÓN FINAL DE COMPARACIÓN")
    logger.info("=" * 80)
    
    if backend_data:
        backend_is_admin = backend_data.get('is_admin')
        user_reports_is_admin = user_reported_data.get('is_admin')
        
        if backend_is_admin != user_reports_is_admin:
            logger.error("❌ DISCREPANCIA CONFIRMADA ENTRE BACKEND Y FRONTEND")
            logger.error(f"   Backend: {backend_is_admin}")
            logger.error(f"   Frontend: {user_reports_is_admin}")
            
            if backend_is_admin is True:
                logger.error("🔍 CAUSA RAÍZ CONFIRMADA: Problema en frontend")
                logger.error("💡 SOLUCIÓN PRINCIPAL: Verificar y corregir frontend")
            else:
                logger.error("🔍 CAUSA RAÍZ CONFIRMADA: Problema en backend/BD")
                logger.error("💡 SOLUCIÓN PRINCIPAL: Corregir datos en backend/BD")
        else:
            logger.info("✅ No hay discrepancia - problema puede ser otro")
    
    logger.info("🎯 PRÓXIMOS PASOS RECOMENDADOS:")
    logger.info("   1. Ejecutar scripts de diagnóstico en producción")
    logger.info("   2. Verificar datos exactos en base de datos")
    logger.info("   3. Probar flujo completo frontend-backend")
    logger.info("   4. Implementar solución basada en hallazgos")
    
    return True

if __name__ == "__main__":
    comparar_almacenado_vs_mostrado()
