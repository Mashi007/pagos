#!/usr/bin/env python3
"""
Script simple para probar endpoints sin autenticación
"""
import requests
import json

# Configuración
BASE_URL = "https://pagos-f2qf.onrender.com"
API_BASE = f"{BASE_URL}/api/v1"

def test_endpoint(url):
    """Probar un endpoint"""
    try:
        print(f"\nProbando: GET {url}")
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("EXITO")
            try:
                data = response.json()
                print(f"Respuesta: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}...")
            except:
                print(f"Respuesta: {response.text[:200]}...")
        else:
            print("ERROR")
            print(f"Error: {response.text[:200]}...")
            
        return response.status_code == 200
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR DE CONEXION: {e}")
        return False

def main():
    """Función principal"""
    print("PROBANDO ENDPOINTS SIN AUTENTICACION")
    print("=" * 50)
    
    # Endpoints que no requieren autenticación
    endpoints = [
        f"{API_BASE}/health",
        f"{API_BASE}/validadores/test-simple",
    ]
    
    success_count = 0
    for endpoint in endpoints:
        if test_endpoint(endpoint):
            success_count += 1
    
    print(f"\nRESUMEN: {success_count}/{len(endpoints)} endpoints funcionando")

if __name__ == "__main__":
    main()
