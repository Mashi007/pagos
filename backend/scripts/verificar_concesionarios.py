#!/usr/bin/env python3
"""
Script para verificar la estructura de la tabla concesionarios
"""

import requests
import json
from datetime import datetime

# Configuración
BASE_URL = "https://pagos-f2qf.onrender.com"

def test_concesionarios_structure():
    """Probar endpoints de concesionarios para ver la estructura real"""
    print(f"\n{'='*60}")
    print("VERIFICANDO ESTRUCTURA DE CONCESIONARIOS")
    print(f"{'='*60}")
    
    # Primero hacer login para obtener token
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
        
        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token')
            print("✅ Login exitoso")
            
            # Probar endpoint que funciona (test-simple)
            print(f"\n{'-'*40}")
            print("PROBANDO: Concesionarios Test Simple")
            print(f"{'-'*40}")
            
            response = requests.get(
                f"{BASE_URL}/api/v1/concesionarios/test-simple",
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Test simple funciona")
                print(f"Data: {json.dumps(data, indent=2, ensure_ascii=False)}")
            else:
                print("❌ Test simple falla")
                print(f"Error: {response.text}")
                
            # Probar endpoint con auth
            print(f"\n{'-'*40}")
            print("PROBANDO: Concesionarios con Auth")
            print(f"{'-'*40}")
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{BASE_URL}/api/v1/concesionarios",
                headers=headers,
                params={"limit": 5},
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Endpoint con auth funciona")
                print(f"Data: {json.dumps(data, indent=2, ensure_ascii=False)}")
            else:
                print("❌ Endpoint con auth falla")
                print(f"Error: {response.text}")
                
        else:
            print("❌ Login falló")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error general: {e}")

def main():
    """Función principal"""
    print("VERIFICANDO ESTRUCTURA DE CONCESIONARIOS")
    print(f"Base URL: {BASE_URL}")
    print(f"Timestamp: {datetime.now()}")
    
    test_concesionarios_structure()
    
    print(f"\n{'='*60}")
    print("VERIFICACION COMPLETADA")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
