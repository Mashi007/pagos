#!/usr/bin/env python3
"""
Script maestro de validación alternativa para causa raíz
Ejecuta múltiples validaciones para identificar el problema 401
"""

import os
import sys
import subprocess
import time
from datetime import datetime

def run_validation_script(script_name: str, description: str):
    """Ejecutar un script de validación"""
    print(f"\n{'='*60}")
    print(f"🚀 EJECUTANDO: {description}")
    print(f"📁 Script: {script_name}")
    print(f"{'='*60}")
    
    try:
        # Ejecutar el script
        result = subprocess.run([
            sys.executable, 
            f"backend/scripts/{script_name}"
        ], 
        capture_output=True, 
        text=True, 
        timeout=60
        )
        
        print("📊 SALIDA:")
        print(result.stdout)
        
        if result.stderr:
            print("❌ ERRORES:")
            print(result.stderr)
        
        print(f"📊 Exit Code: {result.returncode}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("⏰ TIMEOUT: Script tardó más de 60 segundos")
        return False
    except Exception as e:
        print(f"❌ ERROR EJECUTANDO SCRIPT: {e}")
        return False

def main():
    """Función principal"""
    print("🔍 VALIDACIÓN ALTERNATIVA MAESTRA PARA CAUSA RAÍZ")
    print("🎯 Objetivo: Identificar causa de errores 401 Unauthorized")
    print(f"⏰ Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Lista de validaciones a ejecutar
    validations = [
        {
            "script": "validar_configuracion_entorno.py",
            "description": "Validación de Configuración de Entorno",
            "critical": True
        },
        {
            "script": "validar_configuracion_seguridad.py", 
            "description": "Validación de Configuración de Seguridad",
            "critical": True
        },
        {
            "script": "validar_comunicacion_frontend_backend.py",
            "description": "Validación de Comunicación Frontend-Backend",
            "critical": True
        },
        {
            "script": "validar_tokens_jwt.py",
            "description": "Validación de Tokens JWT",
            "critical": False
        }
    ]
    
    results = []
    
    # Ejecutar cada validación
    for validation in validations:
        success = run_validation_script(
            validation["script"], 
            validation["description"]
        )
        
        results.append({
            "name": validation["description"],
            "success": success,
            "critical": validation["critical"]
        })
        
        # Pausa entre validaciones
        print(f"\n⏸️ Pausa de 3 segundos antes de la siguiente validación...")
        time.sleep(3)
    
    # Resumen final
    print(f"\n{'='*60}")
    print("📊 RESUMEN FINAL DE VALIDACIONES")
    print(f"{'='*60}")
    
    critical_failures = 0
    total_critical = 0
    
    for result in results:
        status = "✅ ÉXITO" if result["success"] else "❌ FALLO"
        criticality = "🔴 CRÍTICO" if result["critical"] else "🟡 OPCIONAL"
        
        print(f"{status} {criticality} - {result['name']}")
        
        if result["critical"]:
            total_critical += 1
            if not result["success"]:
                critical_failures += 1
    
    print(f"\n🎯 DIAGNÓSTICO FINAL:")
    
    if critical_failures == 0:
        print("✅ TODAS LAS VALIDACIONES CRÍTICAS EXITOSAS")
        print("   El backend está funcionando correctamente")
        print("   El problema está en el frontend o en la comunicación")
    elif critical_failures == total_critical:
        print("❌ TODAS LAS VALIDACIONES CRÍTICAS FALLARON")
        print("   Problema crítico en el backend")
        print("   Revisar configuración de servidor, BD, o autenticación")
    else:
        print("⚠️ VALIDACIONES CRÍTICAS PARCIALMENTE FALLIDAS")
        print("   Problema específico identificado")
        print("   Revisar los resultados individuales para detalles")
    
    print(f"\n⏰ Finalizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return critical_failures == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
