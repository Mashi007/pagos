#!/usr/bin/env python3
"""
PRUEBAS SIMPLES DEL SISTEMA RAPICREDIT
Verificacion basica de respuestas del sistema
"""
import requests
import json
import sys
from datetime import datetime

def test_endpoint(url, name, expected_status=200):
    """Probar un endpoint simple"""
    try:
        print(f"Probando {name}...")
        response = requests.get(url, timeout=10)
        
        if response.status_code == expected_status:
            print(f"  OK: {name} - Status {response.status_code}")
            return True
        else:
            print(f"  FAIL: {name} - Status {response.status_code}")
            return False
    except Exception as e:
        print(f"  ERROR: {name} - {str(e)}")
        return False

def test_auth():
    """Probar autenticacion"""
    try:
        print("Probando autenticacion...")
        
        # Datos de login
        login_data = {
            "email": "admin@rapicredit.com",
            "password": "admin123",
            "remember": True
        }
        
        response = requests.post(
            "https://pagos-f2qf.onrender.com/api/v1/auth/login",
            json=login_data,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'access_token' in data['data']:
                print("  OK: Autenticacion exitosa - Token recibido")
                return data['data']['access_token']
            else:
                print("  FAIL: Token no encontrado en respuesta")
                return None
        else:
            print(f"  FAIL: Status {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"  ERROR: {str(e)}")
        return None

def test_protected_endpoint(token):
    """Probar endpoint protegido"""
    try:
        print("Probando endpoint protegido...")
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }
        
        response = requests.get(
            "https://pagos-f2qf.onrender.com/api/v1/clientes?page=1&per_page=5",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            print("  OK: Endpoint protegido accesible")
            return True
        elif response.status_code == 403:
            print("  FAIL: 403 Forbidden - Token invalido")
            return False
        else:
            print(f"  FAIL: Status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ERROR: {str(e)}")
        return False

def main():
    """Funcion principal"""
    print("PRUEBAS SIMPLES DEL SISTEMA RAPICREDIT")
    print("=" * 50)
    
    # Contadores
    total = 0
    passed = 0
    
    # Test 1: Health endpoint
    total += 1
    if test_endpoint("https://pagos-f2qf.onrender.com/api/v1/health", "Health Check"):
        passed += 1
    
    # Test 2: Frontend
    total += 1
    if test_endpoint("https://rapicredit.onrender.com", "Frontend"):
        passed += 1
    
    # Test 3: Auth endpoint (esperamos 401 sin credenciales)
    total += 1
    if test_endpoint("https://pagos-f2qf.onrender.com/api/v1/clientes", "Clientes (sin auth)", 401):
        passed += 1
    
    # Test 4: Autenticacion completa
    total += 1
    token = test_auth()
    if token:
        passed += 1
        
        # Test 5: Endpoint protegido
        total += 1
        if test_protected_endpoint(token):
            passed += 1
    else:
        # Contar como fallo si no hay token
        total += 1
    
    # Resumen
    print("\n" + "=" * 50)
    print("RESUMEN:")
    print(f"Pruebas Exitosas: {passed}")
    print(f"Pruebas Fallidas: {total - passed}")
    print(f"Tasa de Exito: {(passed/total*100):.1f}%")
    
    if passed/total >= 0.8:
        print("Estado: HEALTHY")
        sys.exit(0)
    else:
        print("Estado: DEGRADED")
        sys.exit(1)

if __name__ == "__main__":
    main()
