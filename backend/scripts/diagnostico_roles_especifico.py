#!/usr/bin/env python3
"""
Script para diagnosticar el problema de roles específicamente
"""

import requests
import json
from datetime import datetime

# Configuración
BASE_URL = "https://pagos-f2qf.onrender.com"

def test_login_and_user_data():
    """Probar login y verificar datos del usuario"""
    print(f"\n{'='*60}")
    print("DIAGNOSTICO ESPECIFICO DE ROLES")
    print(f"{'='*60}")
    
    # Datos de login
    login_data = {
        "email": "itmaster@rapicreditca.com",
        "password": "R@pi_2025**",
        "remember": True
    }
    
    try:
        print("1. PROBANDO LOGIN...")
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=login_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("   ✅ LOGIN EXITOSO")
            print(f"   Token: {data.get('access_token', 'No token')[:50]}...")
            
            # Verificar datos del usuario
            user = data.get('user', {})
            print(f"\n2. DATOS DEL USUARIO:")
            print(f"   ID: {user.get('id', 'No ID')}")
            print(f"   Email: {user.get('email', 'No email')}")
            print(f"   Nombre: {user.get('nombre', 'No nombre')}")
            print(f"   Apellido: {user.get('apellido', 'No apellido')}")
            print(f"   ROL: {user.get('rol', 'No rol')}")
            print(f"   Activo: {user.get('is_active', 'No activo')}")
            
            # Verificar token
            token = data.get('access_token')
            if token:
                print(f"\n3. PROBANDO ENDPOINT /auth/me...")
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
                
                me_response = requests.get(
                    f"{BASE_URL}/api/v1/auth/me",
                    headers=headers,
                    timeout=30
                )
                
                print(f"   Status Code: {me_response.status_code}")
                
                if me_response.status_code == 200:
                    me_data = me_response.json()
                    print("   ✅ ENDPOINT /auth/me EXITOSO")
                    print(f"   Datos completos: {json.dumps(me_data, indent=2, ensure_ascii=False)}")
                else:
                    print("   ❌ ENDPOINT /auth/me FALLA")
                    print(f"   Error: {me_response.text}")
            
            # Probar endpoint de usuarios
            print(f"\n4. PROBANDO ENDPOINT /users...")
            users_response = requests.get(
                f"{BASE_URL}/api/v1/users",
                headers=headers,
                timeout=30
            )
            
            print(f"   Status Code: {users_response.status_code}")
            
            if users_response.status_code == 200:
                users_data = users_response.json()
                print("   ✅ ENDPOINT /users EXITOSO")
                print(f"   Usuarios: {json.dumps(users_data, indent=2, ensure_ascii=False)}")
            else:
                print("   ❌ ENDPOINT /users FALLA")
                print(f"   Error: {users_response.text}")
                
        else:
            print("   ❌ LOGIN FALLA")
            print(f"   Error: {response.text}")
            
    except Exception as e:
        print(f"   ❌ ERROR GENERAL: {e}")

def main():
    """Función principal"""
    print("DIAGNOSTICO ESPECIFICO DE PROBLEMA DE ROLES")
    print(f"Base URL: {BASE_URL}")
    print(f"Timestamp: {datetime.now()}")
    
    test_login_and_user_data()
    
    print(f"\n{'='*60}")
    print("DIAGNOSTICO COMPLETADO")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
