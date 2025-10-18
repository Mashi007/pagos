#!/usr/bin/env python3
"""
Script para probar endpoints específicos que están fallando
"""

import requests
import json
import sys
from datetime import datetime

# Configuración
BASE_URL = "https://pagos-f2qf.onrender.com"
ENDPOINTS_TO_TEST = [
    {
        "name": "Concesionarios GET",
        "method": "GET",
        "url": f"{BASE_URL}/api/v1/concesionarios",
        "params": {"limit": 100}
    },
    {
        "name": "Concesionarios POST",
        "method": "POST", 
        "url": f"{BASE_URL}/api/v1/concesionarios",
        "data": {
            "nombre": "Test Concesionario",
            "direccion": "Test Direccion",
            "telefono": "123456789",
            "email": "test@test.com",
            "activo": True
        }
    },
    {
        "name": "Usuarios GET",
        "method": "GET",
        "url": f"{BASE_URL}/api/v1/users",
        "params": {"limit": 100}
    },
    {
        "name": "Usuarios POST",
        "method": "POST",
        "url": f"{BASE_URL}/api/v1/users",
        "data": {
            "email": "test@test.com",
            "nombre": "Test",
            "apellido": "User",
            "cargo": "Test Cargo",
            "rol": "USER",
            "password": "testpassword123",
            "is_active": True
        }
    },
    {
        "name": "Health Check",
        "method": "GET",
        "url": f"{BASE_URL}/health"
    }
]

def test_endpoint(endpoint):
    """Probar un endpoint específico"""
    print(f"\n{'='*60}")
    print(f"PROBANDO: {endpoint['name']}")
    print(f"Método: {endpoint['method']}")
    print(f"URL: {endpoint['url']}")
    print(f"{'='*60}")
    
    try:
        # Preparar parámetros
        kwargs = {}
        if 'params' in endpoint:
            kwargs['params'] = endpoint['params']
        if 'data' in endpoint:
            kwargs['json'] = endpoint['data']
            kwargs['headers'] = {'Content-Type': 'application/json'}
        
        # Realizar petición
        response = requests.request(
            method=endpoint['method'],
            url=endpoint['url'],
            timeout=30,
            **kwargs
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code < 400:
            print("RESPUESTA EXITOSA")
            try:
                data = response.json()
                print(f"Data: {json.dumps(data, indent=2, ensure_ascii=False)}")
            except:
                print(f"Text: {response.text}")
        else:
            print("ERROR EN RESPUESTA")
            print(f"Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"ERROR DE CONEXION: {e}")
    except Exception as e:
        print(f"ERROR GENERAL: {e}")

def main():
    """Función principal"""
    print("PROBANDO ENDPOINTS ESPECIFICOS")
    print(f"Base URL: {BASE_URL}")
    print(f"Timestamp: {datetime.now()}")
    
    for endpoint in ENDPOINTS_TO_TEST:
        test_endpoint(endpoint)
    
    print(f"\n{'='*60}")
    print("PRUEBAS COMPLETADAS")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
