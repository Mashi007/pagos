# backend/scripts/verificar_respuesta_me.py
"""
VERIFICACIÓN EXACTA DE RESPUESTA /me - TERCERA AUDITORÍA
Verificar la respuesta exacta del endpoint /me para confirmar la causa
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

def verificar_respuesta_me():
    """
    Verificar la respuesta exacta del endpoint /me
    """
    logger.info("🔍 VERIFICANDO RESPUESTA EXACTA DEL ENDPOINT /me")
    logger.info("=" * 60)
    
    backend_url = "https://pagos-f2qf.onrender.com"
    
    # Credenciales de prueba
    test_credentials = {
        "email": "itmaster@rapicreditca.com",
        "password": "R@pi_2025**",
        "remember": True
    }
    
    # 1. OBTENER TOKEN DE ACCESO
    logger.info("🔑 1. OBTENIENDO TOKEN DE ACCESO")
    logger.info("-" * 40)
    
    try:
        response = requests.post(
            f"{backend_url}/api/v1/auth/login",
            json=test_credentials,
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        
        if response.status_code != 200:
            logger.error(f"❌ Login falló: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            return False
        
        data = response.json()
        access_token = data.get('access_token')
        
        if not access_token:
            logger.error("❌ No se obtuvo token de acceso")
            return False
        
        logger.info("✅ Token de acceso obtenido")
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo token: {e}")
        return False
    
    # 2. VERIFICAR RESPUESTA EXACTA DE /me
    logger.info("\n🔍 2. VERIFICANDO RESPUESTA EXACTA DE /me")
    logger.info("-" * 40)
    
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        response = requests.get(
            f"{backend_url}/api/v1/auth/me",
            headers=headers,
            timeout=15
        )
        
        logger.info(f"📊 Status Code: {response.status_code}")
        logger.info(f"📊 Headers de respuesta: {dict(response.headers)}")
        
        if response.status_code == 200:
            # Obtener respuesta como texto primero
            response_text = response.text
            logger.info(f"📊 Respuesta como texto: {response_text}")
            
            # Parsear JSON
            try:
                user_data = response.json()
                logger.info("✅ Respuesta JSON válida")
                
                # Verificar cada campo específicamente
                logger.info("\n📋 ANÁLISIS DETALLADO DE CAMPOS:")
                logger.info("-" * 30)
                
                fields_to_check = [
                    'id', 'email', 'nombre', 'apellido', 'cargo',
                    'is_admin', 'is_active', 'created_at', 'updated_at',
                    'last_login', 'permissions'
                ]
                
                for field in fields_to_check:
                    value = user_data.get(field)
                    logger.info(f"   {field}: {value} ({type(value)})")
                
                # Verificación específica de is_admin
                is_admin = user_data.get('is_admin')
                logger.info(f"\n🔑 VERIFICACIÓN ESPECÍFICA DE is_admin:")
                logger.info(f"   Valor: {is_admin}")
                logger.info(f"   Tipo: {type(is_admin)}")
                logger.info(f"   Es True: {is_admin is True}")
                logger.info(f"   Es False: {is_admin is False}")
                logger.info(f"   Es None: {is_admin is None}")
                
                # Verificar permisos
                permissions = user_data.get('permissions', [])
                logger.info(f"\n🔐 VERIFICACIÓN DE PERMISOS:")
                logger.info(f"   Cantidad: {len(permissions)}")
                logger.info(f"   Tipo: {type(permissions)}")
                logger.info(f"   Lista: {permissions}")
                
                # Verificar si hay campos inesperados
                unexpected_fields = set(user_data.keys()) - set(fields_to_check)
                if unexpected_fields:
                    logger.warning(f"⚠️ Campos inesperados: {unexpected_fields}")
                
                # Verificar si faltan campos esperados
                missing_fields = set(fields_to_check) - set(user_data.keys())
                if missing_fields:
                    logger.warning(f"⚠️ Campos faltantes: {missing_fields}")
                
                # CONCLUSIÓN
                logger.info(f"\n📊 CONCLUSIÓN:")
                if is_admin is True:
                    logger.info("✅ CONFIRMADO: Usuario ES administrador en respuesta de /me")
                    logger.info("🔍 CAUSA PROBABLE: Problema en frontend o caché")
                elif is_admin is False:
                    logger.error("❌ PROBLEMA: Usuario NO es administrador en respuesta de /me")
                    logger.error("🔍 CAUSA PROBABLE: Problema en backend o base de datos")
                else:
                    logger.error(f"❌ PROBLEMA: Valor is_admin inválido: {is_admin}")
                    logger.error("🔍 CAUSA PROBABLE: Error en serialización o esquema")
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Error parseando JSON: {e}")
                logger.error(f"   📊 Respuesta raw: {response_text}")
                
        else:
            logger.error(f"❌ Endpoint /me falló: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Error verificando /me: {e}")
    
    # 3. VERIFICAR ESQUEMA DE RESPUESTA
    logger.info("\n📋 3. VERIFICANDO ESQUEMA DE RESPUESTA")
    logger.info("-" * 40)
    
    try:
        # Verificar si la respuesta coincide con UserMeResponse
        logger.info("🔍 Verificando esquema UserMeResponse...")
        
        # Campos requeridos según el esquema
        required_fields = ['id', 'email', 'nombre', 'apellido', 'is_admin', 'is_active', 'permissions']
        
        for field in required_fields:
            if field not in user_data:
                logger.error(f"❌ Campo requerido faltante: {field}")
            else:
                logger.info(f"✅ Campo requerido presente: {field}")
        
    except Exception as e:
        logger.error(f"❌ Error verificando esquema: {e}")
    
    logger.info("\n📊 RESUMEN FINAL DE VERIFICACIÓN /me")
    logger.info("=" * 60)
    logger.info("✅ Verificación completada")

if __name__ == "__main__":
    verificar_respuesta_me()
