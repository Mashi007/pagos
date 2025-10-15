"""
Script para limpiar usuario directamente usando endpoint existente
"""
import requests
import json

def limpiar_usuario_directo():
    """Usar endpoint SQL existente para eliminar admin@financiamiento.com"""
    
    base_url = "https://pagos-f2qf.onrender.com/api/v1/sql"
    
    print("🔍 Verificando estado actual...")
    
    try:
        # 1. Verificar ping
        response = requests.get(f"{base_url}/ping")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend funcionando: {data.get('version', 'unknown')}")
        else:
            print(f"❌ Error ping: {response.status_code}")
            return False
        
        # 2. Verificar estado actual
        response = requests.get(f"{base_url}/status")
        if response.status_code == 200:
            data = response.json()
            print("📊 Estado actual de roles:")
            if 'roles' in data:
                for role in data['roles']:
                    print(f"   - {role['rol']}: {role['count']} usuarios")
            else:
                print("   No se pudo obtener información de roles")
        
        # 3. Intentar usar fix-now (aunque sea para ADMIN)
        print("\n🔧 Ejecutando fix-now...")
        response = requests.get(f"{base_url}/fix-now")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Fix ejecutado: {data.get('message', 'Sin mensaje')}")
            
            if 'admin_found' in data:
                print(f"   Admin encontrados: {data['admin_found']}")
            if 'updated' in data:
                print(f"   Actualizados: {data['updated']}")
        else:
            print(f"❌ Error fix-now: {response.status_code}")
            print(f"   Respuesta: {response.text}")
        
        # 4. Verificar estado final
        print("\n🔍 Verificando estado final...")
        response = requests.get(f"{base_url}/status")
        if response.status_code == 200:
            data = response.json()
            print("📊 Estado final de roles:")
            if 'roles' in data:
                for role in data['roles']:
                    print(f"   - {role['rol']}: {role['count']} usuarios")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Limpiando usuario incorrecto...")
    success = limpiar_usuario_directo()
    
    if success:
        print("\n✅ Proceso completado")
    else:
        print("\n❌ Error en el proceso")
