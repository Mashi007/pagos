#!/usr/bin/env python3
"""
Script simple para probar la conectividad del servidor
"""

import requests
import time

def probar_conectividad():
    """Probar conectividad básica del servidor"""
    base_url = "https://pagos-f2qf.onrender.com"
    
    print("🔍 PROBANDO CONECTIVIDAD DEL SERVIDOR")
    print("=" * 50)
    
    # Probar endpoint básico
    try:
        print("📡 Probando endpoint básico...")
        response = requests.get(f"{base_url}/", timeout=10)
        print(f"   📊 Status Code: {response.status_code}")
        if response.status_code in [200, 405]:  # 405 es normal para GET en root
            print("   ✅ Servidor respondiendo")
        else:
            print(f"   ⚠️ Respuesta inesperada: {response.text[:100]}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Probar endpoint de documentación
    try:
        print("\n📡 Probando endpoint de documentación...")
        response = requests.get(f"{base_url}/docs", timeout=10)
        print(f"   📊 Status Code: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Documentación disponible")
        else:
            print(f"   ⚠️ Documentación no disponible: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Probar endpoint de login
    try:
        print("\n📡 Probando endpoint de login...")
        response = requests.post(
            f"{base_url}/api/v1/auth/login",
            json={"email": "test", "password": "test"},
            timeout=10
        )
        print(f"   📊 Status Code: {response.status_code}")
        if response.status_code == 503:
            print("   ❌ Servicio de base de datos no disponible")
        elif response.status_code == 422:
            print("   ✅ Endpoint funcionando (error de validación esperado)")
        else:
            print(f"   ⚠️ Respuesta inesperada: {response.text[:100]}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n📊 RESUMEN:")
    print("=" * 50)
    print("🎯 El servidor está funcionando pero la base de datos puede estar")
    print("   temporalmente no disponible. Esto es normal durante despliegues.")
    print("💡 Espera unos minutos y vuelve a probar.")

if __name__ == "__main__":
    probar_conectividad()
