# backend/scripts/verificar_datos_tiempo_real.py
"""
VERIFICACIÓN DE DATOS EN TIEMPO REAL - SEXTA AUDITORÍA
Verificar datos en tiempo real en producción para confirmar corrección
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

def verificar_datos_tiempo_real():
    """
    Verificar datos en tiempo real en producción
    """
    logger.info("⏰ VERIFICACIÓN DE DATOS EN TIEMPO REAL EN PRODUCCIÓN")
    logger.info("=" * 80)
    logger.info(f"📅 Fecha y hora: {datetime.now()}")
    logger.info("🎯 Objetivo: Verificar datos en tiempo real para confirmar corrección")
    logger.info("=" * 80)
    
    backend_url = "https://pagos-f2qf.onrender.com"
    
    # Credenciales exactas
    credentials = {
        "email": "itmaster@rapicreditca.com",
        "password": "R@pi_2025**",
        "remember": True
    }
    
    # 1. VERIFICAR ESTADO DEL BACKEND
    logger.info("🔍 1. VERIFICANDO ESTADO DEL BACKEND")
    logger.info("-" * 50)
    
    try:
        # Verificar health check
        response = requests.get(f"{backend_url}/api/v1/health", timeout=10)
        logger.info(f"📊 Health Check Status: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("✅ Backend está funcionando")
        else:
            logger.warning(f"⚠️ Backend con problemas: {response.status_code}")
            
    except Exception as e:
        logger.error(f"❌ Error verificando backend: {e}")
    
    # 2. REALIZAR MÚLTIPLES LOGINS PARA VERIFICAR CONSISTENCIA
    logger.info("\n🔄 2. REALIZANDO MÚLTIPLES LOGINS PARA VERIFICAR CONSISTENCIA")
    logger.info("-" * 50)
    
    login_results = []
    
    for i in range(3):
        logger.info(f"🔐 Login #{i + 1}/3:")
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{backend_url}/api/v1/auth/login",
                json=credentials,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            end_time = time.time()
            
            duration = end_time - start_time
            logger.info(f"   📊 Duration: {duration:.3f}s")
            logger.info(f"   📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                login_data = response.json()
                user_data = login_data.get('user', {})
                
                result = {
                    "login_number": i + 1,
                    "duration": duration,
                    "status": response.status_code,
                    "is_admin": user_data.get('is_admin'),
                    "email": user_data.get('email'),
                    "nombre": user_data.get('nombre'),
                    "apellido": user_data.get('apellido'),
                    "cargo": user_data.get('cargo'),
                    "timestamp": datetime.now().isoformat()
                }
                
                login_results.append(result)
                
                logger.info(f"   ✅ Usuario: {user_data.get('nombre')} {user_data.get('apellido')}")
                logger.info(f"   🔑 is_admin: {user_data.get('is_admin')}")
                logger.info(f"   💼 Cargo: {user_data.get('cargo')}")
                
            else:
                logger.error(f"   ❌ Login falló: {response.status_code}")
                
        except Exception as e:
            logger.error(f"   ❌ Error en login #{i + 1}: {e}")
        
        # Pausa entre logins
        if i < 2:
            time.sleep(1)
    
    # Analizar consistencia de logins
    logger.info(f"\n📊 ANÁLISIS DE CONSISTENCIA DE LOGINS:")
    logger.info(f"   📈 Logins exitosos: {len(login_results)}/3")
    
    if login_results:
        is_admin_values = [r['is_admin'] for r in login_results]
        unique_values = set(is_admin_values)
        
        logger.info(f"   🔑 Valores únicos de is_admin: {unique_values}")
        
        if len(unique_values) == 1:
            logger.info("   ✅ CONSISTENCIA PERFECTA: Todos los logins retornan el mismo valor")
            logger.info(f"   🎯 Valor consistente: {list(unique_values)[0]}")
        else:
            logger.error("   ❌ INCONSISTENCIA: Los logins retornan valores diferentes")
            logger.error(f"   🔑 Valores encontrados: {unique_values}")
    
    # 3. VERIFICAR ENDPOINT /me MÚLTIPLES VECES
    logger.info("\n🔍 3. VERIFICANDO ENDPOINT /me MÚLTIPLES VECES")
    logger.info("-" * 50)
    
    if not login_results:
        logger.error("❌ No hay datos de login para probar /me")
        return False
    
    # Usar el último login exitoso
    last_login = login_results[-1]
    
    # Obtener token del último login
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
            
            if not access_token:
                logger.error("❌ No se pudo obtener token para probar /me")
                return False
            
            logger.info("✅ Token obtenido para pruebas de /me")
            
        else:
            logger.error(f"❌ No se pudo obtener token: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error obteniendo token: {e}")
        return False
    
    # Probar /me múltiples veces
    me_results = []
    
    for i in range(3):
        logger.info(f"🔍 /me #{i + 1}/3:")
        
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            start_time = time.time()
            response = requests.get(
                f"{backend_url}/api/v1/auth/me",
                headers=headers,
                timeout=30
            )
            end_time = time.time()
            
            duration = end_time - start_time
            logger.info(f"   📊 Duration: {duration:.3f}s")
            logger.info(f"   📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                me_data = response.json()
                
                result = {
                    "me_number": i + 1,
                    "duration": duration,
                    "status": response.status_code,
                    "is_admin": me_data.get('is_admin'),
                    "email": me_data.get('email'),
                    "nombre": me_data.get('nombre'),
                    "apellido": me_data.get('apellido'),
                    "cargo": me_data.get('cargo'),
                    "permissions_count": len(me_data.get('permissions', [])),
                    "timestamp": datetime.now().isoformat()
                }
                
                me_results.append(result)
                
                logger.info(f"   ✅ Usuario: {me_data.get('nombre')} {me_data.get('apellido')}")
                logger.info(f"   🔑 is_admin: {me_data.get('is_admin')}")
                logger.info(f"   🔐 Permisos: {len(me_data.get('permissions', []))}")
                
            else:
                logger.error(f"   ❌ /me falló: {response.status_code}")
                
        except Exception as e:
            logger.error(f"   ❌ Error en /me #{i + 1}: {e}")
        
        # Pausa entre llamadas
        if i < 2:
            time.sleep(1)
    
    # Analizar consistencia de /me
    logger.info(f"\n📊 ANÁLISIS DE CONSISTENCIA DE /me:")
    logger.info(f"   📈 Llamadas exitosas: {len(me_results)}/3")
    
    if me_results:
        is_admin_values = [r['is_admin'] for r in me_results]
        unique_values = set(is_admin_values)
        
        logger.info(f"   🔑 Valores únicos de is_admin: {unique_values}")
        
        if len(unique_values) == 1:
            logger.info("   ✅ CONSISTENCIA PERFECTA: Todas las llamadas retornan el mismo valor")
            logger.info(f"   🎯 Valor consistente: {list(unique_values)[0]}")
        else:
            logger.error("   ❌ INCONSISTENCIA: Las llamadas retornan valores diferentes")
            logger.error(f"   🔑 Valores encontrados: {unique_values}")
    
    # 4. COMPARAR LOGIN vs /me EN TIEMPO REAL
    logger.info("\n🔄 4. COMPARANDO LOGIN vs /me EN TIEMPO REAL")
    logger.info("-" * 50)
    
    if login_results and me_results:
        # Usar los últimos resultados
        last_login_result = login_results[-1]
        last_me_result = me_results[-1]
        
        logger.info("📊 COMPARACIÓN EN TIEMPO REAL:")
        logger.info(f"   🔐 Login is_admin: {last_login_result['is_admin']}")
        logger.info(f"   🔐 /me is_admin: {last_me_result['is_admin']}")
        logger.info(f"   📧 Login email: {last_login_result['email']}")
        logger.info(f"   📧 /me email: {last_me_result['email']}")
        logger.info(f"   👤 Login nombre: {last_login_result['nombre']} {last_login_result['apellido']}")
        logger.info(f"   👤 /me nombre: {last_me_result['nombre']} {last_me_result['apellido']}")
        
        # Verificar consistencia crítica
        if last_login_result['is_admin'] == last_me_result['is_admin']:
            logger.info("   ✅ CONSISTENCIA CRÍTICA: Ambos endpoints retornan el mismo is_admin")
            
            if last_login_result['is_admin'] is True:
                logger.info("   🎯 RESULTADO: Usuario ES administrador en ambos endpoints")
                logger.info("   ✅ CORRECCIÓN CONFIRMADA: El problema está resuelto")
            elif last_login_result['is_admin'] is False:
                logger.error("   🎯 RESULTADO: Usuario NO es administrador en ambos endpoints")
                logger.error("   ❌ PROBLEMA PERSISTENTE: Usuario no es admin en BD")
            else:
                logger.error(f"   🎯 RESULTADO INESPERADO: is_admin = {last_login_result['is_admin']}")
        else:
            logger.error("   ❌ INCONSISTENCIA CRÍTICA: Los endpoints retornan valores diferentes")
            logger.error("   🔍 CAUSA: La corrección no fue aplicada correctamente")
    
    # 5. VERIFICAR TIMING Y PERFORMANCE
    logger.info("\n⏱️ 5. VERIFICANDO TIMING Y PERFORMANCE")
    logger.info("-" * 50)
    
    if login_results:
        avg_login_time = sum(r['duration'] for r in login_results) / len(login_results)
        logger.info(f"📊 Tiempo promedio de login: {avg_login_time:.3f}s")
        
        if avg_login_time < 1:
            logger.info("✅ PERFORMANCE EXCELENTE: Login muy rápido")
        elif avg_login_time < 3:
            logger.info("✅ PERFORMANCE BUENA: Login aceptable")
        else:
            logger.warning("⚠️ PERFORMANCE LENTA: Login toma mucho tiempo")
    
    if me_results:
        avg_me_time = sum(r['duration'] for r in me_results) / len(me_results)
        logger.info(f"📊 Tiempo promedio de /me: {avg_me_time:.3f}s")
        
        if avg_me_time < 0.5:
            logger.info("✅ PERFORMANCE EXCELENTE: /me muy rápido")
        elif avg_me_time < 1:
            logger.info("✅ PERFORMANCE BUENA: /me aceptable")
        else:
            logger.warning("⚠️ PERFORMANCE LENTA: /me toma mucho tiempo")
    
    # 6. CONCLUSIÓN FINAL
    logger.info("\n📊 CONCLUSIÓN FINAL DE VERIFICACIÓN EN TIEMPO REAL")
    logger.info("=" * 80)
    
    logger.info("🎯 RESULTADOS DE LA VERIFICACIÓN EN TIEMPO REAL:")
    logger.info(f"   🔐 Logins exitosos: {len(login_results)}/3")
    logger.info(f"   🔍 Llamadas /me exitosas: {len(me_results)}/3")
    
    if login_results and me_results:
        last_login_result = login_results[-1]
        last_me_result = me_results[-1]
        
        logger.info(f"   🔑 is_admin en login: {last_login_result['is_admin']}")
        logger.info(f"   🔑 is_admin en /me: {last_me_result['is_admin']}")
        logger.info(f"   ✅ Consistencia: {last_login_result['is_admin'] == last_me_result['is_admin']}")
        
        if last_login_result['is_admin'] == last_me_result['is_admin'] == True:
            logger.info("\n✅ VERIFICACIÓN EN TIEMPO REAL EXITOSA:")
            logger.info("   🎯 La corrección está funcionando en producción")
            logger.info("   🎯 Los datos son consistentes entre endpoints")
            logger.info("   🎯 El usuario es correctamente identificado como admin")
            logger.info("   🎯 El problema 'Rol: USER' está resuelto")
        elif last_login_result['is_admin'] == last_me_result['is_admin'] == False:
            logger.error("\n❌ VERIFICACIÓN EN TIEMPO REAL FALLIDA:")
            logger.error("   🔍 El usuario no es admin en base de datos")
            logger.error("   🔍 La corrección no puede resolver este problema")
            logger.error("   💡 SOLUCIÓN: Actualizar is_admin en base de datos")
        else:
            logger.error("\n❌ VERIFICACIÓN EN TIEMPO REAL INCONSISTENTE:")
            logger.error("   🔍 Los endpoints aún son inconsistentes")
            logger.error("   🔍 La corrección no fue aplicada correctamente")
            logger.error("   💡 SOLUCIÓN: Revisar y reaplicar la corrección")
    else:
        logger.error("\n❌ VERIFICACIÓN EN TIEMPO REAL INCOMPLETA:")
        logger.error("   🔍 No se pudieron obtener datos suficientes")
        logger.error("   💡 SOLUCIÓN: Revisar conectividad y endpoints")
    
    return True

if __name__ == "__main__":
    verificar_datos_tiempo_real()
