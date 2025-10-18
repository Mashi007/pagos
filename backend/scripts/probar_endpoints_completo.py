#!/usr/bin/env python3
"""
Script para probar endpoints específicos con autenticación
"""

import requests
import json
import sys
from datetime import datetime

# Configuración
BASE_URL = "https://pagos-f2qf.onrender.com"

def test_endpoint_without_auth():
    """Probar endpoints que no requieren autenticación"""
    print(f"\n{'='*60}")
    print("PROBANDO ENDPOINTS SIN AUTENTICACION")
    print(f"{'='*60}")
    
    endpoints = [
        {
            "name": "Concesionarios Test Simple",
            "method": "GET",
            "url": f"{BASE_URL}/api/v1/concesionarios/test-simple"
        },
        {
            "name": "Concesionarios Test No Auth",
            "method": "GET", 
            "url": f"{BASE_URL}/api/v1/concesionarios/test-no-auth"
        },
        {
            "name": "Usuarios Test Simple",
            "method": "GET",
            "url": f"{BASE_URL}/api/v1/users/test-simple"
        },
        {
            "name": "Health Check",
            "method": "GET",
            "url": f"{BASE_URL}/api/v1/health"
        }
    ]
    
    for endpoint in endpoints:
        print(f"\n{'-'*40}")
        print(f"PROBANDO: {endpoint['name']}")
        print(f"URL: {endpoint['url']}")
        print(f"{'-'*40}")
        
        try:
            response = requests.get(endpoint['url'], timeout=30)
            print(f"Status Code: {response.status_code}")
            
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

def test_login():
    """Probar login para obtener token"""
    print(f"\n{'='*60}")
    print("PROBANDO LOGIN")
    print(f"{'='*60}")
    
    login_data = {
        "email": "itmaster@rapicreditca.com",
        "password": "R@pi_2025**"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=login_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("LOGIN EXITOSO")
            print(f"Token: {data.get('access_token', 'No token')[:50]}...")
            return data.get('access_token')
        else:
            print("ERROR EN LOGIN")
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"ERROR EN LOGIN: {e}")
        return None

def test_endpoint_with_auth(token):
    """Probar endpoints con autenticación"""
    if not token:
        print("No hay token disponible para probar endpoints con auth")
        return
        
    print(f"\n{'='*60}")
    print("PROBANDO ENDPOINTS CON AUTENTICACION")
    print(f"{'='*60}")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    endpoints = [
        {
            "name": "Concesionarios GET",
            "method": "GET",
            "url": f"{BASE_URL}/api/v1/concesionarios",
            "params": {"limit": 100}
        },
        {
            "name": "Usuarios GET",
            "method": "GET",
            "url": f"{BASE_URL}/api/v1/users",
            "params": {"limit": 100}
        }
    ]
    
    for endpoint in endpoints:
        print(f"\n{'-'*40}")
        print(f"PROBANDO: {endpoint['name']}")
        print(f"URL: {endpoint['url']}")
        print(f"{'-'*40}")
        
        try:
            kwargs = {'headers': headers}
            if 'params' in endpoint:
                kwargs['params'] = endpoint['params']
                
            response = requests.get(endpoint['url'], timeout=30, **kwargs)
            print(f"Status Code: {response.status_code}")
            
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
    print("PROBANDO ENDPOINTS CON Y SIN AUTENTICACION")
    print(f"Base URL: {BASE_URL}")
    print(f"Timestamp: {datetime.now()}")
    
    # Probar endpoints sin autenticación
    test_endpoint_without_auth()
    
    # Probar login
    token = test_login()
    
    # Probar endpoints con autenticación
    test_endpoint_with_auth(token)
    
    print(f"\n{'='*60}")
    print("PRUEBAS COMPLETADAS")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
