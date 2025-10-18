#!/usr/bin/env python3
"""
Script para verificar conexión frontend-backend
Especialmente para concesionarios y analistas
"""
import requests
import json
import time

def probar_endpoint_concesionarios():
    """Probar endpoints de concesionarios"""
    print("PROBANDO ENDPOINTS DE CONCESIONARIOS")
    print("=" * 50)
    
    base_url = "https://pagos-f2qf.onrender.com"
    
    try:
        # 1. Probar endpoint sin autenticación
        print("1. Probando endpoint sin autenticación...")
        response = requests.get(f"{base_url}/api/v1/concesionarios/test-no-auth", timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   OK - Total concesionarios: {data.get('total_concesionarios', 0)}")
            print(f"   Mensaje: {data.get('message', 'N/A')}")
        else:
            print(f"   ERROR - {response.text}")
            return False
        
        # 2. Probar endpoint simple
        print("\n2. Probando endpoint simple...")
        response = requests.get(f"{base_url}/api/v1/concesionarios/test-simple", timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   OK - Total concesionarios: {data.get('total_concesionarios', 0)}")
        else:
            print(f"   ERROR - {response.text}")
        
        # 3. Probar endpoint con autenticación
        print("\n3. Probando endpoint con autenticación...")
        
        # Login
        login_data = {
            "username": "itmaster@rapicreditca.com",
            "password": "admin123"
        }
        
        login_response = requests.post(
            f"{base_url}/api/v1/auth/login",
            data=login_data,
            timeout=10
        )
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}
            
            # Probar listado de concesionarios
            response = requests.get(
                f"{base_url}/api/v1/concesionarios/",
                headers=headers,
                timeout=10
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   OK - Total concesionarios: {data.get('total', 0)}")
                print(f"   Items: {len(data.get('items', []))}")
            else:
                print(f"   ERROR - {response.text}")
        else:
            print(f"   ERROR en login: {login_response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"ERROR - {e}")
        return False

def probar_endpoint_analistas():
    """Probar endpoints de analistas"""
    print("\nPROBANDO ENDPOINTS DE ANALISTAS")
    print("=" * 50)
    
    base_url = "https://pagos-f2qf.onrender.com"
    
    try:
        # Login
        login_data = {
            "username": "itmaster@rapicreditca.com",
            "password": "admin123"
        }
        
        login_response = requests.post(
            f"{base_url}/api/v1/auth/login",
            data=login_data,
            timeout=10
        )
        
        if login_response.status_code != 200:
            print(f"ERROR en login: {login_response.status_code}")
            return False
        
        token = login_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Probar endpoint de analistas
        print("1. Probando endpoint de analistas...")
        response = requests.get(
            f"{base_url}/api/v1/analistas/",
            headers=headers,
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   OK - Respuesta recibida")
            print(f"   Tipo de respuesta: {type(data)}")
        else:
            print(f"   ERROR - {response.text}")
        
        return True
        
    except Exception as e:
        print(f"ERROR - {e}")
        return False

def probar_creacion_concesionario():
    """Probar creación de concesionario"""
    print("\nPROBANDO CREACION DE CONCESIONARIO")
    print("=" * 50)
    
    base_url = "https://pagos-f2qf.onrender.com"
    
    try:
        # Login
        login_data = {
            "username": "itmaster@rapicreditca.com",
            "password": "admin123"
        }
        
        login_response = requests.post(
            f"{base_url}/api/v1/auth/login",
            data=login_data,
            timeout=10
        )
        
        if login_response.status_code != 200:
            print(f"ERROR en login: {login_response.status_code}")
            return False
        
        token = login_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Datos de concesionario de prueba
        concesionario_data = {
            "nombre": "Concesionario Test",
            "direccion": "Dirección de prueba",
            "telefono": "1234567890",
            "email": "test@concesionario.com",
            "responsable": "Responsable Test",
            "activo": True
        }
        
        print("Datos enviados:")
        print(json.dumps(concesionario_data, indent=2))
        
        # Crear concesionario
        response = requests.post(
            f"{base_url}/api/v1/concesionarios/",
            json=concesionario_data,
            headers=headers,
            timeout=10
        )
        
        print(f"\nStatus de creación: {response.status_code}")
        print(f"Respuesta: {response.text}")
        
        if response.status_code == 201:
            print("OK - Concesionario creado exitosamente")
            return True
        else:
            print("ERROR - No se pudo crear concesionario")
            return False
            
    except Exception as e:
        print(f"ERROR - {e}")
        return False

def main():
    """Función principal"""
    print("VERIFICACION DE CONEXION FRONTEND-BACKEND")
    print("=" * 60)
    
    # Probar concesionarios
    concesionarios_ok = probar_endpoint_concesionarios()
    
    # Probar analistas
    analistas_ok = probar_endpoint_analistas()
    
    # Probar creación de concesionario
    creacion_ok = probar_creacion_concesionario()
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE PRUEBAS")
    print("=" * 60)
    print(f"Endpoints concesionarios: {'OK' if concesionarios_ok else 'ERROR'}")
    print(f"Endpoints analistas: {'OK' if analistas_ok else 'ERROR'}")
    print(f"Creación concesionario: {'OK' if creacion_ok else 'ERROR'}")
    
    if concesionarios_ok and analistas_ok and creacion_ok:
        print("\nSistema funcionando correctamente")
    else:
        print("\nHay problemas de conexión frontend-backend")

if __name__ == "__main__":
    main()
