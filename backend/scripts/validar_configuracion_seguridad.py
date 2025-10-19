#!/usr/bin/env python3
"""
Script de validación de configuración de seguridad JWT
Verifica configuración del backend sin depender del frontend
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

def test_public_endpoints():
    """Probar endpoints públicos"""
    print("🌐 PROBANDO ENDPOINTS PÚBLICOS...")
    
    public_endpoints = [
        "/",
        "/docs",
        "/api/v1/auth/login",
        "/api/v1/analistas/activos",
        "/api/v1/concesionarios/activos",
        "/api/v1/modelos-vehiculos/activos"
    ]
    
    for endpoint in public_endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            print(f"  {endpoint}: {response.status_code} {'✅' if response.status_code in [200, 405] else '❌'}")
        except Exception as e:
            print(f"  {endpoint}: ERROR - {e}")

def test_auth_endpoints():
    """Probar endpoints de autenticación específicamente"""
    print("\n🔐 PROBANDO ENDPOINTS DE AUTENTICACIÓN...")
    
    auth_endpoints = [
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout"
    ]
    
    for endpoint in auth_endpoints:
        try:
            # Probar con POST (método correcto para login)
            if endpoint == "/api/v1/auth/login":
                response = requests.post(f"{BASE_URL}{endpoint}", json={}, timeout=10)
            else:
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            
            print(f"  {endpoint}: {response.status_code} {'✅' if response.status_code in [200, 401, 422] else '❌'}")
            
            if response.status_code == 401:
                print(f"    📝 Respuesta 401 esperada para endpoint protegido")
            elif response.status_code == 422:
                print(f"    📝 Respuesta 422 esperada para datos faltantes")
                
        except Exception as e:
            print(f"  {endpoint}: ERROR - {e}")

def test_cors_configuration():
    """Probar configuración CORS"""
    print("\n🌐 PROBANDO CONFIGURACIÓN CORS...")
    
    try:
        # Simular request desde frontend
        headers = {
            'Origin': 'https://rapicredit.onrender.com',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'Authorization, Content-Type'
        }
        
        response = requests.options(f"{BASE_URL}/api/v1/auth/me", headers=headers, timeout=10)
        print(f"📊 OPTIONS Status: {response.status_code}")
        
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
            'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials')
        }
        
        print("📊 Headers CORS encontrados:")
        for header, value in cors_headers.items():
            status = "✅" if value else "❌"
            print(f"  {header}: {value} {status}")
            
    except Exception as e:
        print(f"❌ Error probando CORS: {e}")

def test_token_generation():
    """Probar generación de tokens con credenciales válidas"""
    print("\n🎫 PROBANDO GENERACIÓN DE TOKENS...")
    
    # Credenciales de prueba (cambiar por las reales)
    test_credentials = [
        {"email": "itmaster@rapicreditca.com", "password": "admin123"},
        {"email": "admin@rapicreditca.com", "password": "admin123"},
        {"email": "test@rapicreditca.com", "password": "test123"}
    ]
    
    for creds in test_credentials:
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/auth/login",
                json=creds,
                timeout=10
            )
            
            print(f"  {creds['email']}: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                access_token = data.get('access_token')
                refresh_token = data.get('refresh_token')
                
                print(f"    ✅ Access Token: {'Presente' if access_token else 'Faltante'}")
                print(f"    ✅ Refresh Token: {'Presente' if refresh_token else 'Faltante'}")
                
                # Validar estructura del token
                if access_token:
                    try:
                        decoded = jwt.decode(access_token, options={"verify_signature": False})
                        print(f"    ✅ Token válido - exp: {decoded.get('exp')}")
                    except:
                        print(f"    ❌ Token inválido")
                        
            elif response.status_code == 401:
                print(f"    ❌ Credenciales inválidas")
            else:
                print(f"    ❌ Error: {response.text[:100]}...")
                
        except Exception as e:
            print(f"  {creds['email']}: ERROR - {e}")

def test_database_connectivity():
    """Probar conectividad a base de datos indirectamente"""
    print("\n🗄️ PROBANDO CONECTIVIDAD A BASE DE DATOS...")
    
    # Endpoints que requieren BD
    db_endpoints = [
        "/api/v1/analistas/activos",
        "/api/v1/concesionarios/activos", 
        "/api/v1/modelos-vehiculos/activos"
    ]
    
    for endpoint in db_endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            print(f"  {endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"    ✅ Datos recibidos: {len(data)} registros")
                except:
                    print(f"    ✅ Respuesta válida pero no JSON")
            elif response.status_code == 500:
                print(f"    ❌ Error interno del servidor - posible problema de BD")
            else:
                print(f"    ⚠️ Status inesperado")
                
        except Exception as e:
            print(f"  {endpoint}: ERROR - {e}")

def main():
    """Función principal de validación"""
    print("🔍 VALIDACIÓN ALTERNATIVA DE CONFIGURACIÓN DE SEGURIDAD")
    print("=" * 60)
    
    # 1. Probar endpoints públicos
    test_public_endpoints()
    
    # 2. Probar endpoints de autenticación
    test_auth_endpoints()
    
    # 3. Probar configuración CORS
    test_cors_configuration()
    
    # 4. Probar generación de tokens
    test_token_generation()
    
    # 5. Probar conectividad a BD
    test_database_connectivity()
    
    print("\n🎯 VALIDACIÓN COMPLETADA")
    print("Revisa los resultados para identificar la causa raíz del problema 401")

if __name__ == "__main__":
    main()
