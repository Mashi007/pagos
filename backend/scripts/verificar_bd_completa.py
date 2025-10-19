#!/usr/bin/env python3
"""
Script para verificar base de datos completa
"""
import requests
import json
import sys
import os

# Agregar el directorio del proyecto al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "https://pagos-f2qf.onrender.com"

def verificar_base_datos():
    """Verificar estructura completa de base de datos"""
    print("Verificando base de datos completa...")
    
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
            
            # 1. Verificar endpoint de clientes
            print("\n1. Verificando endpoint de clientes...")
            clientes_response = requests.get(f"{BASE_URL}/api/v1/clientes/", headers=headers)
            print(f"   Status: {clientes_response.status_code}")
            if clientes_response.status_code == 200:
                data = clientes_response.json()
                print(f"   Total clientes: {data.get('total', 0)}")
                print(f"   Items: {len(data.get('items', []))}")
            else:
                print(f"   Error: {clientes_response.text}")
            
            # 2. Verificar modelos de vehículos
            print("\n2. Verificando modelos de vehículos...")
            modelos_response = requests.get(f"{BASE_URL}/api/v1/modelos-vehiculos/", headers=headers)
            print(f"   Status: {modelos_response.status_code}")
            if modelos_response.status_code == 200:
                data = modelos_response.json()
                print(f"   Total modelos: {data.get('total', 0)}")
                if data.get('items'):
                    print(f"   Primer modelo: {data['items'][0]}")
            else:
                print(f"   Error: {modelos_response.text}")
            
            # 3. Verificar analistas
            print("\n3. Verificando analistas...")
            analistas_response = requests.get(f"{BASE_URL}/api/v1/analistas/", headers=headers)
            print(f"   Status: {analistas_response.status_code}")
            if analistas_response.status_code == 200:
                data = analistas_response.json()
                print(f"   Total analistas: {data.get('total', 0)}")
                if data.get('items'):
                    print(f"   Primer analista: {data['items'][0]}")
            else:
                print(f"   Error: {analistas_response.text}")
            
            # 4. Verificar concesionarios
            print("\n4. Verificando concesionarios...")
            concesionarios_response = requests.get(f"{BASE_URL}/api/v1/concesionarios/", headers=headers)
            print(f"   Status: {concesionarios_response.status_code}")
            if concesionarios_response.status_code == 200:
                data = concesionarios_response.json()
                print(f"   Total concesionarios: {data.get('total', 0)}")
                if data.get('items'):
                    print(f"   Primer concesionario: {data['items'][0]}")
            else:
                print(f"   Error: {concesionarios_response.text}")
            
            # 5. Verificar validadores
            print("\n5. Verificando validadores...")
            validadores_response = requests.get(f"{BASE_URL}/api/v1/validadores/", headers=headers)
            print(f"   Status: {validadores_response.status_code}")
            if validadores_response.status_code == 200:
                data = validadores_response.json()
                print(f"   Total validadores: {data.get('total', 0)}")
                if data.get('items'):
                    print(f"   Primer validador: {data['items'][0]}")
            else:
                print(f"   Error: {validadores_response.text}")
                
        else:
            print(f"Error en login: {login_response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verificar_base_datos()
