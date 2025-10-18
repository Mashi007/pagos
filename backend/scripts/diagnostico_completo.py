#!/usr/bin/env python3
"""
Script simple para probar conexión a BD y verificar estructura
"""
import requests
import json

def probar_conexion_bd():
    """Probar conexión a la base de datos via API"""
    print("PROBANDO CONEXION A BASE DE DATOS")
    print("=" * 40)
    
    base_url = "https://pagos-f2qf.onrender.com"
    
    try:
        # Probar endpoint de health
        print("1. Probando endpoint de health...")
        response = requests.get(f"{base_url}/api/v1/health", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   OK - Servidor respondiendo")
        else:
            print(f"   ERROR - {response.text}")
            return False
        
        # Probar login
        print("\n2. Probando login...")
        login_data = {
            "username": "itmaster@rapicreditca.com",
            "password": "admin123"
        }
        
        login_response = requests.post(
            f"{base_url}/api/v1/auth/login",
            data=login_data,
            timeout=10
        )
        
        print(f"   Status: {login_response.status_code}")
        
        if login_response.status_code == 200:
            print("   OK - Login exitoso")
            token = login_response.json().get("access_token")
            
            # Probar endpoint de usuarios
            print("\n3. Probando endpoint de usuarios...")
            headers = {"Authorization": f"Bearer {token}"}
            
            users_response = requests.get(
                f"{base_url}/api/v1/users/test-simple",
                headers=headers,
                timeout=10
            )
            
            print(f"   Status: {users_response.status_code}")
            
            if users_response.status_code == 200:
                data = users_response.json()
                print("   OK - Endpoint de usuarios funcionando")
                print(f"   Total usuarios: {data.get('total_users', 0)}")
                
                if data.get('users'):
                    usuario = data['users'][0]
                    print(f"   Usuario ejemplo:")
                    print(f"     Email: {usuario.get('email')}")
                    print(f"     Nombre: {usuario.get('nombre')}")
                    print(f"     Apellido: {usuario.get('apellido')}")
                    print(f"     Rol: {usuario.get('rol')}")
                
                return True
            else:
                print(f"   ERROR - {users_response.text}")
                return False
        else:
            print(f"   ERROR - {login_response.text}")
            return False
            
    except Exception as e:
        print(f"ERROR - {e}")
        return False

def probar_creacion_usuario():
    """Probar creación de usuario"""
    print("\nPROBANDO CREACION DE USUARIO")
    print("=" * 40)
    
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
        
        # Datos de usuario de prueba
        user_data = {
            "email": "test@example.com",
            "nombre": "Test",
            "apellido": "Usuario",
            "cargo": "Desarrollador",
            "rol": "USER",
            "password": "test123456",
            "is_active": True
        }
        
        print("Datos enviados:")
        print(json.dumps(user_data, indent=2))
        
        # Crear usuario
        create_response = requests.post(
            f"{base_url}/api/v1/users/",
            json=user_data,
            headers=headers,
            timeout=10
        )
        
        print(f"\nStatus de creación: {create_response.status_code}")
        print(f"Respuesta: {create_response.text}")
        
        if create_response.status_code == 201:
            print("OK - Usuario creado exitosamente")
            return True
        else:
            print("ERROR - No se pudo crear usuario")
            return False
            
    except Exception as e:
        print(f"ERROR - {e}")
        return False

def main():
    """Función principal"""
    print("DIAGNOSTICO COMPLETO DEL SISTEMA")
    print("=" * 50)
    
    # Probar conexión
    conexion_ok = probar_conexion_bd()
    
    if conexion_ok:
        # Probar creación
        creacion_ok = probar_creacion_usuario()
        
        print("\n" + "=" * 50)
        print("RESUMEN")
        print("=" * 50)
        print(f"Conexión BD: {'OK' if conexion_ok else 'ERROR'}")
        print(f"Creación usuario: {'OK' if creacion_ok else 'ERROR'}")
        
        if conexion_ok and creacion_ok:
            print("\nSistema funcionando correctamente")
        else:
            print("\nHay problemas en el sistema")
    else:
        print("\nNo se pudo conectar a la base de datos")

if __name__ == "__main__":
    main()
