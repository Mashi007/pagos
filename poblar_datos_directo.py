#!/usr/bin/env python3
"""
Script para poblar datos directamente en la base de datos
"""
import requests
import json

# Configuración
BASE_URL = "https://pagos-f2qf.onrender.com"
API_BASE = f"{BASE_URL}/api/v1"

def poblar_datos():
    """Poblar datos usando endpoints del backend"""
    
    print("POBLANDO DATOS EN LA BASE DE DATOS")
    print("=" * 50)
    
    # 1. Crear usuario de prueba primero
    print("\n1. Creando usuario de prueba...")
    try:
        response = requests.post(f"{API_BASE}/auth/create-test-user", timeout=30)
        if response.status_code == 200:
            print("Usuario de prueba creado exitosamente")
            data = response.json()
            print(f"Credenciales: {data.get('credentials', {})}")
        else:
            print(f"Error creando usuario: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")
    
    # 2. Intentar login
    print("\n2. Intentando login...")
    login_data = {
        "email": "admin@rapicredit.com",
        "password": "admin123",
        "remember": True
    }
    
    try:
        login_response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
        if login_response.status_code == 200:
            print("Login exitoso")
            token_data = login_response.json()
            access_token = token_data.get("access_token")
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # 3. Probar endpoints después del login
            print("\n3. Probando endpoints después del login...")
            
            endpoints = [
                f"{API_BASE}/concesionarios/activos",
                f"{API_BASE}/asesores/activos",
                f"{API_BASE}/validadores/configuracion"
            ]
            
            for endpoint in endpoints:
                try:
                    print(f"\nProbando: {endpoint}")
                    response = requests.get(endpoint, headers=headers, timeout=10)
                    print(f"Status: {response.status_code}")
                    
                    if response.status_code == 200:
                        print("EXITO")
                        data = response.json()
                        print(f"Datos recibidos: {len(data) if isinstance(data, list) else 'objeto'}")
                    else:
                        print("ERROR")
                        print(f"Error: {response.text[:200]}...")
                        
                except Exception as e:
                    print(f"Error probando endpoint: {e}")
                    
        else:
            print(f"Login falló: {login_response.status_code}")
            print(login_response.text)
            
    except Exception as e:
        print(f"Error en login: {e}")

if __name__ == "__main__":
    poblar_datos()
