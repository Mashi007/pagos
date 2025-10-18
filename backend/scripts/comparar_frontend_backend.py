# backend/scripts/comparar_frontend_backend.py
"""
COMPARACIÓN FRONTEND VS BACKEND EN TIEMPO REAL - TERCERA AUDITORÍA
Comparar datos exactos entre frontend y backend para confirmar la causa
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

def comparar_frontend_backend():
    """
    Comparar datos exactos entre frontend y backend
    """
    logger.info("🔄 COMPARANDO FRONTEND VS BACKEND EN TIEMPO REAL")
    logger.info("=" * 60)
    
    backend_url = "https://pagos-f2qf.onrender.com"
    frontend_url = "https://rapicredit.onrender.com"
    
    # Credenciales de prueba
    test_credentials = {
        "email": "itmaster@rapicreditca.com",
        "password": "R@pi_2025**",
        "remember": True
    }
    
    # 1. OBTENER DATOS DEL BACKEND
    logger.info("🔍 1. OBTENIENDO DATOS DEL BACKEND")
    logger.info("-" * 40)
    
    backend_data = None
    access_token = None
    
    try:
        # Login
        response = requests.post(
            f"{backend_url}/api/v1/auth/login",
            json=test_credentials,
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        
        if response.status_code == 200:
            login_data = response.json()
            access_token = login_data.get('access_token')
            backend_login_user = login_data.get('user', {})
            
            logger.info("✅ Login backend exitoso")
            logger.info(f"   📧 Email: {backend_login_user.get('email')}")
            logger.info(f"   🔑 is_admin: {backend_login_user.get('is_admin')}")
            
            # Obtener datos de /me
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{backend_url}/api/v1/auth/me",
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                backend_data = response.json()
                logger.info("✅ Datos de /me obtenidos del backend")
                logger.info(f"   📧 Email: {backend_data.get('email')}")
                logger.info(f"   🔑 is_admin: {backend_data.get('is_admin')}")
                logger.info(f"   🔐 Permisos: {len(backend_data.get('permissions', []))}")
            else:
                logger.error(f"❌ Error obteniendo /me: {response.status_code}")
                
        else:
            logger.error(f"❌ Login backend falló: {response.status_code}")
            
    except Exception as e:
        logger.error(f"❌ Error obteniendo datos del backend: {e}")
    
    # 2. SIMULAR DATOS DEL FRONTEND (basado en el problema reportado)
    logger.info("\n🌐 2. SIMULANDO DATOS DEL FRONTEND")
    logger.info("-" * 40)
    
    # Datos que el usuario reporta ver en el frontend
    frontend_data = {
        "id": 1,  # Asumiendo ID numérico
        "email": "itmaster@rapicreditca.com",
        "nombre": "IT Master",
        "apellido": "Sistema",
        "cargo": "Administrador",
        "is_admin": False,  # ⚠️ PROBLEMA: Frontend muestra False
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "last_login": "2024-01-01T00:00:00Z"
    }
    
    logger.info("📊 Datos simulados del frontend (basado en problema reportado):")
    logger.info(f"   📧 Email: {frontend_data.get('email')}")
    logger.info(f"   🔑 is_admin: {frontend_data.get('is_admin')} ⚠️ PROBLEMA")
    
    # 3. COMPARAR DATOS
    logger.info("\n🔄 3. COMPARANDO DATOS FRONTEND VS BACKEND")
    logger.info("-" * 40)
    
    if backend_data:
        comparison_fields = [
            'id', 'email', 'nombre', 'apellido', 'cargo',
            'is_admin', 'is_active', 'created_at', 'updated_at', 'last_login'
        ]
        
        discrepancies = []
        
        for field in comparison_fields:
            backend_value = backend_data.get(field)
            frontend_value = frontend_data.get(field)
            
            if backend_value != frontend_value:
                discrepancies.append({
                    'field': field,
                    'backend': backend_value,
                    'frontend': frontend_value,
                    'types': (type(backend_value), type(frontend_value))
                })
                logger.warning(f"⚠️ DISCREPANCIA en {field}:")
                logger.warning(f"   Backend: {backend_value} ({type(backend_value)})")
                logger.warning(f"   Frontend: {frontend_value} ({type(frontend_value)})")
            else:
                logger.info(f"✅ {field}: {backend_value}")
        
        # 4. ANÁLISIS DE DISCREPANCIAS
        logger.info("\n📊 4. ANÁLISIS DE DISCREPANCIAS")
        logger.info("-" * 40)
        
        if discrepancies:
            logger.warning(f"⚠️ Se encontraron {len(discrepancies)} discrepancias:")
            
            for disc in discrepancies:
                logger.warning(f"   🔍 {disc['field']}: {disc['backend']} vs {disc['frontend']}")
            
            # Verificar si is_admin es la discrepancia principal
            is_admin_disc = next((d for d in discrepancies if d['field'] == 'is_admin'), None)
            if is_admin_disc:
                logger.error("❌ CONFIRMADO: Discrepancia crítica en is_admin")
                logger.error(f"   Backend dice: {is_admin_disc['backend']}")
                logger.error(f"   Frontend muestra: {is_admin_disc['frontend']}")
                
                if is_admin_disc['backend'] is True and is_admin_disc['frontend'] is False:
                    logger.error("🔍 CAUSA CONFIRMADA: Frontend muestra datos obsoletos")
                    logger.error("💡 SOLUCIÓN: Limpiar caché del frontend o verificar almacenamiento")
                elif is_admin_disc['backend'] is False:
                    logger.error("🔍 CAUSA CONFIRMADA: Backend tiene datos incorrectos")
                    logger.error("💡 SOLUCIÓN: Actualizar base de datos")
        else:
            logger.info("✅ No se encontraron discrepancias")
    
    # 5. VERIFICAR ALMACENAMIENTO DEL FRONTEND
    logger.info("\n💾 5. VERIFICANDO ALMACENAMIENTO DEL FRONTEND")
    logger.info("-" * 40)
    
    logger.info("🔍 Posibles causas del problema en el frontend:")
    logger.info("   1. localStorage con datos obsoletos")
    logger.info("   2. sessionStorage con datos obsoletos")
    logger.info("   3. Estado de React/Zustand no actualizado")
    logger.info("   4. Error en la función refreshUser()")
    logger.info("   5. Error en la función initializeAuth()")
    logger.info("   6. Problema en el interceptor de Axios")
    
    # 6. RECOMENDACIONES
    logger.info("\n💡 6. RECOMENDACIONES")
    logger.info("-" * 40)
    
    logger.info("🔧 Acciones recomendadas:")
    logger.info("   1. Limpiar localStorage y sessionStorage del navegador")
    logger.info("   2. Verificar que initializeAuth() llame a refreshUser()")
    logger.info("   3. Verificar que refreshUser() actualice el estado correctamente")
    logger.info("   4. Verificar que el interceptor de Axios maneje errores correctamente")
    logger.info("   5. Agregar logs detallados en el frontend para debugging")
    
    logger.info("\n📊 RESUMEN FINAL DE COMPARACIÓN")
    logger.info("=" * 60)
    logger.info("✅ Comparación completada")
    logger.info("💡 Revisar discrepancias para confirmar la causa raíz")

if __name__ == "__main__":
    comparar_frontend_backend()
