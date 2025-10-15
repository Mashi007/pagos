#!/usr/bin/env python3
"""
Script de prueba para verificar endpoints de configuración
"""
import requests
import json
import sys

# Configuración
BASE_URL = "https://pagos-f2qf.onrender.com"
API_BASE = f"{BASE_URL}/api/v1"

def test_endpoint(url, method="GET", data=None, headers=None):
    """Probar un endpoint"""
    try:
        print(f"\nProbando: {method} {url}")
        
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        
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
    """Función principal de pruebas"""
    print("INICIANDO PRUEBAS DE ENDPOINTS DE CONFIGURACION")
    print("=" * 60)
    
    # 1. Probar health check
    print("\n1. HEALTH CHECK")
    test_endpoint(f"{API_BASE}/health")
    
    # 2. Probar login para obtener token
    print("\n2. LOGIN")
    login_data = {
        "email": "admin@financiamiento.com",
        "password": "admin123",
        "remember": True
    }
    
    login_response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
    
    if login_response.status_code == 200:
        print("Login exitoso")
        try:
            token_data = login_response.json()
            access_token = token_data.get("access_token")
            headers = {"Authorization": f"Bearer {access_token}"}
            print(f"Token obtenido: {access_token[:20]}...")
        except:
            print("Error procesando respuesta de login")
            return
    else:
        print("Login fallo")
        print(f"Error: {login_response.text}")
        return
    
    # 3. Probar endpoints de configuración
    print("\n3. ENDPOINTS DE CONFIGURACIÓN")
    
    endpoints_to_test = [
        f"{API_BASE}/validadores/configuracion",
        f"{API_BASE}/validadores/test-simple",
        f"{API_BASE}/concesionarios/activos",
        f"{API_BASE}/asesores/activos",
        f"{API_BASE}/configuracion/sistema/completa"
    ]
    
    success_count = 0
    total_count = len(endpoints_to_test)
    
    for endpoint in endpoints_to_test:
        if test_endpoint(endpoint, headers=headers):
            success_count += 1
    
    # 4. Resumen
    print("\n" + "=" * 60)
    print(f"RESUMEN: {success_count}/{total_count} endpoints funcionando")
    
    if success_count == total_count:
        print("TODOS LOS ENDPOINTS FUNCIONANDO")
    elif success_count > 0:
        print("ALGUNOS ENDPOINTS FUNCIONANDO")
    else:
        print("NINGUN ENDPOINT FUNCIONANDO")
    
    print("\nPROXIMOS PASOS:")
    if success_count < total_count:
        print("- Verificar que las tablas existan en la base de datos")
        print("- Ejecutar migraciones de Alembic")
        print("- Poblar datos de ejemplo")
    else:
        print("- El formulario deberia funcionar correctamente")
        print("- Probar creacion de cliente")

if __name__ == "__main__":
    main()
