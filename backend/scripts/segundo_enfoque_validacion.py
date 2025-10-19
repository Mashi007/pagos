#!/usr/bin/env python3
"""
SEGUNDO ENFOQUE DE VALIDACIÓN - ANÁLISIS PROFUNDO DE ERRORES
Verificación exhaustiva de errores y posibles causas después de correcciones
"""

import requests
import os
import logging
import time
import subprocess
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = os.getenv("FRONTEND_URL", "https://pagos-f2qf.onrender.com")

def enfoque_1_verificacion_sintaxis_codigo():
    """ENFOQUE 1: Verificación exhaustiva de sintaxis en código crítico"""
    logger.info("")
    logger.info("🔍 ENFOQUE 1: VERIFICACIÓN DE SINTAXIS EN CÓDIGO CRÍTICO")
    logger.info("=" * 70)
    logger.info("📋 Objetivo: Verificar que no hay errores de sintaxis en archivos críticos")
    
    archivos_criticos = [
        "backend/app/api/v1/endpoints/auth.py",
        "backend/app/api/v1/endpoints/users.py", 
        "backend/app/api/v1/endpoints/analistas.py",
        "backend/app/core/security_audit.py",
        "backend/app/utils/auditoria_helper.py",
        "backend/app/schemas/user.py",
        "backend/app/models/user.py",
        "backend/app/main.py"
    ]
    
    errores_encontrados = []
    
    for archivo in archivos_criticos:
        logger.info(f"📄 Verificando: {archivo}")
        try:
            # Verificar sintaxis Python
            result = subprocess.run([
                "python", "-m", "py_compile", archivo
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"   ✅ Sintaxis correcta")
            else:
                logger.error(f"   ❌ Error de sintaxis:")
                logger.error(f"      {result.stderr}")
                errores_encontrados.append((archivo, result.stderr))
                
        except Exception as e:
            logger.error(f"   ❌ Error verificando archivo: {e}")
            errores_encontrados.append((archivo, str(e)))
    
    logger.info("")
    logger.info("📊 RESUMEN ENFOQUE 1:")
    logger.info("-" * 40)
    if errores_encontrados:
        logger.error(f"❌ Errores encontrados: {len(errores_encontrados)}")
        for archivo, error in errores_encontrados:
            logger.error(f"   📄 {archivo}: {error}")
    else:
        logger.info("✅ Todos los archivos críticos tienen sintaxis correcta")
    
    return len(errores_encontrados) == 0

def enfoque_2_verificacion_imports_dependencias():
    """ENFOQUE 2: Verificación de imports y dependencias"""
    logger.info("")
    logger.info("🔍 ENFOQUE 2: VERIFICACIÓN DE IMPORTS Y DEPENDENCIAS")
    logger.info("=" * 70)
    logger.info("📋 Objetivo: Verificar que todos los imports están correctos")
    
    # Verificar imports críticos
    imports_criticos = [
        ("backend/app/api/v1/endpoints/auth.py", ["import logging", "logger = logging.getLogger"]),
        ("backend/app/core/security_audit.py", ["import logging", "security_audit_logger = logging.getLogger"]),
        ("backend/app/utils/auditoria_helper.py", ["import logging", "logger = logging.getLogger"]),
        ("backend/app/schemas/user.py", ["from pydantic import", "field_validator"]),
        ("backend/app/api/v1/endpoints/users.py", ["import logging", "logger = logging.getLogger"])
    ]
    
    problemas_encontrados = []
    
    for archivo, imports_requeridos in imports_criticos:
        logger.info(f"📄 Verificando imports en: {archivo}")
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            imports_faltantes = []
            for import_req in imports_requeridos:
                if import_req not in contenido:
                    imports_faltantes.append(import_req)
            
            if imports_faltantes:
                logger.error(f"   ❌ Imports faltantes: {imports_faltantes}")
                problemas_encontrados.append((archivo, imports_faltantes))
            else:
                logger.info(f"   ✅ Todos los imports presentes")
                
        except Exception as e:
            logger.error(f"   ❌ Error leyendo archivo: {e}")
            problemas_encontrados.append((archivo, [str(e)]))
    
    logger.info("")
    logger.info("📊 RESUMEN ENFOQUE 2:")
    logger.info("-" * 40)
    if problemas_encontrados:
        logger.error(f"❌ Problemas encontrados: {len(problemas_encontrados)}")
        for archivo, problemas in problemas_encontrados:
            logger.error(f"   📄 {archivo}: {problemas}")
    else:
        logger.info("✅ Todos los imports están correctos")
    
    return len(problemas_encontrados) == 0

def enfoque_3_verificacion_conectividad_servidor():
    """ENFOQUE 3: Verificación exhaustiva de conectividad del servidor"""
    logger.info("")
    logger.info("🔍 ENFOQUE 3: VERIFICACIÓN DE CONECTIVIDAD DEL SERVIDOR")
    logger.info("=" * 70)
    logger.info("📋 Objetivo: Verificar estado completo del servidor")
    
    endpoints_criticos = [
        ("/", "GET", "Servidor principal"),
        ("/api/v1/auth/login", "OPTIONS", "CORS Login"),
        ("/api/v1/auth/me", "OPTIONS", "CORS Me"),
        ("/api/v1/usuarios/", "OPTIONS", "CORS Usuarios"),
        ("/api/v1/analistas/", "OPTIONS", "CORS Analistas"),
        ("/docs", "GET", "Documentación API")
    ]
    
    problemas_conectividad = []
    
    for endpoint, metodo, descripcion in endpoints_criticos:
        logger.info(f"🌐 Verificando: {descripcion} ({metodo} {endpoint})")
        try:
            if metodo == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            elif metodo == "OPTIONS":
                response = requests.options(f"{BASE_URL}{endpoint}", timeout=10)
            
            logger.info(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code in [200, 405]:  # 405 es normal para algunos endpoints
                logger.info(f"   ✅ {descripcion} disponible")
            else:
                logger.warning(f"   ⚠️ {descripcion} responde con código inesperado: {response.status_code}")
                problemas_conectividad.append((endpoint, response.status_code))
                
        except requests.exceptions.Timeout:
            logger.error(f"   ❌ Timeout en {descripcion}")
            problemas_conectividad.append((endpoint, "TIMEOUT"))
        except requests.exceptions.ConnectionError:
            logger.error(f"   ❌ Error de conexión en {descripcion}")
            problemas_conectividad.append((endpoint, "CONNECTION_ERROR"))
        except Exception as e:
            logger.error(f"   ❌ Error inesperado en {descripcion}: {e}")
            problemas_conectividad.append((endpoint, str(e)))
    
    logger.info("")
    logger.info("📊 RESUMEN ENFOQUE 3:")
    logger.info("-" * 40)
    if problemas_conectividad:
        logger.error(f"❌ Problemas de conectividad: {len(problemas_conectividad)}")
        for endpoint, problema in problemas_conectividad:
            logger.error(f"   🌐 {endpoint}: {problema}")
    else:
        logger.info("✅ Todos los endpoints están disponibles")
    
    return len(problemas_conectividad) == 0

def enfoque_4_verificacion_autenticacion_detallada():
    """ENFOQUE 4: Verificación detallada del sistema de autenticación"""
    logger.info("")
    logger.info("🔍 ENFOQUE 4: VERIFICACIÓN DETALLADA DE AUTENTICACIÓN")
    logger.info("=" * 70)
    logger.info("📋 Objetivo: Verificar funcionamiento completo del sistema de auth")
    
    # Credenciales de prueba
    credenciales_admin = {
        "email": "itmaster@rapicreditca.com",
        "password": "admin123",
        "remember": True
    }
    
    credenciales_usuario = {
        "email": "prueba2@gmail.com", 
        "password": "Casa1803",
        "remember": True
    }
    
    problemas_auth = []
    
    # Probar login admin
    logger.info("🔑 Probando login de administrador...")
    try:
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=credenciales_admin, timeout=15)
        logger.info(f"   📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"   ✅ Login admin exitoso")
            logger.info(f"   📊 Usuario: {data['user']['email']}")
            logger.info(f"   📊 Rol: {'Admin' if data['user']['is_admin'] else 'Usuario'}")
            
            # Probar endpoint /me con token
            token = data['access_token']
            headers = {"Authorization": f"Bearer {token}"}
            
            logger.info("🔍 Probando endpoint /me...")
            me_response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers, timeout=10)
            logger.info(f"   📊 Status Code: {me_response.status_code}")
            
            if me_response.status_code == 200:
                logger.info("   ✅ Endpoint /me funcionando")
            else:
                logger.error(f"   ❌ Error en /me: {me_response.status_code}")
                problemas_auth.append(("/me", me_response.status_code))
                
        else:
            logger.error(f"   ❌ Error en login admin: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            problemas_auth.append(("login_admin", response.status_code))
            
    except Exception as e:
        logger.error(f"   ❌ Error en login admin: {e}")
        problemas_auth.append(("login_admin", str(e)))
    
    # Probar login usuario regular
    logger.info("")
    logger.info("👤 Probando login de usuario regular...")
    try:
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=credenciales_usuario, timeout=15)
        logger.info(f"   📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"   ✅ Login usuario exitoso")
            logger.info(f"   📊 Usuario: {data['user']['email']}")
            logger.info(f"   📊 Rol: {'Admin' if data['user']['is_admin'] else 'Usuario'}")
        else:
            logger.error(f"   ❌ Error en login usuario: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            problemas_auth.append(("login_usuario", response.status_code))
            
    except Exception as e:
        logger.error(f"   ❌ Error en login usuario: {e}")
        problemas_auth.append(("login_usuario", str(e)))
    
    logger.info("")
    logger.info("📊 RESUMEN ENFOQUE 4:")
    logger.info("-" * 40)
    if problemas_auth:
        logger.error(f"❌ Problemas de autenticación: {len(problemas_auth)}")
        for endpoint, problema in problemas_auth:
            logger.error(f"   🔐 {endpoint}: {problema}")
    else:
        logger.info("✅ Sistema de autenticación funcionando correctamente")
    
    return len(problemas_auth) == 0

def enfoque_5_verificacion_endpoints_criticos():
    """ENFOQUE 5: Verificación de endpoints críticos con autenticación"""
    logger.info("")
    logger.info("🔍 ENFOQUE 5: VERIFICACIÓN DE ENDPOINTS CRÍTICOS")
    logger.info("=" * 70)
    logger.info("📋 Objetivo: Verificar endpoints críticos con autenticación")
    
    # Primero obtener token de admin
    logger.info("🔑 Obteniendo token de administrador...")
    try:
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", 
                               json={"email": "itmaster@rapicreditca.com", "password": "admin123", "remember": True}, 
                               timeout=15)
        
        if response.status_code != 200:
            logger.error("❌ No se pudo obtener token de admin")
            return False
            
        token = response.json()['access_token']
        headers = {"Authorization": f"Bearer {token}"}
        logger.info("✅ Token de administrador obtenido")
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo token: {e}")
        return False
    
    # Endpoints críticos a verificar
    endpoints_criticos = [
        ("/api/v1/usuarios/?page=1&page_size=10", "Lista de usuarios"),
        ("/api/v1/analistas/", "Lista de analistas"),
        ("/api/v1/clientes/?page=1&page_size=10", "Lista de clientes"),
        ("/api/v1/prestamos/?page=1&page_size=10", "Lista de préstamos"),
        ("/api/v1/pagos/?page=1&page_size=10", "Lista de pagos")
    ]
    
    problemas_endpoints = []
    
    for endpoint, descripcion in endpoints_criticos:
        logger.info(f"🔗 Verificando: {descripcion}")
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=15)
            logger.info(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                total = data.get('total', len(data.get('items', [])))
                logger.info(f"   ✅ {descripcion} funcionando")
                logger.info(f"   📊 Total registros: {total}")
            else:
                logger.error(f"   ❌ Error en {descripcion}: {response.status_code}")
                logger.error(f"   📊 Respuesta: {response.text}")
                problemas_endpoints.append((endpoint, response.status_code))
                
        except Exception as e:
            logger.error(f"   ❌ Error en {descripcion}: {e}")
            problemas_endpoints.append((endpoint, str(e)))
    
    logger.info("")
    logger.info("📊 RESUMEN ENFOQUE 5:")
    logger.info("-" * 40)
    if problemas_endpoints:
        logger.error(f"❌ Problemas en endpoints: {len(problemas_endpoints)}")
        for endpoint, problema in problemas_endpoints:
            logger.error(f"   🔗 {endpoint}: {problema}")
    else:
        logger.info("✅ Todos los endpoints críticos funcionando")
    
    return len(problemas_endpoints) == 0

def enfoque_6_verificacion_logs_errores():
    """ENFOQUE 6: Verificación de logs y errores en tiempo real"""
    logger.info("")
    logger.info("🔍 ENFOQUE 6: VERIFICACIÓN DE LOGS Y ERRORES")
    logger.info("=" * 70)
    logger.info("📋 Objetivo: Detectar errores en logs después de las correcciones")
    
    # Realizar operaciones que generen logs
    operaciones_log = [
        ("login_admin", lambda: requests.post(f"{BASE_URL}/api/v1/auth/login", 
                                           json={"email": "itmaster@rapicreditca.com", "password": "admin123", "remember": True})),
        ("login_fail", lambda: requests.post(f"{BASE_URL}/api/v1/auth/login", 
                                           json={"email": "test@test.com", "password": "wrong", "remember": True})),
        ("endpoint_test", lambda: requests.get(f"{BASE_URL}/api/v1/usuarios/?page=1&page_size=5"))
    ]
    
    errores_detectados = []
    
    for nombre_op, operacion in operaciones_log:
        logger.info(f"📝 Ejecutando operación: {nombre_op}")
        try:
            response = operacion()
            logger.info(f"   📊 Status Code: {response.status_code}")
            
            # Verificar si la respuesta contiene errores de logger
            if "logger" in response.text.lower() and "not defined" in response.text.lower():
                logger.error(f"   ❌ Error de logger detectado en respuesta")
                errores_detectados.append((nombre_op, "LOGGER_ERROR"))
            else:
                logger.info(f"   ✅ Operación ejecutada sin errores de logger")
                
        except Exception as e:
            logger.error(f"   ❌ Error en operación: {e}")
            errores_detectados.append((nombre_op, str(e)))
    
    logger.info("")
    logger.info("📊 RESUMEN ENFOQUE 6:")
    logger.info("-" * 40)
    if errores_detectados:
        logger.error(f"❌ Errores detectados: {len(errores_detectados)}")
        for operacion, error in errores_detectados:
            logger.error(f"   📝 {operacion}: {error}")
    else:
        logger.info("✅ No se detectaron errores de logger en las operaciones")
    
    return len(errores_detectados) == 0

def main():
    logger.info("🔍 SEGUNDO ENFOQUE DE VALIDACIÓN - ANÁLISIS PROFUNDO")
    logger.info("=" * 80)
    logger.info(f"📊 Fecha y hora: {datetime.now()}")
    logger.info("🎯 Objetivo: Verificación exhaustiva de errores y posibles causas")
    logger.info("🔧 Contexto: Después de correcciones de logger")
    logger.info("=" * 80)
    
    # Ejecutar todos los enfoques
    resultados = {}
    
    resultados["Sintaxis"] = enfoque_1_verificacion_sintaxis_codigo()
    resultados["Imports"] = enfoque_2_verificacion_imports_dependencias()
    resultados["Conectividad"] = enfoque_3_verificacion_conectividad_servidor()
    resultados["Autenticación"] = enfoque_4_verificacion_autenticacion_detallada()
    resultados["Endpoints"] = enfoque_5_verificacion_endpoints_criticos()
    resultados["Logs"] = enfoque_6_verificacion_logs_errores()
    
    # Resumen final
    logger.info("")
    logger.info("📊 RESUMEN FINAL DEL SEGUNDO ENFOQUE")
    logger.info("=" * 80)
    
    exitosos = sum(resultados.values())
    total = len(resultados)
    
    logger.info(f"🎯 Enfoques ejecutados: {total}")
    logger.info(f"✅ Enfoques exitosos: {exitosos}")
    logger.info(f"❌ Enfoques con problemas: {total - exitosos}")
    logger.info(f"📈 Tasa de éxito: {(exitosos/total)*100:.1f}%")
    logger.info("")
    
    logger.info("📋 DETALLE DE RESULTADOS:")
    logger.info("-" * 50)
    for enfoque, resultado in resultados.items():
        estado = "✅ EXITOSO" if resultado else "❌ CON PROBLEMAS"
        logger.info(f"   {enfoque}: {estado}")
    
    logger.info("")
    if exitosos == total:
        logger.info("🎉 SEGUNDO ENFOQUE COMPLETAMENTE EXITOSO")
        logger.info("   ✅ Todos los sistemas verificados correctamente")
        logger.info("   ✅ No se detectaron errores críticos")
        logger.info("   ✅ Sistema listo para casos reales")
    else:
        logger.error("❌ SEGUNDO ENFOQUE DETECTÓ PROBLEMAS")
        logger.error("   💡 Revisar resultados específicos para identificar causas")
        logger.error("   💡 Aplicar correcciones adicionales según sea necesario")

if __name__ == "__main__":
    main()
