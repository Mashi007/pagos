#!/usr/bin/env python3
"""
Script para ejecutar la migración de roles desde el cliente.
"""

import requests
import json
import sys

BASE_URL = "https://pagos-f2qf.onrender.com/api/v1"

def check_status():
    """Verificar el estado actual de los roles."""
    print("🔍 Verificando estado actual...")
    try:
        response = requests.get(f"{BASE_URL}/emergency/check-roles", timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n📊 Estado actual:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return data.get("necesita_migracion", False)
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error conectando: {e}")
        print("ℹ️  Esto es normal si la app está crasheando por el error de enum")
        return None


def execute_migration():
    """Ejecutar la migración."""
    print("\n🚀 Ejecutando migración...")
    try:
        response = requests.post(f"{BASE_URL}/emergency/migrate-roles", timeout=60)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ MIGRACIÓN EXITOSA!")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error ejecutando migración: {e}")
        return False


def verify_result():
    """Verificar el resultado después de la migración."""
    print("\n🔍 Verificando resultado...")
    try:
        response = requests.get(f"{BASE_URL}/emergency/check-roles", timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n📊 Estado final:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            if not data.get("necesita_migracion", True):
                print("\n✅ SISTEMA CORRECTO!")
                return True
            else:
                print("\n⚠️  Aún necesita migración")
                return False
        else:
            print(f"❌ Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error verificando: {e}")
        return False


def test_login():
    """Probar el login después de la migración."""
    print("\n🔑 Probando login...")
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={
                "email": "itmaster@rapicreditca.com",
                "password": "admin123"
            },
            timeout=30
        )
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Login exitoso!")
            return True
        else:
            print(f"⚠️  Login falló: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error probando login: {e}")
        return False


def main():
    print("="*60)
    print("🔧 MIGRACIÓN DE ROLES - Sistema de Préstamos")
    print("="*60)
    
    # Paso 1: Intentar verificar estado (puede fallar si la app está crasheando)
    needs_migration = check_status()
    
    # Paso 2: Ejecutar migración de todos modos
    print("\n" + "="*60)
    print("📋 PASO 1: EJECUTAR MIGRACIÓN")
    print("="*60)
    
    if execute_migration():
        print("\n✅ Migración ejecutada correctamente")
        
        # Paso 3: Esperar un momento para que la DB se estabilice
        print("\n⏳ Esperando 5 segundos para que la DB se estabilice...")
        import time
        time.sleep(5)
        
        # Paso 4: Verificar resultado
        print("\n" + "="*60)
        print("📋 PASO 2: VERIFICAR RESULTADO")
        print("="*60)
        
        if verify_result():
            # Paso 5: Probar login
            print("\n" + "="*60)
            print("📋 PASO 3: PROBAR LOGIN")
            print("="*60)
            
            test_login()
            
            print("\n" + "="*60)
            print("✅ PROCESO COMPLETADO")
            print("="*60)
            print("\n📝 Siguiente paso:")
            print("   1. Verificar que la app funciona en el navegador")
            print("   2. Eliminar archivos temporales:")
            print("      - backend/app/api/v1/endpoints/emergency_migrate_roles.py")
            print("      - backend/scripts/run_migration_production.py")
            print("      - execute_migration.py (este archivo)")
            print("   3. Actualizar main.py para remover el endpoint")
            print("   4. Commit y push")
            return 0
        else:
            print("\n⚠️  Verificación falló, revisa los logs")
            return 1
    else:
        print("\n❌ Migración falló")
        print("\n🔍 Posibles causas:")
        print("   1. La app aún está iniciando (espera 1-2 minutos)")
        print("   2. Error de conexión a DB")
        print("   3. Permisos insuficientes en PostgreSQL")
        print("\n💡 Intenta ejecutar este script nuevamente en 1 minuto")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Proceso interrumpido por el usuario")
        sys.exit(1)

