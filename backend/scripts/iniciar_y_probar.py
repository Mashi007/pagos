#!/usr/bin/env python3
"""
Script para iniciar el servidor y probar endpoints
"""
import subprocess
import time
import requests
import sys
import os

def start_server():
    """Iniciar el servidor FastAPI"""
    print("Iniciando servidor FastAPI...")
    
    try:
        # Cambiar al directorio backend
        os.chdir("backend")
        
        # Iniciar servidor en background
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--reload", 
            "--host", "0.0.0.0", 
            "--port", "8000"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print("Servidor iniciado. Esperando que este listo...")
        
        # Esperar a que el servidor esté listo
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                response = requests.get("http://localhost:8000/docs", timeout=2)
                if response.status_code == 200:
                    print("OK - Servidor listo!")
                    return process
            except:
                pass
            
            time.sleep(1)
            print(f"Esperando servidor... ({attempt + 1}/{max_attempts})")
        
        print("ERROR - Servidor no se inicio correctamente")
        process.terminate()
        return None
        
    except Exception as e:
        print(f"ERROR - Error iniciando servidor: {e}")
        return None

def test_basic_endpoints():
    """Probar endpoints básicos"""
    print("\nProbando endpoints básicos...")
    
    endpoints = [
        ("GET", "/docs"),
        ("GET", "/api/v1/auth/login"),
        ("GET", "/api/v1/dashboard/"),
        ("GET", "/api/v1/clientes/"),
        ("GET", "/api/v1/prestamos/"),
        ("GET", "/api/v1/pagos/"),
    ]
    
    successful = 0
    failed = 0
    
    for method, endpoint in endpoints:
        try:
            url = f"http://localhost:8000{endpoint}"
            if method == "GET":
                response = requests.get(url, timeout=5)
            else:
                response = requests.post(url, timeout=5)
            
            if response.status_code in [200, 422, 401]:  # 422 y 401 son esperados sin auth
                print(f"  OK - {method} {endpoint} - {response.status_code}")
                successful += 1
            else:
                print(f"  ERROR - {method} {endpoint} - {response.status_code}")
                failed += 1
                
        except Exception as e:
            print(f"  ERROR - {method} {endpoint} - {e}")
            failed += 1
    
    print(f"\nResultados: {successful} exitosos, {failed} fallidos")
    return successful, failed

def test_auth_endpoint():
    """Probar endpoint de autenticación"""
    print("\nProbando autenticación...")
    
    try:
        # Probar login con credenciales de Daniel
        login_data = {
            "username": "itmaster@rapicreditca.com",
            "password": "admin123"
        }
        
        response = requests.post(
            "http://localhost:8000/api/v1/auth/login",
            data=login_data,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print(f"  OK - Login exitoso, token obtenido")
            
            # Probar endpoint protegido
            headers = {"Authorization": f"Bearer {token}"}
            protected_response = requests.get(
                "http://localhost:8000/api/v1/auth/me",
                headers=headers,
                timeout=5
            )
            
            if protected_response.status_code == 200:
                user_data = protected_response.json()
                print(f"  OK - Usuario autenticado: {user_data.get('email', 'N/A')}")
                print(f"  OK - Rol del usuario: {user_data.get('rol', 'N/A')}")
                return True
            else:
                print(f"  ERROR - Error en endpoint protegido: {protected_response.status_code}")
                return False
        else:
            print(f"  ERROR - Error en login: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"  ERROR - Error en autenticación: {e}")
        return False

def main():
    """Función principal"""
    print("INICIANDO SERVIDOR Y PRUEBAS DE ENDPOINTS")
    print("=" * 60)
    
    # Iniciar servidor
    server_process = start_server()
    if not server_process:
        print("No se pudo iniciar el servidor. Abortando.")
        return
    
    try:
        # Probar endpoints básicos
        successful, failed = test_basic_endpoints()
        
        # Probar autenticación
        auth_success = test_auth_endpoint()
        
        # Resumen final
        print("\n" + "=" * 60)
        print("RESUMEN FINAL DE PRUEBAS")
        print("=" * 60)
        print(f"Endpoints básicos: {successful} exitosos, {failed} fallidos")
        print(f"Autenticación: {'OK' if auth_success else 'ERROR'}")
        
        if successful > 0 and auth_success:
            print("\nRESULTADO: Sistema funcionando correctamente")
        else:
            print("\nRESULTADO: Hay problemas en el sistema")
            
    finally:
        # Terminar servidor
        print("\nTerminando servidor...")
        server_process.terminate()
        server_process.wait()
        print("Servidor terminado.")

if __name__ == "__main__":
    main()
