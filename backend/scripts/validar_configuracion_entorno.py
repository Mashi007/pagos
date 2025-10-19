#!/usr/bin/env python3
"""
Script de validación de configuración de entorno
Verifica variables de entorno y configuración del backend
"""

import os
import sys
import requests
import json
from datetime import datetime, timedelta
import jwt
from typing import Dict, Any

# Configuración
BASE_URL = "https://pagos-f2qf.onrender.com"

def test_environment_endpoints():
    """Probar endpoints que revelan información del entorno"""
    print("🌍 PROBANDO ENDPOINTS DE INFORMACIÓN DEL ENTORNO...")
    
    info_endpoints = [
        "/",
        "/docs",
        "/openapi.json",
        "/health",  # Si existe
        "/status",  # Si existe
        "/api/v1/health",  # Si existe
    ]
    
    for endpoint in info_endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            print(f"  {endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"    📝 Datos: {json.dumps(data, indent=2)[:200]}...")
                except:
                    print(f"    📝 HTML/Texto: {response.text[:100]}...")
                    
        except Exception as e:
            print(f"  {endpoint}: ERROR - {e}")

def test_database_endpoints():
    """Probar endpoints que requieren base de datos"""
    print("\n🗄️ PROBANDO ENDPOINTS DE BASE DE DATOS...")
    
    db_endpoints = [
        "/api/v1/analistas/activos",
        "/api/v1/concesionarios/activos",
        "/api/v1/modelos-vehiculos/activos",
        "/api/v1/configuracion/general"
    ]
    
    for endpoint in db_endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            print(f"  {endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"    ✅ Datos recibidos: {len(data)} registros")
                except:
                    print(f"    ✅ Respuesta válida")
            elif response.status_code == 500:
                print(f"    ❌ Error interno - posible problema de BD")
                print(f"    📝 Error: {response.text[:200]}...")
            elif response.status_code == 401:
                print(f"    ⚠️ Requiere autenticación")
            else:
                print(f"    ⚠️ Status inesperado: {response.text[:100]}...")
                
        except Exception as e:
            print(f"  {endpoint}: ERROR - {e}")

def test_auth_configuration():
    """Probar configuración de autenticación"""
    print("\n🔐 PROBANDO CONFIGURACIÓN DE AUTENTICACIÓN...")
    
    # Probar diferentes métodos de autenticación
    auth_tests = [
        {
            "name": "Login con credenciales válidas",
            "method": "POST",
            "endpoint": "/api/v1/auth/login",
            "data": {"email": "itmaster@rapicreditca.com", "password": "admin123"},
            "expected_status": [200, 401, 422]
        },
        {
            "name": "Login con credenciales inválidas",
            "method": "POST", 
            "endpoint": "/api/v1/auth/login",
            "data": {"email": "invalid@test.com", "password": "wrong"},
            "expected_status": [401, 422]
        },
        {
            "name": "Login sin datos",
            "method": "POST",
            "endpoint": "/api/v1/auth/login", 
            "data": {},
            "expected_status": [422, 400]
        },
        {
            "name": "Refresh token",
            "method": "POST",
            "endpoint": "/api/v1/auth/refresh",
            "data": {"refresh_token": "invalid_token"},
            "expected_status": [401, 422]
        }
    ]
    
    for test in auth_tests:
        try:
            print(f"\n  🔍 {test['name']}")
            
            if test['method'] == 'POST':
                response = requests.post(
                    f"{BASE_URL}{test['endpoint']}",
                    json=test['data'],
                    timeout=10
                )
            else:
                response = requests.get(
                    f"{BASE_URL}{test['endpoint']}",
                    timeout=10
                )
            
            print(f"    📊 Status: {response.status_code}")
            
            if response.status_code in test['expected_status']:
                print(f"    ✅ Status esperado")
            else:
                print(f"    ❌ Status inesperado")
            
            print(f"    📝 Respuesta: {response.text[:150]}...")
            
        except Exception as e:
            print(f"    ❌ Error: {e}")

def test_cors_configuration():
    """Probar configuración CORS detallada"""
    print("\n🌐 PROBANDO CONFIGURACIÓN CORS DETALLADA...")
    
    # Diferentes orígenes para probar
    origins_to_test = [
        "https://rapicredit.onrender.com",
        "http://localhost:3000",
        "http://localhost:5173",
        "https://example.com"
    ]
    
    for origin in origins_to_test:
        print(f"\n  🔍 Probando origen: {origin}")
        
        cors_headers = {
            'Origin': origin,
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'Authorization, Content-Type'
        }
        
        try:
            response = requests.options(
                f"{BASE_URL}/api/v1/auth/me",
                headers=cors_headers,
                timeout=10
            )
            
            print(f"    📊 OPTIONS Status: {response.status_code}")
            
            allow_origin = response.headers.get('Access-Control-Allow-Origin')
            if allow_origin == origin or allow_origin == '*':
                print(f"    ✅ Origen permitido: {allow_origin}")
            else:
                print(f"    ❌ Origen no permitido: {allow_origin}")
                
        except Exception as e:
            print(f"    ❌ Error: {e}")

def test_rate_limiting():
    """Probar límites de velocidad"""
    print("\n⚡ PROBANDO LÍMITES DE VELOCIDAD...")
    
    try:
        # Hacer múltiples requests rápidos
        for i in range(5):
            response = requests.get(f"{BASE_URL}/api/v1/analistas/activos", timeout=5)
            print(f"  Request {i+1}: {response.status_code}")
            
            if response.status_code == 429:
                print(f"    ⚠️ Rate limit alcanzado")
                break
                
    except Exception as e:
        print(f"❌ Error en rate limiting test: {e}")

def main():
    """Función principal"""
    print("🔍 VALIDACIÓN ALTERNATIVA DE CONFIGURACIÓN DE ENTORNO")
    print("=" * 60)
    
    # 1. Probar endpoints de información
    test_environment_endpoints()
    
    # 2. Probar endpoints de BD
    test_database_endpoints()
    
    # 3. Probar configuración de auth
    test_auth_configuration()
    
    # 4. Probar configuración CORS
    test_cors_configuration()
    
    # 5. Probar rate limiting
    test_rate_limiting()
    
    print("\n🎯 VALIDACIÓN DE ENTORNO COMPLETADA")
    print("Revisa los resultados para identificar problemas de configuración")

if __name__ == "__main__":
    main()
