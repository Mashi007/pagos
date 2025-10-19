#!/usr/bin/env python3
"""
Script para verificar la estructura real de la tabla clientes en la base de datos
"""
import requests
import json
import sys
import os

# Agregar el directorio del proyecto al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "https://pagos-f2qf.onrender.com"

def verificar_estructura_clientes():
    """Verificar la estructura real de la tabla clientes"""
    print("Verificando estructura de tabla clientes...")
    
    try:
        # Login como admin
        login_data = {
            "email": "itmaster@rapicreditca.com",
            "password": "R@pi_2025**"
        }
        
        login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Probar endpoint simple que solo usa campos básicos
            print("\n1. Probando endpoint simple...")
            simple_response = requests.get(f"{BASE_URL}/api/v1/clientes/simple", headers=headers)
            print(f"   Simple endpoint: {simple_response.status_code}")
            if simple_response.status_code == 200:
                data = simple_response.json()
                print(f"   Total clientes: {data.get('total', 0)}")
                if data.get('items'):
                    print(f"   Primer cliente: {data['items'][0]}")
            else:
                print(f"   Error: {simple_response.text}")
            
            # Probar endpoint normal
            print("\n2. Probando endpoint normal...")
            normal_response = requests.get(f"{BASE_URL}/api/v1/clientes/", headers=headers)
            print(f"   Normal endpoint: {normal_response.status_code}")
            if normal_response.status_code == 200:
                data = normal_response.json()
                print(f"   Total clientes: {data.get('total', 0)}")
                if data.get('items'):
                    print(f"   Primer cliente: {data['items'][0]}")
            else:
                print(f"   Error: {normal_response.text}")
                
            # Probar endpoint de test
            print("\n3. Probando endpoint de test...")
            test_response = requests.get(f"{BASE_URL}/api/v1/clientes/test-auth", headers=headers)
            print(f"   Test endpoint: {test_response.status_code}")
            if test_response.status_code == 200:
                data = test_response.json()
                print(f"   Respuesta: {data}")
            else:
                print(f"   Error: {test_response.text}")
                
        else:
            print(f"Error en login: {login_response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verificar_estructura_clientes()