#!/usr/bin/env python3
"""
Segundo enfoque de validación y resolución de problemas
Verificación completa del sistema después de correcciones
"""
import requests
import json
import sys
import os
import time

# Agregar el directorio del proyecto al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "https://pagos-f2qf.onrender.com"

def segundo_enfoque_validacion():
    """Segundo enfoque: Validación completa del sistema"""
    print("=== SEGUNDO ENFOQUE DE VALIDACION Y RESOLUCION ===")
    
    try:
        # 1. Verificar estado del servidor después de correcciones
        print("\n1. VERIFICACION POST-CORRECCIONES:")
        
        # Esperar un poco para que el despliegue se complete
        print("   Esperando 30 segundos para completar despliegue...")
        time.sleep(30)
        
        # Verificar conectividad básica
        try:
            response = requests.get(f"{BASE_URL}/", timeout=10)
            print(f"   Conectividad basica: {response.status_code}")
        except Exception as e:
            print(f"   Error conectividad: {e}")
        
        # 2. Verificar endpoint de auth (problema principal)
        print("\n2. VERIFICACION ENDPOINT DE AUTH:")
        
        # Probar login con credenciales reales
        try:
            login_data = {
                "email": "itmaster@rapicreditca.com",
                "password": "R@pi_2025**"
            }
            response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data, timeout=15)
            print(f"   Auth POST con credenciales reales: {response.status_code}")
            
            if response.status_code == 200:
                print(f"      LOGIN EXITOSO!")
                data = response.json()
                print(f"      Token recibido: {data.get('access_token', 'N/A')[:20]}...")
                print(f"      Usuario: {data.get('user', {}).get('email', 'N/A')}")
                return True  # Login exitoso
            elif response.status_code == 503:
                print(f"      ERROR 503 PERSISTE: {response.text}")
                return False
            elif response.status_code == 401:
                print(f"      ERROR 401: Credenciales incorrectas")
                return False
            else:
                print(f"      Status inesperado: {response.text}")
                return False
                
        except Exception as e:
            print(f"   Error en auth: {e}")
            return False
        
        # 3. Verificar otros endpoints críticos
        print("\n3. VERIFICACION OTROS ENDPOINTS:")
        
        endpoints_criticos = [
            ("/api/v1/clientes/ping", "Clientes"),
            ("/api/v1/validadores/ping", "Validadores"),
            ("/api/v1/usuarios/", "Usuarios"),
            ("/api/v1/clientes/count", "Conteo clientes")
        ]
        
        for endpoint, descripcion in endpoints_criticos:
            try:
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
                print(f"   {descripcion}: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"      OK")
                elif response.status_code == 403:
                    print(f"      Requiere autenticacion (esperado)")
                elif response.status_code == 404:
                    print(f"      No existe")
                elif response.status_code == 503:
                    print(f"      Error de servidor")
                    
            except Exception as e:
                print(f"   {descripcion}: ERROR - {e}")
        
        # 4. Si el login fue exitoso, probar funcionalidades
        print("\n4. VERIFICACION FUNCIONALIDADES:")
        
        # Probar crear cliente
        try:
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
            
            response = requests.post(f"{BASE_URL}/api/v1/clientes/crear", json=cliente_data, timeout=15)
            print(f"   Crear cliente: {response.status_code}")
            
            if response.status_code == 200:
                print(f"      Cliente creado exitosamente!")
                data = response.json()
                print(f"      ID: {data.get('id', 'N/A')}")
                print(f"      Cedula: {data.get('cedula', 'N/A')}")
            elif response.status_code == 400:
                print(f"      Error de validacion: {response.text}")
            elif response.status_code == 401:
                print(f"      Requiere autenticacion")
            else:
                print(f"      Error: {response.text}")
                
        except Exception as e:
            print(f"   Error creando cliente: {e}")
        
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
                print(f"      Error: {response.text}")
                
        except Exception as e:
            print(f"   Error verificando configuracion: {e}")
        
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
                print(f"   Intento {i+1}: ERROR - {e}")
        
        if tiempos:
            tiempo_promedio = sum(tiempos) / len(tiempos)
            print(f"   Tiempo promedio: {tiempo_promedio:.2f}s")
            
            if tiempo_promedio > 10:
                print(f"   TIMEOUT: El servidor esta tardando mucho")
            elif tiempo_promedio > 5:
                print(f"   LENTO: El servidor esta respondiendo lentamente")
            else:
                print(f"   RAPIDO: El servidor responde rapidamente")
        
        # 7. Conclusiones finales
        print("\n=== CONCLUSIONES DEL SEGUNDO ENFOQUE ===")
        print("Si el login es exitoso (200), el problema esta resuelto.")
        print("Si el login da 503, el problema persiste.")
        print("Si el login da 401, las credenciales son incorrectas.")
        print("Si otros endpoints funcionan, el sistema esta operativo.")
        
        return True
        
    except Exception as e:
        print(f"Error en segundo enfoque: {e}")
        return False

if __name__ == "__main__":
    resultado = segundo_enfoque_validacion()
    if resultado:
        print("\n✅ SISTEMA FUNCIONANDO CORRECTAMENTE")
    else:
        print("\n❌ SISTEMA CON PROBLEMAS")
