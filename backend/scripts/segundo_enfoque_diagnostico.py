#!/usr/bin/env python3
"""
Segundo enfoque de diagnóstico - Análisis profundo de causa raíz
"""
import requests
import json
import sys
import os
import time

# Agregar el directorio del proyecto al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "https://pagos-f2qf.onrender.com"

def segundo_enfoque_diagnostico():
    """Segundo enfoque: Análisis profundo de causa raíz"""
    print("=== SEGUNDO ENFOQUE DE DIAGNÓSTICO - CAUSA RAÍZ ===")
    
    try:
        # 1. Verificar estado de todos los endpoints críticos
        print("\n1. VERIFICACIÓN COMPLETA DE ENDPOINTS:")
        endpoints_criticos = [
            ("GET", "/", "Conectividad básica"),
            ("GET", "/api/v1/clientes/ping", "Clientes funcionando"),
            ("GET", "/api/v1/auth/login", "Auth GET (debería ser 405)"),
            ("POST", "/api/v1/auth/login", "Auth POST (problema principal)"),
            ("GET", "/api/v1/auth/me", "Auth me (requiere token)"),
            ("GET", "/api/v1/usuarios/", "Usuarios (requiere auth)"),
            ("GET", "/api/v1/validadores/ping", "Validadores"),
            ("GET", "/api/v1/carga-masiva/dashboard", "Carga masiva")
        ]
        
        for metodo, endpoint, descripcion in endpoints_criticos:
            try:
                if metodo == "GET":
                    response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
                elif metodo == "POST":
                    response = requests.post(f"{BASE_URL}{endpoint}", json={}, timeout=10)
                
                print(f"   {metodo} {endpoint}: {response.status_code} - {descripcion}")
                
                if response.status_code == 503:
                    print(f"      ❌ ERROR 503: {response.text}")
                elif response.status_code == 200:
                    print(f"      ✅ OK")
                elif response.status_code == 405:
                    print(f"      ⚠️  Method Not Allowed (esperado)")
                elif response.status_code == 403:
                    print(f"      ⚠️  Forbidden (requiere auth)")
                elif response.status_code == 404:
                    print(f"      ❌ Not Found")
                    
            except Exception as e:
                print(f"   {metodo} {endpoint}: ERROR - {e}")
        
        # 2. Análisis específico del error 503 en auth
        print("\n2. ANÁLISIS ESPECÍFICO DEL ERROR 503 EN AUTH:")
        
        # Probar diferentes variaciones del endpoint de auth
        variaciones_auth = [
            ("POST", "/api/v1/auth/login", "{}", "JSON vacío"),
            ("POST", "/api/v1/auth/login", '{"email": "test"}', "Solo email"),
            ("POST", "/api/v1/auth/login", '{"password": "test"}', "Solo password"),
            ("POST", "/api/v1/auth/login", '{"email": "test@test.com", "password": "test"}', "Credenciales de prueba"),
            ("POST", "/api/v1/auth/login", '{"email": "itmaster@rapicreditca.com", "password": "R@pi_2025**"}', "Credenciales reales")
        ]
        
        for metodo, endpoint, data, descripcion in variaciones_auth:
            try:
                response = requests.post(f"{BASE_URL}{endpoint}", json=json.loads(data), timeout=10)
                print(f"   {descripcion}: {response.status_code}")
                if response.status_code == 503:
                    print(f"      Error: {response.text}")
                elif response.status_code == 401:
                    print(f"      Unauthorized (esperado para credenciales incorrectas)")
                elif response.status_code == 422:
                    print(f"      Validation Error (esperado para datos incompletos)")
                elif response.status_code == 200:
                    print(f"      ✅ LOGIN EXITOSO!")
                    
            except Exception as e:
                print(f"   {descripcion}: ERROR - {e}")
        
        # 3. Verificar si el problema es específico del módulo auth
        print("\n3. VERIFICACIÓN DE MÓDULOS ESPECÍFICOS:")
        
        # Probar endpoints que NO requieren auth
        endpoints_sin_auth = [
            "/api/v1/clientes/ping",
            "/api/v1/validadores/ping",
            "/api/v1/carga-masiva/ping"
        ]
        
        for endpoint in endpoints_sin_auth:
            try:
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
                print(f"   {endpoint}: {response.status_code}")
                if response.status_code == 200:
                    print(f"      ✅ Funcionando")
                elif response.status_code == 404:
                    print(f"      ❌ No existe")
                else:
                    print(f"      ⚠️  Status inesperado")
                    
            except Exception as e:
                print(f"   {endpoint}: ERROR - {e}")
        
        # 4. Verificar si el problema es de base de datos
        print("\n4. VERIFICACIÓN DE BASE DE DATOS:")
        
        # Probar endpoints que requieren DB pero no auth
        try:
            response = requests.get(f"{BASE_URL}/api/v1/clientes/count", timeout=10)
            print(f"   /api/v1/clientes/count: {response.status_code}")
            if response.status_code == 403:
                print(f"      ⚠️  Requiere autenticación (esperado)")
            elif response.status_code == 200:
                print(f"      ✅ Base de datos funcionando")
            elif response.status_code == 503:
                print(f"      ❌ Error de base de datos: {response.text}")
                
        except Exception as e:
            print(f"   Error verificando DB: {e}")
        
        # 5. Análisis de timing
        print("\n5. ANÁLISIS DE TIMING:")
        
        tiempos = []
        for i in range(3):
            try:
                start_time = time.time()
                response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={}, timeout=15)
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
                print(f"   ⚠️  TIMEOUT: El servidor está tardando mucho en responder")
            elif tiempo_promedio > 5:
                print(f"   ⚠️  LENTO: El servidor está respondiendo lentamente")
            else:
                print(f"   ✅ RÁPIDO: El servidor responde rápidamente")
        
        # 6. Conclusiones
        print("\n=== CONCLUSIONES DEL SEGUNDO ENFOQUE ===")
        print("Si TODOS los endpoints dan 503, el problema es del servidor completo.")
        print("Si SOLO auth da 503, el problema es específico del módulo de autenticación.")
        print("Si auth da 503 pero otros endpoints funcionan, el problema es de dependencias.")
        print("Si el tiempo de respuesta es >10s, el problema es de recursos del servidor.")
        
    except Exception as e:
        print(f"Error en segundo enfoque: {e}")

if __name__ == "__main__":
    segundo_enfoque_diagnostico()
