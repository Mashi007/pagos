#!/usr/bin/env python3
import requests
import time

def main():
    print("SOLUCIONANDO PROBLEMA DE LOGIN")
    print("=" * 40)
    
    backend_url = "https://pagos-f2qf.onrender.com"
    
    # Esperar despliegue
    print("Esperando despliegue...")
    time.sleep(30)
    
    # Crear usuario
    print("1. Creando usuario de prueba...")
    try:
        response = requests.post(f"{backend_url}/api/v1/auth/create-test-user", timeout=15)
        if response.status_code == 200:
            data = response.json()
            print(f"   OK Usuario creado: {data['message']}")
            print(f"   Email: {data['credentials']['email']}")
            print(f"   Password: {data['credentials']['password']}")
        else:
            print(f"   ERROR: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return
    except Exception as e:
        print(f"   ERROR: {str(e)}")
        return
    
    # Probar login
    print("\n2. Probando login...")
    try:
        login_response = requests.post(
            f"{backend_url}/api/v1/auth/login",
            json={
                "email": "admin@rapicredit.com",
                "password": "admin123",
                "remember": True
            },
            timeout=15
        )
        
        if login_response.status_code == 200:
            login_data = login_response.json()
            if 'access_token' in login_data:
                print(f"   OK LOGIN EXITOSO!")
                print(f"   Token: {login_data['access_token'][:20]}...")
                print(f"   Usuario: {login_data.get('user', {}).get('nombre', 'N/A')}")
                print(f"   Rol: {login_data.get('user', {}).get('rol', 'N/A')}")
                
                # Probar endpoint
                print("\n3. Probando endpoint protegido...")
                try:
                    protected_response = requests.get(
                        f"{backend_url}/api/v1/clientes?page=1&per_page=5",
                        headers={
                            'Authorization': f'Bearer {login_data["access_token"]}',
                            'Accept': 'application/json'
                        },
                        timeout=15
                    )
                    
                    if protected_response.status_code == 200:
                        print(f"   OK ENDPOINT FUNCIONA!")
                        print(f"   Datos recibidos correctamente")
                        
                        print("\n" + "=" * 40)
                        print("PROBLEMA ARREGLADO!")
                        print("=" * 40)
                        print("CREDENCIALES:")
                        print("Email: admin@rapicredit.com")
                        print("Password: admin123")
                        print("\nPROXIMOS PASOS:")
                        print("1. Ir a: https://rapicredit.onrender.com")
                        print("2. Login con las credenciales de arriba")
                        print("3. Verificar que funciona")
                        print("=" * 40)
                        return True
                    else:
                        print(f"   ERROR endpoint: {protected_response.status_code}")
                        return False
                        
                except Exception as e:
                    print(f"   ERROR endpoint: {str(e)}")
                    return False
            else:
                print(f"   ERROR: No hay token en respuesta")
                return False
        else:
            print(f"   ERROR login: {login_response.status_code}")
            print(f"   Respuesta: {login_response.text}")
            return False
            
    except Exception as e:
        print(f"   ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    main()
