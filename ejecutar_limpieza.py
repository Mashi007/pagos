"""
Script para ejecutar limpieza en producción
"""
import requests
import json

def ejecutar_limpieza():
    """Ejecutar limpieza en la base de datos de producción"""
    
    base_url = "https://pagos-f2qf.onrender.com/api/v1/clean"
    
    print("🔍 Verificando estado actual del sistema...")
    
    try:
        # 1. Verificar estado actual
        response = requests.get(f"{base_url}/system-status")
        
        if response.status_code == 200:
            data = response.json()
            print("📊 Estado actual:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"❌ Error verificando estado: {response.status_code}")
            return False
            
        print("\n🧹 Ejecutando limpieza...")
        
        # 2. Ejecutar limpieza
        response = requests.post(f"{base_url}/clean-admin-users")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Limpieza ejecutada exitosamente:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # Mostrar credenciales
            if "login_credentials" in data:
                creds = data["login_credentials"]
                print(f"\n🔑 Credenciales para login:")
                print(f"   Email: {creds['email']}")
                print(f"   Password: {creds['password']}")
                print(f"   Rol: {creds['role']}")
                
            return True
        else:
            print(f"❌ Error ejecutando limpieza: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Ejecutando limpieza definitiva en producción...")
    success = ejecutar_limpieza()
    
    if success:
        print("\n🎉 LIMPIEZA COMPLETADA")
        print("✅ Sistema listo para login con:")
        print("   Email: itmaster@rapicreditca.com")
        print("   Password: R@pi_2025**")
    else:
        print("\n❌ Error en la limpieza")
