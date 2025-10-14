#!/usr/bin/env python3
"""
TEST SIMPLE DE LOGIN - VERIFICAR CREDENCIALES
Script simple para probar login con diferentes credenciales
"""
import requests
import json

def test_login_credentials():
    """Probar diferentes credenciales de login"""
    api_url = "https://pagos-f2qf.onrender.com"
    
    # Lista de credenciales a probar
    credentials_to_test = [
        {
            "email": "admin@financiamiento.com",
            "password": "admin123",
            "description": "Credencial original con contraseña común"
        },
        {
            "email": "admin@financiamiento.com", 
            "password": "admin",
            "description": "Credencial original con contraseña simple"
        },
        {
            "email": "admin@financiamiento.com",
            "password": "password",
            "description": "Credencial original con contraseña por defecto"
        },
        {
            "email": "admin@financiamiento.com",
            "password": "123456",
            "description": "Credencial original con contraseña numérica"
        },
        {
            "email": "admin@rapicredit.com",
            "password": "admin123",
            "description": "Credencial alternativa con contraseña común"
        },
        {
            "email": "admin@rapicredit.com",
            "password": "admin",
            "description": "Credencial alternativa con contraseña simple"
        }
    ]
    
    print("PROBANDO CREDENCIALES DE LOGIN")
    print("=" * 60)
    
    successful_logins = []
    
    for i, creds in enumerate(credentials_to_test, 1):
        print(f"\n{i}. Probando: {creds['description']}")
        print(f"   Email: {creds['email']}")
        print(f"   Password: {creds['password']}")
        
        try:
            response = requests.post(
                f"{api_url}/api/v1/auth/login",
                json={
                    "email": creds["email"],
                    "password": creds["password"],
                    "remember": True
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'access_token' in data['data']:
                    print(f"   OK LOGIN EXITOSO!")
                    print(f"   Token recibido: {data['data']['access_token'][:20]}...")
                    print(f"   Usuario: {data.get('user', {}).get('nombre', 'N/A')}")
                    print(f"   Rol: {data.get('user', {}).get('rol', 'N/A')}")
                    
                    successful_logins.append({
                        "email": creds["email"],
                        "password": creds["password"],
                        "description": creds["description"],
                        "token": data['data']['access_token'],
                        "user": data.get('user', {})
                    })
                else:
                    print(f"   ERROR Login fallo: No hay token en respuesta")
                    print(f"   Respuesta: {response.text}")
            else:
                print(f"   ERROR Login fallo: HTTP {response.status_code}")
                print(f"   Respuesta: {response.text}")
                
        except Exception as e:
            print(f"   ERROR: {str(e)}")
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE PRUEBAS:")
    
    if successful_logins:
        print(f"OK {len(successful_logins)} credencial(es) exitosa(s):")
        for login in successful_logins:
            print(f"   Email: {login['email']}")
            print(f"   Password: {login['password']}")
            print(f"   Usuario: {login['user'].get('nombre', 'N/A')} ({login['user'].get('rol', 'N/A')})")
            print()
        
        print("CREDENCIALES VALIDAS ENCONTRADAS:")
        print("   Usa estas credenciales para hacer login en la aplicacion")
        print("   https://rapicredit.onrender.com")
    else:
        print("ERROR Ninguna credencial funciono")
        print("Posibles causas:")
        print("   - Usuario no existe en la base de datos")
        print("   - Contraseña incorrecta")
        print("   - Problema con el endpoint de login")
        print("   - Base de datos no inicializada correctamente")
    
    print("=" * 60)
    return successful_logins

def test_protected_endpoint(token):
    """Probar endpoint protegido con token"""
    api_url = "https://pagos-f2qf.onrender.com"
    
    print(f"\n🔒 Probando endpoint protegido con token...")
    
    try:
        response = requests.get(
            f"{api_url}/api/v1/clientes?page=1&per_page=5",
            headers={
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json'
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Endpoint protegido accesible")
            print(f"   📊 Datos recibidos: {len(data.get('data', []))} clientes")
            return True
        else:
            print(f"   ❌ Endpoint protegido falló: HTTP {response.status_code}")
            print(f"   📄 Respuesta: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

def main():
    """Función principal"""
    # Probar credenciales
    successful_logins = test_login_credentials()
    
    # Si hay logins exitosos, probar endpoint protegido
    if successful_logins:
        print(f"\n🧪 Probando endpoint protegido con primera credencial exitosa...")
        first_login = successful_logins[0]
        test_protected_endpoint(first_login['token'])
    
    print(f"\n🎯 PRÓXIMOS PASOS:")
    if successful_logins:
        print("1. Usar las credenciales encontradas en la aplicación")
        print("2. Verificar que los tokens se almacenan correctamente")
        print("3. Navegar a la sección de clientes")
    else:
        print("1. Verificar que el usuario existe en la base de datos")
        print("2. Crear usuario de prueba con contraseña conocida")
        print("3. Verificar configuración del backend")

if __name__ == "__main__":
    main()
