# backend/scripts/verificar_timing_cache.py
"""
VERIFICACIÓN DE TIMING Y CACHÉ - CUARTA AUDITORÍA
Verificar timing de actualizaciones y caché para confirmar causa raíz
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

def verificar_timing_cache():
    """
    Verificar timing de actualizaciones y caché
    """
    logger.info("⏰ VERIFICACIÓN DE TIMING Y CACHÉ")
    logger.info("=" * 80)
    logger.info(f"📅 Fecha y hora: {datetime.now()}")
    logger.info("🎯 Objetivo: Verificar timing de actualizaciones y caché")
    logger.info("=" * 80)
    
    backend_url = "https://pagos-f2qf.onrender.com"
    
    # Credenciales exactas
    credentials = {
        "email": "itmaster@rapicreditca.com",
        "password": "R@pi_2025**",
        "remember": True
    }
    
    # 1. MEDIR TIEMPO DE RESPUESTA DE ENDPOINTS
    logger.info("⏱️ 1. MIDIENDO TIEMPO DE RESPUESTA DE ENDPOINTS")
    logger.info("-" * 50)
    
    endpoints_to_test = [
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/log-test/force-logs",
        "/api/v1/verificar-permisos/verificar-permisos-completos"
    ]
    
    response_times = {}
    
    for endpoint in endpoints_to_test:
        try:
            start_time = time.time()
            
            if endpoint == "/api/v1/auth/login":
                response = requests.post(
                    f"{backend_url}{endpoint}",
                    json=credentials,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
            else:
                response = requests.get(
                    f"{backend_url}{endpoint}",
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            response_times[endpoint] = {
                "time": response_time,
                "status": response.status_code,
                "success": response.status_code == 200
            }
            
            logger.info(f"   📊 {endpoint}: {response_time:.3f}s (Status: {response.status_code})")
            
        except Exception as e:
            logger.error(f"   ❌ {endpoint}: Error - {e}")
            response_times[endpoint] = {
                "time": None,
                "status": None,
                "success": False,
                "error": str(e)
            }
    
    # Analizar tiempos de respuesta
    logger.info(f"\n📊 ANÁLISIS DE TIEMPOS DE RESPUESTA:")
    successful_endpoints = [ep for ep, data in response_times.items() if data["success"]]
    failed_endpoints = [ep for ep, data in response_times.items() if not data["success"]]
    
    logger.info(f"   ✅ Endpoints exitosos: {len(successful_endpoints)}")
    logger.info(f"   ❌ Endpoints fallidos: {len(failed_endpoints)}")
    
    if successful_endpoints:
        avg_time = sum(response_times[ep]["time"] for ep in successful_endpoints) / len(successful_endpoints)
        logger.info(f"   ⏱️ Tiempo promedio: {avg_time:.3f}s")
        
        if avg_time > 5:
            logger.warning("⚠️ Tiempo de respuesta alto - puede causar timeouts")
        elif avg_time > 2:
            logger.warning("⚠️ Tiempo de respuesta moderado")
        else:
            logger.info("✅ Tiempo de respuesta aceptable")
    
    # 2. SIMULAR MÚLTIPLES LLAMADAS PARA VERIFICAR CONSISTENCIA
    logger.info("\n🔄 2. SIMULANDO MÚLTIPLES LLAMADAS PARA VERIFICAR CONSISTENCIA")
    logger.info("-" * 50)
    
    # Obtener token primero
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
            logger.info("✅ Token obtenido para pruebas de consistencia")
        else:
            logger.error("❌ No se pudo obtener token para pruebas")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error obteniendo token: {e}")
        return False
    
    # Hacer múltiples llamadas a /me
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    logger.info("🔄 Haciendo 5 llamadas consecutivas a /me...")
    
    me_responses = []
    for i in range(5):
        try:
            start_time = time.time()
            response = requests.get(
                f"{backend_url}/api/v1/auth/me",
                headers=headers,
                timeout=30
            )
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                me_responses.append({
                    "call": i + 1,
                    "time": end_time - start_time,
                    "is_admin": data.get('is_admin'),
                    "email": data.get('email'),
                    "timestamp": datetime.now().isoformat()
                })
                logger.info(f"   📊 Llamada {i + 1}: {end_time - start_time:.3f}s, is_admin: {data.get('is_admin')}")
            else:
                logger.error(f"   ❌ Llamada {i + 1}: Status {response.status_code}")
                
        except Exception as e:
            logger.error(f"   ❌ Llamada {i + 1}: Error - {e}")
        
        # Pequeña pausa entre llamadas
        time.sleep(0.5)
    
    # Verificar consistencia
    logger.info(f"\n🔍 ANÁLISIS DE CONSISTENCIA:")
    if me_responses:
        is_admin_values = [resp["is_admin"] for resp in me_responses]
        unique_values = set(is_admin_values)
        
        logger.info(f"   📊 Valores únicos de is_admin: {unique_values}")
        logger.info(f"   📊 Total respuestas: {len(me_responses)}")
        
        if len(unique_values) == 1:
            logger.info("✅ CONSISTENCIA: Todas las respuestas tienen el mismo valor")
            logger.info(f"   🔑 Valor consistente: {list(unique_values)[0]}")
        else:
            logger.error("❌ INCONSISTENCIA: Las respuestas tienen valores diferentes")
            logger.error(f"   🔑 Valores encontrados: {unique_values}")
    
    # 3. SIMULAR PROBLEMA DE CACHÉ DEL FRONTEND
    logger.info("\n💾 3. SIMULANDO PROBLEMA DE CACHÉ DEL FRONTEND")
    logger.info("-" * 50)
    
    # Simular diferentes escenarios de caché
    cache_scenarios = [
        {
            "nombre": "Datos frescos del backend",
            "descripcion": "Datos obtenidos directamente del backend",
            "is_admin": True,
            "timestamp": datetime.now().isoformat()
        },
        {
            "nombre": "Datos obsoletos en localStorage",
            "descripcion": "Datos cacheados antiguos (antes del cambio)",
            "is_admin": False,
            "timestamp": "2025-01-01T00:00:00"
        },
        {
            "nombre": "Datos corruptos en sessionStorage",
            "descripcion": "Datos con problemas de serialización",
            "is_admin": None,
            "timestamp": datetime.now().isoformat()
        },
        {
            "nombre": "Datos parciales",
            "descripcion": "Datos incompletos (falta is_admin)",
            "is_admin": "undefined",
            "timestamp": datetime.now().isoformat()
        }
    ]
    
    logger.info("📋 Escenarios de caché simulados:")
    for scenario in cache_scenarios:
        logger.info(f"   📊 {scenario['nombre']}:")
        logger.info(f"      🔑 is_admin: {scenario['is_admin']} ({type(scenario['is_admin'])})")
        logger.info(f"      📝 Descripción: {scenario['descripcion']}")
        logger.info(f"      ⏰ Timestamp: {scenario['timestamp']}")
        
        # Simular lógica del frontend para cada escenario
        if scenario['is_admin'] is True:
            user_role = "Administrador"
            logger.info(f"      🎭 Frontend mostraría: {user_role}")
        elif scenario['is_admin'] is False:
            user_role = "Usuario"
            logger.info(f"      🎭 Frontend mostraría: {user_role}")
        else:
            user_role = "Error/Indefinido"
            logger.info(f"      🎭 Frontend mostraría: {user_role}")
        
        logger.info("")
    
    # 4. SIMULAR TIMING DE ACTUALIZACIONES
    logger.info("\n⏰ 4. SIMULANDO TIMING DE ACTUALIZACIONES")
    logger.info("-" * 50)
    
    # Simular diferentes momentos de actualización
    update_timings = [
        {
            "momento": "Al hacer login",
            "descripcion": "Datos obtenidos durante el proceso de login",
            "probabilidad_correcta": 0.95
        },
        {
            "momento": "Al inicializar la aplicación",
            "descripcion": "Datos obtenidos al cargar la página",
            "probabilidad_correcta": 0.80
        },
        {
            "momento": "Al refrescar usuario",
            "descripcion": "Datos obtenidos manualmente",
            "probabilidad_correcta": 0.90
        },
        {
            "momento": "Al cambiar de página",
            "descripcion": "Datos obtenidos al navegar",
            "probabilidad_correcta": 0.70
        }
    ]
    
    logger.info("📊 Probabilidades de datos correctos por momento:")
    for timing in update_timings:
        logger.info(f"   ⏰ {timing['momento']}: {timing['probabilidad_correcta']*100:.0f}%")
        logger.info(f"      📝 {timing['descripcion']}")
    
    # 5. IDENTIFICAR PUNTOS CRÍTICOS DE FALLA
    logger.info("\n🚨 5. IDENTIFICANDO PUNTOS CRÍTICOS DE FALLA")
    logger.info("-" * 50)
    
    critical_points = [
        {
            "punto": "Serialización en localStorage",
            "riesgo": "Alto",
            "descripcion": "Los datos pueden corromperse al almacenar",
            "solucion": "Usar funciones de almacenamiento seguro"
        },
        {
            "punto": "Deserialización desde localStorage",
            "riesgo": "Alto",
            "descripcion": "Los datos pueden corromperse al recuperar",
            "solucion": "Validar datos al recuperar"
        },
        {
            "punto": "Timing de initializeAuth()",
            "riesgo": "Medio",
            "descripcion": "Puede ejecutarse antes de que el backend esté listo",
            "solucion": "Agregar retry logic"
        },
        {
            "punto": "Timing de refreshUser()",
            "riesgo": "Medio",
            "descripcion": "Puede fallar si hay problemas de red",
            "solucion": "Manejar errores gracefully"
        },
        {
            "punto": "Caché del navegador",
            "riesgo": "Bajo",
            "descripcion": "El navegador puede cachear respuestas",
            "solucion": "Usar headers de no-cache"
        }
    ]
    
    logger.info("📋 Puntos críticos de falla:")
    for point in critical_points:
        logger.info(f"   🚨 {point['punto']} (Riesgo: {point['riesgo']})")
        logger.info(f"      📝 {point['descripcion']}")
        logger.info(f"      💡 Solución: {point['solucion']}")
        logger.info("")
    
    # 6. CONCLUSIÓN FINAL
    logger.info("\n📊 CONCLUSIÓN FINAL DE TIMING Y CACHÉ")
    logger.info("=" * 80)
    
    logger.info("🎯 HALLAZGOS PRINCIPALES:")
    
    # Analizar tiempos
    if successful_endpoints:
        avg_time = sum(response_times[ep]["time"] for ep in successful_endpoints) / len(successful_endpoints)
        if avg_time > 3:
            logger.warning(f"   ⏱️ Tiempo de respuesta alto: {avg_time:.3f}s")
        else:
            logger.info(f"   ⏱️ Tiempo de respuesta aceptable: {avg_time:.3f}s")
    
    # Analizar consistencia
    if me_responses:
        is_admin_values = [resp["is_admin"] for resp in me_responses]
        unique_values = set(is_admin_values)
        if len(unique_values) == 1:
            logger.info("   ✅ Consistencia en respuestas del backend")
        else:
            logger.error("   ❌ Inconsistencia en respuestas del backend")
    
    # Recomendaciones
    logger.info("\n💡 RECOMENDACIONES:")
    logger.info("   1. Implementar retry logic en funciones críticas")
    logger.info("   2. Agregar validación de datos al recuperar del storage")
    logger.info("   3. Usar headers de no-cache para endpoints críticos")
    logger.info("   4. Implementar fallback cuando refreshUser() falla")
    logger.info("   5. Agregar logging detallado para debugging")
    
    return True

if __name__ == "__main__":
    verificar_timing_cache()
