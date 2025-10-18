#!/usr/bin/env python3
"""
Script para verificar el estado del servidor y probar creación de usuarios
"""
import requests
import json
import time

def check_server_status():
    """Verificar estado del servidor"""
    urls_to_check = [
        "https://pagos-f2qf.onrender.com",
        "http://localhost:8000"
    ]
    
    for url in urls_to_check:
        try:
            print(f"Verificando servidor en: {url}")
            response = requests.get(f"{url}/docs", timeout=10)
            if response.status_code == 200:
                print(f"OK - Servidor funcionando en: {url}")
                return url
            else:
                print(f"WARNING - Servidor responde con status {response.status_code}")
        except Exception as e:
            print(f"ERROR - Error conectando a {url}: {e}")
    
    return None

def test_user_creation(base_url):
    """Probar creación de usuario"""
    print(f"\nProbando creación de usuario en: {base_url}")
    
    # Primero hacer login como admin
    login_data = {
        "username": "itmaster@rapicreditca.com",
        "password": "admin123"
    }
    
    try:
        login_response = requests.post(
            f"{base_url}/api/v1/auth/login",
            data=login_data,
            timeout=10
        )
        
        if login_response.status_code != 200:
            print(f"ERROR - Error en login: {login_response.status_code}")
            print(f"Respuesta: {login_response.text}")
            return False
        
        token = login_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        print("OK - Login exitoso")
        
        # Probar creación de usuario
        user_data = {
            "email": "test@example.com",
            "nombre": "Test",
            "apellido": "Usuario",
            "cargo": "Desarrollador",
            "rol": "USER",
            "password": "test123456",
            "is_active": True
        }
        
        create_response = requests.post(
            f"{base_url}/api/v1/users/",
            json=user_data,
            headers=headers,
            timeout=10
        )
        
        print(f"Status de creación: {create_response.status_code}")
        
        if create_response.status_code == 201:
            print("OK - Usuario creado exitosamente")
            user_info = create_response.json()
            print(f"Usuario creado: {user_info.get('email')} - {user_info.get('nombre')} {user_info.get('apellido')}")
            return True
        elif create_response.status_code == 400:
            error_detail = create_response.json().get("detail", "Error desconocido")
            print(f"ERROR - Error de validación: {error_detail}")
            return False
        else:
            print(f"ERROR - Error inesperado: {create_response.status_code}")
            print(f"Respuesta: {create_response.text}")
            return False
            
    except Exception as e:
        print(f"ERROR - Error en prueba: {e}")
        return False

def test_existing_user(base_url):
    """Probar creación de usuario existente"""
    print(f"\nProbando creación de usuario existente...")
    
    # Login como admin
    login_data = {
        "username": "itmaster@rapicreditca.com",
        "password": "admin123"
    }
    
    try:
        login_response = requests.post(
            f"{base_url}/api/v1/auth/login",
            data=login_data,
            timeout=10
        )
        
        if login_response.status_code != 200:
            return False
        
        token = login_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Intentar crear usuario con email existente
        user_data = {
            "email": "itmaster@rapicreditca.com",  # Email existente
            "nombre": "Daniel",
            "apellido": "Casañas",
            "cargo": "Consultor Tecnología",
            "rol": "ADMIN",
            "password": "admin123",
            "is_active": True
        }
        
        create_response = requests.post(
            f"{base_url}/api/v1/users/",
            json=user_data,
            headers=headers,
            timeout=10
        )
        
        print(f"Status de creación usuario existente: {create_response.status_code}")
        
        if create_response.status_code == 400:
            error_detail = create_response.json().get("detail", "Error desconocido")
            print(f"OK - Correctamente rechazado: {error_detail}")
            return True
        else:
            print(f"ERROR - Debería haber sido rechazado: {create_response.status_code}")
            return False
            
    except Exception as e:
        print(f"ERROR - Error en prueba: {e}")
        return False

def main():
    """Función principal"""
    print("VERIFICACION DEL SISTEMA DE USUARIOS")
    print("=" * 50)
    
    # Verificar servidor
    base_url = check_server_status()
    if not base_url:
        print("ERROR - No se pudo conectar a ningún servidor")
        return
    
    # Probar creación de usuario nuevo
    success_new = test_user_creation(base_url)
    
    # Probar creación de usuario existente
    success_existing = test_existing_user(base_url)
    
    # Resumen
    print("\n" + "=" * 50)
    print("RESUMEN DE PRUEBAS")
    print("=" * 50)
    print(f"Servidor: {base_url}")
    print(f"Creacion usuario nuevo: {'OK' if success_new else 'ERROR'}")
    print(f"Validacion usuario existente: {'OK' if success_existing else 'ERROR'}")
    
    if success_new and success_existing:
        print("\nSistema funcionando correctamente")
    else:
        print("\nHay problemas en el sistema")

if __name__ == "__main__":
    main()
