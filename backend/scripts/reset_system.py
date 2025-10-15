# backend/scripts/reset_system.py
"""
Script para resetear el sistema de usuarios usando el endpoint de administración
"""
import requests
import json
import sys

# URL del sistema
BASE_URL = "https://pagos-f2qf.onrender.com"
LOGIN_URL = f"{BASE_URL}/api/v1/auth/login"
RESET_URL = f"{BASE_URL}/api/v1/admin-system/reset-admin-system"
STATUS_URL = f"{BASE_URL}/api/v1/admin-system/system-status"

def login_admin():
    """Hacer login como administrador"""
    try:
        # Primero intentar con las credenciales actuales
        credentials = [
            {"email": "admin@financiamiento.com", "password": "Admin2025!"},
            {"email": "admin@sistema.com", "password": "Admin123!"},
            {"email": "itmaster@rapicreditca.com", "password": "R@pi_2025**"}
        ]
        
        for cred in credentials:
            try:
                response = requests.post(LOGIN_URL, json=cred)
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Login exitoso con: {cred['email']}")
                    return data["access_token"]
            except:
                continue
        
        print("❌ No se pudo hacer login con ninguna credencial")
        return None
        
    except Exception as e:
        print(f"❌ Error en login: {e}")
        return None

def reset_admin_system(token):
    """Resetear el sistema de usuarios"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(RESET_URL, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Sistema reseteado exitosamente")
            print(f"📧 Nuevo administrador: {data['admin_created']['email']}")
            print(f"👤 Nombre: {data['admin_created']['nombre']}")
            print(f"🎭 Rol: {data['admin_created']['rol']}")
            print(f"👥 Total usuarios: {data['total_users']}")
            return True
        else:
            print(f"❌ Error reseteando sistema: {response.status_code}")
            print(f"   {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error en reset: {e}")
        return False

def verify_system_status(token):
    """Verificar estado del sistema"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(STATUS_URL, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print("\n🔍 ESTADO DEL SISTEMA:")
            print(f"   👥 Total usuarios: {data['total_users']}")
            print(f"   🔐 Sistema seguro: {data['system_secure']}")
            print(f"   👑 Admin activo: {data['admin_active']['exists']}")
            
            if data['admin_active']['exists']:
                print(f"   📧 Email admin: {data['admin_active']['email']}")
                print(f"   👤 Nombre admin: {data['admin_active']['name']}")
            
            return data['system_secure']
        else:
            print(f"❌ Error verificando estado: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error verificando estado: {e}")
        return False

def main():
    """Función principal"""
    print("\n" + "="*70)
    print("🔧 RESETEO DEL SISTEMA DE USUARIOS")
    print("="*70 + "\n")
    
    # 1. Hacer login
    print("🔐 Intentando login...")
    token = login_admin()
    
    if not token:
        print("❌ No se pudo obtener token de acceso")
        print("   El sistema puede estar sin usuarios o con credenciales incorrectas")
        return
    
    # 2. Resetear sistema
    print("\n🗑️  Reseteando sistema de usuarios...")
    success = reset_admin_system(token)
    
    if not success:
        print("❌ No se pudo resetear el sistema")
        return
    
    # 3. Verificar estado
    print("\n🔍 Verificando estado final...")
    verify_system_status(token)
    
    # 4. Mostrar credenciales finales
    print("\n📋 CREDENCIALES FINALES DEL SISTEMA:")
    print("   📧 Email:    itmaster@rapicreditca.com")
    print("   🔒 Password: R@pi_2025**")
    print("   👤 Nombre:   IT Master")
    print("   🎭 Rol:      ADMINISTRADOR_GENERAL")
    
    print("\n🌐 INFORMACIÓN DE ACCESO:")
    print("   🏠 URL: https://pagos-f2qf.onrender.com")
    print("   📖 Docs: https://pagos-f2qf.onrender.com/docs")
    print("   🔐 Login: POST /api/v1/auth/login")
    
    print("\n🧪 PRUEBA DE LOGIN:")
    print("   curl -X POST 'https://pagos-f2qf.onrender.com/api/v1/auth/login' \\")
    print("        -H 'Content-Type: application/json' \\")
    print('        -d \'{"email":"itmaster@rapicreditca.com","password":"R@pi_2025**"}\'')
    
    print("\n✅ SISTEMA RESETEADO EXITOSAMENTE")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
