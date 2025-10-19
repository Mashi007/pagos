#!/usr/bin/env python3
"""
Script para probar el endpoint de clientes
"""
import requests
import json
import sys
import os

# Agregar el directorio del proyecto al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "https://pagos-f2qf.onrender.com"

def probar_endpoint_clientes():
    """Probar el endpoint de clientes"""
    print("Probando endpoint de clientes...")
    
    try:
        # Probar endpoint simple
        response = requests.get(f"{BASE_URL}/api/v1/clientes/ping")
        print(f"Ping clientes: {response.status_code}")
        if response.status_code == 200:
            print(f"   Respuesta: {response.json()}")
        
        # Probar endpoint con autenticación
        print("\nProbando endpoint con autenticacion...")
        
        # Login como admin
        login_data = {
            "email": "itmaster@rapicreditca.com",
            "password": "R@pi_2025**"
        }
        
        login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Probar endpoint simple de clientes
            clientes_response = requests.get(f"{BASE_URL}/api/v1/clientes/simple", headers=headers)
            print(f"Clientes simple con auth: {clientes_response.status_code}")
            
            if clientes_response.status_code == 200:
                data = clientes_response.json()
                print(f"   Total clientes: {data.get('total', 0)}")
                print(f"   Items: {len(data.get('items', []))}")
                if data.get('items'):
                    print(f"   Primer cliente: {data['items'][0]}")
            else:
                print(f"   Error: {clientes_response.text}")
                
            # Probar endpoint normal de clientes
            clientes_response2 = requests.get(f"{BASE_URL}/api/v1/clientes/", headers=headers)
            print(f"Clientes normal con auth: {clientes_response2.status_code}")
            
            if clientes_response2.status_code == 200:
                data2 = clientes_response2.json()
                print(f"   Total clientes: {data2.get('total', 0)}")
                print(f"   Items: {len(data2.get('items', []))}")
                if data2.get('items'):
                    print(f"   Primer cliente: {data2['items'][0]}")
            else:
                print(f"   Error: {clientes_response2.text}")
        else:
            print(f"Error en login: {login_response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    probar_endpoint_clientes()
