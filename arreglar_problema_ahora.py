#!/usr/bin/env python3
"""
SCRIPT PARA ARREGLAR EL PROBLEMA DE LOGIN INMEDIATAMENTE
"""
import requests
import time

def crear_usuario_y_probar():
    """Crear usuario de prueba y probar login"""
    backend_url = "https://pagos-f2qf.onrender.com"
    
    print("ARREGLANDO PROBLEMA DE LOGIN...")
    print("=" * 50)
    
    # Paso 1: Crear usuario de prueba
    print("1. Creando usuario de prueba...")
    try:
        response = requests.post(
            f"{backend_url}/api/v1/auth/create-test-user",
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Usuario creado: {data['message']}")
            print(f"   📧 Email: {data['credentials']['email']}")
            print(f"   🔑 Password: {data['credentials']['password']}")
        else:
            print(f"   ❌ Error creando usuario: {response.status_code}")
            print(f"   📄 Respuesta: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False
    
    # Paso 2: Probar login con las nuevas credenciales
    print("\n2. Probando login con nuevas credenciales...")
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
                print(f"   ✅ LOGIN EXITOSO!")
                print(f"   🔑 Token recibido: {login_data['access_token'][:20]}...")
                print(f"   👤 Usuario: {login_data.get('user', {}).get('nombre', 'N/A')}")
                print(f"   🎯 Rol: {login_data.get('user', {}).get('rol', 'N/A')}")
                
                # Paso 3: Probar endpoint protegido
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
                        print(f"   ✅ ENDPOINT PROTEGIDO FUNCIONA!")
                        print(f"   📊 Datos recibidos correctamente")
                        return True
                    else:
                        print(f"   ❌ Endpoint protegido falló: {protected_response.status_code}")
                        print(f"   📄 Respuesta: {protected_response.text}")
                        return False
                        
                except Exception as e:
                    print(f"   ❌ Error probando endpoint: {str(e)}")
                    return False
            else:
                print(f"   ❌ Login falló: No hay token en respuesta")
                return False
        else:
            print(f"   ❌ Login falló: {login_response.status_code}")
            print(f"   📄 Respuesta: {login_response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

def main():
    """Función principal"""
    print("SOLUCIONANDO PROBLEMA DE LOGIN EN RAPICREDIT")
    print("=" * 60)
    
    # Esperar un poco para que se despliegue
    print("Esperando 30 segundos para que se despliegue...")
    time.sleep(30)
    
    # Ejecutar solución
    success = crear_usuario_y_probar()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ PROBLEMA ARREGLADO EXITOSAMENTE!")
        print("\n🎯 CREDENCIALES FINALES:")
        print("   📧 Email: admin@rapicredit.com")
        print("   🔑 Password: admin123")
        print("\n🚀 PRÓXIMOS PASOS:")
        print("   1. Ir a: https://rapicredit.onrender.com")
        print("   2. Login con las credenciales de arriba")
        print("   3. Verificar que funciona correctamente")
        print("   4. Navegar a /clientes sin errores")
    else:
        print("❌ PROBLEMA NO SE PUDO ARREGLAR AUTOMÁTICAMENTE")
        print("💡 Verifica manualmente el endpoint:")
        print("   POST https://pagos-f2qf.onrender.com/api/v1/auth/create-test-user")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
