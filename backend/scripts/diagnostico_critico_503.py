#!/usr/bin/env python3
"""
Script de diagnóstico crítico para error 503 en auth
"""
import requests
import json
import sys
import os

# Agregar el directorio del proyecto al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "https://pagos-f2qf.onrender.com"

def diagnostico_critico():
    """Diagnóstico completo del error 503"""
    print("=== DIAGNÓSTICO CRÍTICO - ERROR 503 EN AUTH ===")
    
    try:
        # 1. Verificar conectividad básica
        print("\n1. Verificando conectividad básica...")
        try:
            response = requests.get(f"{BASE_URL}/", timeout=10)
            print(f"   Status: {response.status_code}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # 2. Verificar endpoint de clientes (que funciona)
        print("\n2. Verificando endpoint de clientes...")
        try:
            response = requests.get(f"{BASE_URL}/api/v1/clientes/ping", timeout=10)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Respuesta: {response.json()}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # 3. Verificar endpoint de auth con GET (debería dar 405)
        print("\n3. Verificando endpoint de auth con GET...")
        try:
            response = requests.get(f"{BASE_URL}/api/v1/auth/login", timeout=10)
            print(f"   Status: {response.status_code}")
            if response.status_code != 405:
                print(f"   Respuesta: {response.text}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # 4. Verificar endpoint de auth con POST (debería dar 422 o 401, no 503)
        print("\n4. Verificando endpoint de auth con POST...")
        try:
            response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={}, timeout=10)
            print(f"   Status: {response.status_code}")
            print(f"   Respuesta: {response.text}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # 5. Verificar endpoint de auth con datos válidos
        print("\n5. Verificando endpoint de auth con datos válidos...")
        try:
            login_data = {
                "email": "itmaster@rapicreditca.com",
                "password": "R@pi_2025**"
            }
            response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data, timeout=10)
            print(f"   Status: {response.status_code}")
            if response.status_code == 503:
                print(f"   ERROR 503 CONFIRMADO!")
                print(f"   Respuesta: {response.text}")
            elif response.status_code == 200:
                print(f"   Login exitoso!")
            else:
                print(f"   Respuesta: {response.text}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # 6. Verificar otros endpoints críticos
        print("\n6. Verificando otros endpoints críticos...")
        endpoints = [
            "/api/v1/auth/me",
            "/api/v1/usuarios/",
            "/api/v1/validadores/ping"
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
                print(f"   {endpoint}: {response.status_code}")
            except Exception as e:
                print(f"   {endpoint}: Error - {e}")
        
        print("\n=== RESUMEN DEL DIAGNÓSTICO ===")
        print("Si el endpoint de clientes funciona (200) pero auth da 503,")
        print("el problema está específicamente en el módulo de autenticación.")
        print("Posibles causas:")
        print("1. Error en imports de auditoría")
        print("2. Error en security_audit.py")
        print("3. Error en auditoria_helper.py")
        print("4. Error en dependencias de auth")
        
    except Exception as e:
        print(f"Error en diagnóstico: {e}")

if __name__ == "__main__":
    diagnostico_critico()
