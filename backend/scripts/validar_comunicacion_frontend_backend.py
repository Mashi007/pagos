#!/usr/bin/env python3
"""
Script de validación de comunicación frontend-backend
Simula requests del frontend para identificar problemas de comunicación
"""

import os
import sys
import requests
import json
from datetime import datetime, timedelta
import jwt
from typing import Dict, Any

# Configuración
BACKEND_URL = "https://pagos-f2qf.onrender.com"
FRONTEND_URL = "https://rapicredit.onrender.com"

def simulate_frontend_request():
    """Simular request del frontend con headers reales"""
    print("🌐 SIMULANDO REQUEST DEL FRONTEND...")
    
    # Headers que enviaría el frontend real
    frontend_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Origin': FRONTEND_URL,
        'Referer': f'{FRONTEND_URL}/clientes',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    
    # 1. Probar login
    print("\n🔐 PROBANDO LOGIN...")
    login_data = {
        "email": "itmaster@rapicreditca.com",
        "password": "admin123"  # Cambiar por la contraseña real
    }
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/auth/login",
            json=login_data,
            headers=frontend_headers,
            timeout=10
        )
        
        print(f"📊 Login Status: {response.status_code}")
        print(f"📊 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get('access_token')
            print(f"✅ Login exitoso - Token recibido")
            return access_token
        else:
            print(f"❌ Login falló: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error en login: {e}")
        return None

def test_protected_endpoints_with_token(token: str):
    """Probar endpoints protegidos con token"""
    print(f"\n🔒 PROBANDO ENDPOINTS PROTEGIDOS CON TOKEN...")
    
    # Headers con token
    auth_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Origin': FRONTEND_URL,
        'Referer': f'{FRONTEND_URL}/clientes',
        'Authorization': f'Bearer {token}',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    
    # Endpoints que fallan según los logs
    failing_endpoints = [
        "/api/v1/auth/me",
        "/api/v1/usuarios/?page=1&page_size=100",
        "/api/v1/clientes/?page=1&per_page=20"
    ]
    
    success_count = 0
    for endpoint in failing_endpoints:
        try:
            print(f"\n🔍 Probando: {endpoint}")
            response = requests.get(
                f"{BACKEND_URL}{endpoint}",
                headers=auth_headers,
                timeout=10
            )
            
            print(f"📊 Status: {response.status_code}")
            print(f"📊 Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                print(f"✅ Endpoint accesible!")
                try:
                    data = response.json()
                    print(f"📝 Datos: {len(str(data))} caracteres")
                except:
                    print(f"📝 Respuesta no JSON")
                success_count += 1
            elif response.status_code == 401:
                print(f"❌ 401 Unauthorized - Token inválido o expirado")
                print(f"📝 Respuesta: {response.text[:200]}...")
            else:
                print(f"❌ Error {response.status_code}: {response.text[:200]}...")
                
        except Exception as e:
            print(f"❌ Error en request: {e}")
    
    return success_count, len(failing_endpoints)

def test_cors_preflight():
    """Probar CORS preflight requests"""
    print(f"\n🌐 PROBANDO CORS PREFLIGHT...")
    
    cors_headers = {
        'Access-Control-Request-Method': 'GET',
        'Access-Control-Request-Headers': 'Authorization, Content-Type',
        'Origin': FRONTEND_URL
    }
    
    try:
        response = requests.options(
            f"{BACKEND_URL}/api/v1/auth/me",
            headers=cors_headers,
            timeout=10
        )
        
        print(f"📊 OPTIONS Status: {response.status_code}")
        print(f"📊 CORS Headers:")
        
        cors_response_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
            'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials'),
            'Access-Control-Max-Age': response.headers.get('Access-Control-Max-Age')
        }
        
        for header, value in cors_response_headers.items():
            status = "✅" if value else "❌"
            print(f"  {header}: {value} {status}")
            
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Error en CORS preflight: {e}")
        return False

def analyze_token_structure(token: str):
    """Analizar estructura del token"""
    print(f"\n🔍 ANALIZANDO ESTRUCTURA DEL TOKEN...")
    
    try:
        # Decodificar sin verificar
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        print(f"✅ Token decodificado exitosamente")
        print(f"📝 Payload completo:")
        print(json.dumps(decoded, indent=2))
        
        # Verificar campos importantes
        required_fields = ['sub', 'exp', 'iat', 'email']
        missing_fields = [field for field in required_fields if field not in decoded]
        
        if missing_fields:
            print(f"❌ Campos faltantes: {missing_fields}")
        else:
            print(f"✅ Todos los campos requeridos presentes")
        
        # Verificar expiración
        exp = decoded.get('exp')
        if exp:
            exp_date = datetime.fromtimestamp(exp)
            now = datetime.now()
            time_left = exp_date - now
            
            if time_left.total_seconds() > 0:
                print(f"✅ Token válido por {time_left}")
            else:
                print(f"❌ Token expirado hace {abs(time_left)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error decodificando token: {e}")
        return False

def main():
    """Función principal"""
    print("🔍 VALIDACIÓN ALTERNATIVA DE COMUNICACIÓN FRONTEND-BACKEND")
    print("=" * 70)
    
    # 1. Simular login del frontend
    token = simulate_frontend_request()
    if not token:
        print("\n❌ CRÍTICO: No se pudo obtener token - problema en autenticación")
        return
    
    # 2. Analizar estructura del token
    analyze_token_structure(token)
    
    # 3. Probar endpoints protegidos
    success_count, total_count = test_protected_endpoints_with_token(token)
    
    # 4. Probar CORS
    cors_ok = test_cors_preflight()
    
    # 5. Resumen y diagnóstico
    print(f"\n📊 RESUMEN DE VALIDACIÓN:")
    print(f"✅ Endpoints exitosos: {success_count}/{total_count}")
    print(f"✅ CORS configurado: {'Sí' if cors_ok else 'No'}")
    
    if success_count == total_count and cors_ok:
        print("🎯 CONCLUSIÓN: Backend funcionando correctamente")
        print("   El problema está en el frontend (token storage, interceptors, etc.)")
    elif success_count == 0:
        print("🎯 CONCLUSIÓN: Problema crítico en backend")
        print("   Los tokens no son válidos o hay problema en middleware de auth")
    else:
        print("🎯 CONCLUSIÓN: Problema parcial")
        print("   Algunos endpoints funcionan, otros no - revisar configuración específica")

if __name__ == "__main__":
    main()
