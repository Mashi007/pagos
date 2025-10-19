"""
Segundo enfoque de validación y resolución de problemas
Verificación manual del sistema después de correcciones
"""
import requests
import json
import time

BASE_URL = "https://pagos-f2qf.onrender.com"

def verificar_sistema():
    """Verificación manual del sistema"""
    print("=== SEGUNDO ENFOQUE DE VALIDACION Y RESOLUCION ===")
    
    try:
        # 1. Verificar conectividad básica
        print("\n1. VERIFICACION CONECTIVIDAD BASICA:")
        try:
            response = requests.get(f"{BASE_URL}/", timeout=10)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Servidor respondiendo")
            else:
                print("   ❌ Servidor con problemas")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 2. Verificar endpoint de auth (problema principal)
        print("\n2. VERIFICACION ENDPOINT DE AUTH:")
        
        # Probar login con credenciales reales
        login_data = {
            "email": "itmaster@rapicreditca.com",
            "password": "R@pi_2025**"
        }
        
        try:
            response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data, timeout=15)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ LOGIN EXITOSO!")
                data = response.json()
                print(f"   Token: {data.get('access_token', 'N/A')[:20]}...")
                print(f"   Usuario: {data.get('user', {}).get('email', 'N/A')}")
                return True
            elif response.status_code == 503:
                print("   ❌ ERROR 503 PERSISTE")
                print(f"   Detalles: {response.text}")
                return False
            elif response.status_code == 401:
                print("   ❌ ERROR 401: Credenciales incorrectas")
                return False
            else:
                print(f"   ❌ Status inesperado: {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error en auth: {e}")
            return False
        
        # 3. Verificar otros endpoints críticos
        print("\n3. VERIFICACION OTROS ENDPOINTS:")
        
        endpoints = [
            ("/api/v1/clientes/ping", "Clientes"),
            ("/api/v1/validadores/ping", "Validadores"),
            ("/api/v1/usuarios/", "Usuarios"),
            ("/api/v1/clientes/count", "Conteo clientes")
        ]
        
        for endpoint, descripcion in endpoints:
            try:
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
                print(f"   {descripcion}: {response.status_code}")
                
                if response.status_code == 200:
                    print("      ✅ OK")
                elif response.status_code == 403:
                    print("      ⚠️ Requiere autenticacion (esperado)")
                elif response.status_code == 404:
                    print("      ❌ No existe")
                elif response.status_code == 503:
                    print("      ❌ Error de servidor")
                    
            except Exception as e:
                print(f"   {descripcion}: ❌ ERROR - {e}")
        
        # 4. Probar funcionalidades
        print("\n4. VERIFICACION FUNCIONALIDADES:")
        
        # Probar crear cliente
        cliente_data = {
            "cedula": "V12345678",
            "nombres": "Juan Carlos",
            "apellidos": "Perez Gonzalez",
            "telefono": "4241234567",
            "email": "juan.perez@ejemplo.com",
            "direccion": "Av. Principal, Caracas",
            "modelo_vehiculo": "Toyota Corolla",
            "concesionario": "AutoCenter Caracas"
        }
        
        try:
            response = requests.post(f"{BASE_URL}/api/v1/clientes/crear", json=cliente_data, timeout=15)
            print(f"   Crear cliente: {response.status_code}")
            
            if response.status_code == 200:
                print("      ✅ Cliente creado exitosamente!")
                data = response.json()
                print(f"      ID: {data.get('id', 'N/A')}")
                print(f"      Cedula: {data.get('cedula', 'N/A')}")
            elif response.status_code == 400:
                print("      ⚠️ Error de validacion")
                print(f"      Detalles: {response.text}")
            elif response.status_code == 401:
                print("      ⚠️ Requiere autenticacion")
            else:
                print(f"      ❌ Error: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error creando cliente: {e}")
        
        # 5. Verificar opciones de configuración
        print("\n5. VERIFICACION CONFIGURACION:")
        
        try:
            response = requests.get(f"{BASE_URL}/api/v1/clientes/opciones-configuracion", timeout=10)
            print(f"   Opciones configuracion: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"      Modelos vehiculos: {len(data.get('modelos_vehiculos', []))}")
                print(f"      Analistas: {len(data.get('analistas', []))}")
                print(f"      Concesionarios: {len(data.get('concesionarios', []))}")
            else:
                print(f"      ❌ Error: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error verificando configuracion: {e}")
        
        # 6. Análisis de timing
        print("\n6. ANALISIS DE TIMING:")
        
        tiempos = []
        for i in range(3):
            try:
                start_time = time.time()
                response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data, timeout=15)
                end_time = time.time()
                tiempo = end_time - start_time
                tiempos.append(tiempo)
                print(f"   Intento {i+1}: {response.status_code} en {tiempo:.2f}s")
            except Exception as e:
                print(f"   Intento {i+1}: ❌ ERROR - {e}")
        
        if tiempos:
            tiempo_promedio = sum(tiempos) / len(tiempos)
            print(f"   Tiempo promedio: {tiempo_promedio:.2f}s")
            
            if tiempo_promedio > 10:
                print("   ⚠️ TIMEOUT: El servidor esta tardando mucho")
            elif tiempo_promedio > 5:
                print("   ⚠️ LENTO: El servidor esta respondiendo lentamente")
            else:
                print("   ✅ RAPIDO: El servidor responde rapidamente")
        
        # 7. Conclusiones finales
        print("\n=== CONCLUSIONES DEL SEGUNDO ENFOQUE ===")
        print("✅ Si el login es exitoso (200), el problema esta resuelto.")
        print("❌ Si el login da 503, el problema persiste.")
        print("⚠️ Si el login da 401, las credenciales son incorrectas.")
        print("✅ Si otros endpoints funcionan, el sistema esta operativo.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en segundo enfoque: {e}")
        return False

if __name__ == "__main__":
    resultado = verificar_sistema()
    if resultado:
        print("\n✅ SISTEMA FUNCIONANDO CORRECTAMENTE")
    else:
        print("\n❌ SISTEMA CON PROBLEMAS")
