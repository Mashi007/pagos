#!/usr/bin/env python3
"""
Script para probar creación de cliente desde cero
"""
import requests
import json
import sys
import os

# Agregar el directorio del proyecto al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "https://pagos-f2qf.onrender.com"

def probar_creacion_cliente():
    """Probar creación de cliente desde cero"""
    print("Probando creación de cliente desde cero...")
    
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
            
            # 1. Probar opciones de configuración
            print("\n1. Probando opciones de configuración...")
            opciones_response = requests.get(f"{BASE_URL}/api/v1/clientes/opciones-configuracion", headers=headers)
            print(f"   Status: {opciones_response.status_code}")
            if opciones_response.status_code == 200:
                data = opciones_response.json()
                print(f"   Modelos de vehículos: {len(data.get('modelos_vehiculos', []))}")
                print(f"   Analistas: {len(data.get('analistas', []))}")
                print(f"   Concesionarios: {len(data.get('concesionarios', []))}")
            else:
                print(f"   Error: {opciones_response.text}")
            
            # 2. Probar crear cliente con datos válidos
            print("\n2. Probando creación de cliente...")
            cliente_data = {
                "cedula": "V12345678",
                "nombres": "Juan Carlos",
                "apellidos": "Pérez González",
                "telefono": "4241234567",
                "email": "juan.perez@ejemplo.com",
                "direccion": "Av. Principal, Caracas",
                "fecha_nacimiento": "1990-01-15",
                "ocupacion": "Ingeniero",
                "modelo_vehiculo": "Toyota Corolla",
                "concesionario": "AutoCenter Caracas"
            }
            
            crear_response = requests.post(f"{BASE_URL}/api/v1/clientes/crear", json=cliente_data, headers=headers)
            print(f"   Status: {crear_response.status_code}")
            if crear_response.status_code == 200:
                data = crear_response.json()
                print(f"   Cliente creado - ID: {data.get('id')}")
                print(f"   Cédula: {data.get('cedula')}")
                print(f"   Nombre: {data.get('nombres')} {data.get('apellidos')}")
            else:
                print(f"   Error: {crear_response.text}")
            
            # 3. Probar crear cliente con datos inválidos (nombre corto)
            print("\n3. Probando validación de nombre...")
            cliente_invalido = {
                "cedula": "V87654321",
                "nombres": "Juan",
                "apellidos": "Pérez",
                "telefono": "4247654321",
                "email": "juan.invalido@ejemplo.com"
            }
            
            crear_invalido_response = requests.post(f"{BASE_URL}/api/v1/clientes/crear", json=cliente_invalido, headers=headers)
            print(f"   Status: {crear_invalido_response.status_code}")
            if crear_invalido_response.status_code == 400:
                print(f"   Validación funcionando: {crear_invalido_response.json().get('detail', 'N/A')}")
            else:
                print(f"   Error inesperado: {crear_invalido_response.text}")
            
            # 4. Verificar que el cliente aparece en la lista
            print("\n4. Verificando lista de clientes...")
            lista_response = requests.get(f"{BASE_URL}/api/v1/clientes/", headers=headers)
            print(f"   Status: {lista_response.status_code}")
            if lista_response.status_code == 200:
                data = lista_response.json()
                print(f"   Total clientes: {data.get('total', 0)}")
                if data.get('items'):
                    print(f"   Último cliente: {data['items'][0]}")
            else:
                print(f"   Error: {lista_response.text}")
                
        else:
            print(f"Error en login: {login_response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    probar_creacion_cliente()
