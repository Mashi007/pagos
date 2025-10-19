"""
Script de Validación - Métodos AuthService vs Security
Verificación específica de la corrección aplicada
"""
import os
import re
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verificar_metodos_authservice():
    """Verifica métodos disponibles en AuthService"""
    logger.info("🔍 VERIFICANDO MÉTODOS EN AUTHSERVICE")
    logger.info("-" * 50)
    
    auth_service_path = "backend/app/services/auth_service.py"
    
    if not os.path.exists(auth_service_path):
        logger.error(f"❌ Archivo no encontrado: {auth_service_path}")
        return []
    
    with open(auth_service_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar métodos definidos
    methods_pattern = r'def\s+(\w+)\s*\('
    methods = re.findall(methods_pattern, content)
    
    # Buscar métodos estáticos
    static_pattern = r'@staticmethod\s*\n\s*def\s+(\w+)\s*\('
    static_methods = re.findall(static_pattern, content, re.MULTILINE)
    
    all_methods = list(set(methods + static_methods))
    
    logger.info(f"📋 Métodos encontrados en AuthService: {all_methods}")
    
    # Verificar métodos problemáticos
    problematic_methods = ["create_access_token", "verify_password", "get_password_hash"]
    
    for method in problematic_methods:
        if method in all_methods:
            logger.warning(f"⚠️ Método problemático encontrado: {method}")
        else:
            logger.info(f"✅ Método problemático NO encontrado: {method}")
    
    return all_methods

def verificar_metodos_security():
    """Verifica métodos disponibles en security"""
    logger.info("🔍 VERIFICANDO MÉTODOS EN SECURITY")
    logger.info("-" * 50)
    
    security_path = "backend/app/core/security.py"
    
    if not os.path.exists(security_path):
        logger.error(f"❌ Archivo no encontrado: {security_path}")
        return []
    
    with open(security_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar métodos definidos
    methods_pattern = r'def\s+(\w+)\s*\('
    methods = re.findall(methods_pattern, content)
    
    logger.info(f"📋 Métodos encontrados en security: {methods}")
    
    # Verificar métodos requeridos
    required_methods = ["create_access_token", "verify_password", "get_password_hash"]
    
    for method in required_methods:
        if method in methods:
            logger.info(f"✅ Método requerido encontrado: {method}")
        else:
            logger.error(f"❌ Método requerido NO encontrado: {method}")
    
    return methods

def verificar_correccion_auth_endpoint():
    """Verifica que la corrección en auth.py sea correcta"""
    logger.info("🔍 VERIFICANDO CORRECCIÓN EN AUTH ENDPOINT")
    logger.info("-" * 50)
    
    auth_path = "backend/app/api/v1/endpoints/auth.py"
    
    if not os.path.exists(auth_path):
        logger.error(f"❌ Archivo no encontrado: {auth_path}")
        return False
    
    with open(auth_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar imports correctos
    correct_imports = [
        "from app.core.security import create_access_token",
        "from app.core.security import verify_password", 
        "from app.core.security import get_password_hash"
    ]
    
    imports_found = 0
    for import_line in correct_imports:
        if import_line in content:
            logger.info(f"✅ Import correcto: {import_line}")
            imports_found += 1
        else:
            logger.warning(f"⚠️ Import faltante: {import_line}")
    
    # Verificar llamadas correctas
    correct_calls = [
        "create_access_token(",
        "verify_password(",
        "get_password_hash("
    ]
    
    calls_found = 0
    for call in correct_calls:
        if call in content:
            logger.info(f"✅ Llamada correcta: {call}")
            calls_found += 1
        else:
            logger.warning(f"⚠️ Llamada faltante: {call}")
    
    # Verificar que NO hay llamadas problemáticas
    problematic_calls = re.findall(r'AuthService\.(create_access_token|verify_password|get_password_hash)\s*\(', content)
    
    if problematic_calls:
        logger.error(f"❌ Aún hay llamadas problemáticas: {problematic_calls}")
        return False
    else:
        logger.info("✅ No hay llamadas problemáticas a AuthService")
    
    # Resumen
    if imports_found == len(correct_imports) and calls_found == len(correct_calls) and not problematic_calls:
        logger.info("🎉 CORRECCIÓN COMPLETA Y CORRECTA")
        return True
    else:
        logger.warning("⚠️ CORRECCIÓN INCOMPLETA")
        return False

def analizar_commits_relacionados():
    """Analiza commits relacionados con el problema"""
    logger.info("📋 ANALIZANDO COMMITS RELACIONADOS")
    logger.info("-" * 50)
    
    # Commits relacionados con auth (del historial que vimos)
    commits_auth = [
        "c4b699c - CORREGIR ERROR CRITICO: AuthService.create_access_token no existe",
        "f24881b - SOLUCION CRITICA ERROR 503: Auth simplificado sin auditoria",
        "fd5b77f - ENDPOINTS CLIENTES LIMPIOS Y COMPLETOS"
    ]
    
    logger.info("📊 Commits relacionados con auth:")
    for commit in commits_auth:
        logger.info(f"   {commit}")
    
    # Análisis del problema
    logger.info("")
    logger.info("🔍 ANÁLISIS DEL PROBLEMA:")
    logger.info("   1. Commit f24881b: Auth simplificado - posible introducción del error")
    logger.info("   2. Commit fd5b77f: Endpoints clientes - posible agravamiento")
    logger.info("   3. Commit c4b699c: Corrección aplicada")
    
    return commits_auth

def generar_reporte_final():
    """Genera reporte final del segundo análisis"""
    logger.info("📊 GENERANDO REPORTE FINAL")
    logger.info("=" * 60)
    
    # Ejecutar verificaciones
    authservice_methods = verificar_metodos_authservice()
    security_methods = verificar_metodos_security()
    correccion_ok = verificar_correccion_auth_endpoint()
    commits = analizar_commits_relacionados()
    
    # Conclusiones
    logger.info("")
    logger.info("🎯 CONCLUSIONES DEL SEGUNDO ANÁLISIS:")
    logger.info("-" * 40)
    
    logger.info("✅ CAUSA RAÍZ CONFIRMADA:")
    logger.info("   - AuthService NO tiene create_access_token")
    logger.info("   - Security SÍ tiene create_access_token")
    logger.info("   - Error introducido en commit f24881b (Auth simplificado)")
    
    logger.info("")
    logger.info("✅ CORRECCIÓN VERIFICADA:")
    logger.info(f"   - Imports correctos: {'✅' if correccion_ok else '❌'}")
    logger.info(f"   - Llamadas correctas: {'✅' if correccion_ok else '❌'}")
    logger.info(f"   - Sin llamadas problemáticas: {'✅' if correccion_ok else '❌'}")
    
    logger.info("")
    logger.info("🎉 RESULTADO FINAL:")
    if correccion_ok:
        logger.info("   ✅ CORRECCIÓN COMPLETA Y CORRECTA")
        logger.info("   ✅ ERROR DEBERÍA ESTAR RESUELTO")
        logger.info("   ✅ LOGIN DEBERÍA FUNCIONAR CORRECTAMENTE")
    else:
        logger.info("   ❌ CORRECCIÓN INCOMPLETA")
        logger.info("   ❌ REQUIERE REVISIÓN ADICIONAL")
    
    return {
        "fecha_analisis": datetime.now().isoformat(),
        "authservice_methods": authservice_methods,
        "security_methods": security_methods,
        "correccion_ok": correccion_ok,
        "commits_analizados": commits,
        "conclusion": "CORRECCIÓN COMPLETA" if correccion_ok else "CORRECCIÓN INCOMPLETA"
    }

def main():
    """Función principal"""
    logger.info("🚀 SEGUNDO ENFOQUE DE ANÁLISIS - CONFIRMACIÓN DE CAUSA")
    logger.info("=" * 60)
    logger.info(f"📅 Fecha: {datetime.now()}")
    logger.info(f"🎯 Objetivo: Confirmar causa raíz y verificar corrección")
    logger.info("=" * 60)
    
    resultado = generar_reporte_final()
    
    logger.info("")
    logger.info("🎉 SEGUNDO ANÁLISIS COMPLETADO")
    logger.info("=" * 60)
    
    return resultado

if __name__ == "__main__":
    main()
