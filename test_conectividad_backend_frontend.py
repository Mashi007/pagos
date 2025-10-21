#!/usr/bin/env python3
"""
Test de conectividad Backend-Frontend
Verifica la comunicación entre ambos servicios
"""

import requests
import json
import time
from datetime import datetime

def test_backend_connectivity():
    """Test de conectividad con el backend"""
    
    backend_url = "https://pagos-f2qf.onrender.com"
    frontend_url = "https://rapicredit.onrender.com"
    
    print("TEST DE CONECTIVIDAD BACKEND-FRONTEND")
    print("=" * 50)
    
    # Test 1: Backend Health Check
    print("\n1. TEST: Backend Health Check")
    try:
        response = requests.get(f"{backend_url}/", timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        print("   OK: Backend accesible")
    except Exception as e:
        print(f"   ERROR: Backend no accesible: {e}")
        return False
    
    # Test 2: Backend API Health
    print("\n2. TEST: Backend API Health")
    try:
        response = requests.get(f"{backend_url}/api/v1/health", timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        print("   OK: API Backend funcionando")
    except Exception as e:
        print(f"   ERROR: API Backend no accesible: {e}")
        return False
    
    # Test 3: CORS Headers
    print("\n3. TEST: CORS Headers")
    try:
        headers = {
            "Origin": frontend_url,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization"
        }
        response = requests.options(f"{backend_url}/api/v1/auth/login", headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   CORS Headers: {dict(response.headers)}")
        
        cors_headers = [h for h in response.headers.keys() if 'access-control' in h.lower()]
        if cors_headers:
            print("   OK: CORS configurado")
        else:
            print("   WARNING: CORS headers no encontrados")
    except Exception as e:
        print(f"   ERROR: Error CORS: {e}")
    
    # Test 4: Frontend Accesibilidad
    print("\n4. TEST: Frontend Accesibilidad")
    try:
        response = requests.get(frontend_url, timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type')}")
        print("   OK: Frontend accesible")
    except Exception as e:
        print(f"   ERROR: Frontend no accesible: {e}")
        return False
    
    # Test 5: API Endpoints Críticos
    print("\n5. TEST: API Endpoints Críticos")
    endpoints = [
        "/api/v1/auth/login",
        "/api/v1/clientes",
        "/api/v1/validadores",
        "/api/v1/concesionarios/activos",
        "/api/v1/analistas/activos",
        "/api/v1/modelos-vehiculos/activos"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{backend_url}{endpoint}", timeout=10)
            print(f"   {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"   {endpoint}: ERROR - {e}")
    
    print("\nOK: TEST DE CONECTIVIDAD COMPLETADO")
    return True

def test_api_response_structure():
    """Test de estructura de respuestas de API"""
    
    backend_url = "https://pagos-f2qf.onrender.com"
    
    print("\n🔍 TEST: Estructura de Respuestas API")
    print("=" * 50)
    
    # Test de error 503 (duplicado)
    print("\n1️⃣ TEST: Error 503 Structure")
    try:
        # Datos de cliente con cédula duplicada
        data = {
            "cedula": "V31566283",  # Cédula que sabemos que existe
            "nombres": "TEST",
            "apellidos": "TEST",
            "telefono": "+581111111111",
            "email": "test@test.com",
            "direccion": "test",
            "fecha_nacimiento": "2025-10-01",
            "ocupacion": "TEST",
            "modelo_vehiculo": "ASIAWING NC250",
            "concesionario": "BARRETOMOTORCYCLE, C.A.",
            "analista": "BELIANA YSABEL GONZÁLEZ CARVAJAL",
            "estado": "ACTIVO",
            "notas": ""
        }
        
        response = requests.post(f"{backend_url}/api/v1/clientes", json=data, timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        
        if response.status_code == 503:
            try:
                error_data = response.json()
                print(f"   Error JSON: {json.dumps(error_data, indent=2)}")
                print(f"   Error Keys: {list(error_data.keys())}")
                
                if 'detail' in error_data:
                    print(f"   Detail field: '{error_data['detail']}'")
                    print(f"   Contains 'duplicate key': {'duplicate key' in error_data['detail']}")
                    print(f"   Contains 'already exists': {'already exists' in error_data['detail']}")
                else:
                    print("   ❌ No 'detail' field found")
                    
                if 'message' in error_data:
                    print(f"   Message field: '{error_data['message']}'")
                else:
                    print("   ℹ️ No 'message' field found")
                    
            except json.JSONDecodeError:
                print("   ❌ Response is not valid JSON")
                print(f"   Raw response: {response.text}")
        else:
            print(f"   ⚠️ Expected 503, got {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error testing 503: {e}")

if __name__ == "__main__":
    print(f"Test iniciado: {datetime.now().isoformat()}")
    
    # Test de conectividad básica
    if test_backend_connectivity():
        # Test de estructura de respuestas
        test_api_response_structure()
    
    print(f"\nTest completado: {datetime.now().isoformat()}")
