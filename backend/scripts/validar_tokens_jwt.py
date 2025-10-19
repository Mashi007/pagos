#!/usr/bin/env python3
"""
Script de validación alternativa para verificar causa raíz de errores 401
Valida tokens JWT directamente sin depender del frontend
"""

import os
import sys
import requests
import json
from datetime import datetime, timedelta
import jwt
from typing import Dict, Any

# Configuración
BASE_URL = "https://pagos-f2qf.onrender.com"
TEST_EMAIL = "itmaster@rapicreditca.com"
TEST_PASSWORD = "admin123"  # Cambiar por la contraseña real

def test_login_endpoint():
    """Probar endpoint de login directamente"""
    print("🔐 PROBANDO ENDPOINT DE LOGIN...")
    
    login_url = f"{BASE_URL}/api/v1/auth/login"
    login_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    
    try:
        response = requests.post(login_url, json=login_data, timeout=10)
        print(f"📊 Status Code: {response.status_code}")
        print(f"📊 Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Login exitoso!")
            print(f"📝 Access Token: {data.get('access_token', 'NO_TOKEN')[:50]}...")
            print(f"📝 Refresh Token: {data.get('refresh_token', 'NO_TOKEN')[:50]}...")
            return data
        else:
            print(f"❌ Login falló: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error en login: {e}")
        return None

def test_protected_endpoint(token: str, endpoint: str):
    """Probar endpoint protegido con token"""
    print(f"\n🔒 PROBANDO ENDPOINT PROTEGIDO: {endpoint}")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=10)
        print(f"📊 Status Code: {response.status_code}")
        print(f"📊 Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print(f"✅ Endpoint accesible!")
            try:
                data = response.json()
                print(f"📝 Datos recibidos: {len(str(data))} caracteres")
            except:
                print(f"📝 Respuesta no JSON: {response.text[:200]}...")
        else:
            print(f"❌ Endpoint falló: {response.text[:200]}...")
            
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Error en endpoint: {e}")
        return False

def validate_jwt_token(token: str):
    """Validar estructura del token JWT"""
    print(f"\n🔍 VALIDANDO ESTRUCTURA DEL TOKEN JWT...")
    
    try:
        # Decodificar sin verificar (solo para ver estructura)
        decoded = jwt.decode(token, options={"verify_signature": False})
        print(f"✅ Token JWT válido estructuralmente")
        print(f"📝 Payload: {json.dumps(decoded, indent=2)}")
        
        # Verificar expiración
        exp = decoded.get('exp')
        if exp:
            exp_date = datetime.fromtimestamp(exp)
            now = datetime.now()
            if exp_date > now:
                print(f"✅ Token no expirado (expira: {exp_date})")
            else:
                print(f"❌ Token expirado (expiró: {exp_date})")
        
        return True
        
    except Exception as e:
        print(f"❌ Token JWT inválido: {e}")
        return False

def test_cors_headers():
    """Probar headers CORS"""
    print(f"\n🌐 PROBANDO HEADERS CORS...")
    
    try:
        # OPTIONS request para probar CORS
        response = requests.options(f"{BASE_URL}/api/v1/auth/me", timeout=10)
        print(f"📊 OPTIONS Status: {response.status_code}")
        print(f"📊 CORS Headers:")
        
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
            'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials')
        }
        
        for header, value in cors_headers.items():
            print(f"  {header}: {value}")
            
    except Exception as e:
        print(f"❌ Error probando CORS: {e}")

def main():
    """Función principal de validación"""
    print("🚀 INICIANDO VALIDACIÓN ALTERNATIVA DE CAUSA RAÍZ")
    print("=" * 60)
    
    # 1. Probar login
    login_result = test_login_endpoint()
    if not login_result:
        print("\n❌ CRÍTICO: Login falló - problema en autenticación básica")
        return
    
    access_token = login_result.get('access_token')
    if not access_token:
        print("\n❌ CRÍTICO: No se recibió access_token")
        return
    
    # 2. Validar estructura del token
    validate_jwt_token(access_token)
    
    # 3. Probar endpoints protegidos
    endpoints_to_test = [
        "/api/v1/auth/me",
        "/api/v1/usuarios/?page=1&page_size=100",
        "/api/v1/clientes/?page=1&per_page=20"
    ]
    
    success_count = 0
    for endpoint in endpoints_to_test:
        if test_protected_endpoint(access_token, endpoint):
            success_count += 1
    
    # 4. Probar CORS
    test_cors_headers()
    
    # 5. Resumen
    print(f"\n📊 RESUMEN DE VALIDACIÓN:")
    print(f"✅ Endpoints exitosos: {success_count}/{len(endpoints_to_test)}")
    
    if success_count == len(endpoints_to_test):
        print("🎯 CONCLUSIÓN: Backend funcionando correctamente - problema en frontend")
    elif success_count == 0:
        print("🎯 CONCLUSIÓN: Problema crítico en backend - tokens no válidos")
    else:
        print("🎯 CONCLUSIÓN: Problema parcial - algunos endpoints fallan")

if __name__ == "__main__":
    main()
