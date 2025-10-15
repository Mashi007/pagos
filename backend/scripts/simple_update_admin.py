# backend/scripts/simple_update_admin.py
"""
Script simple para actualizar el administrador del sistema
Usa conexión directa a la base de datos
"""
import os
import sys
import psycopg2
from datetime import datetime
import hashlib
import secrets

# Configuración de la base de datos desde variables de entorno
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://pagos_admin:password@localhost/pagos_db')

def hash_password(password: str) -> str:
    """Hash de contraseña simple usando bcrypt"""
    import bcrypt
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def update_admin_system():
    """Actualizar administrador del sistema"""
    try:
        print("\n" + "="*70)
        print("🔧 ACTUALIZACIÓN DEL SISTEMA DE USUARIOS")
        print("="*70 + "\n")
        
        # Conectar a la base de datos
        print("🔌 Conectando a la base de datos...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # 1. Eliminar todos los usuarios existentes
        print("🗑️  ELIMINANDO USUARIOS EXISTENTES...")
        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
        print(f"   📊 Usuarios encontrados: {count}")
        
        if count > 0:
            cur.execute("DELETE FROM users")
            print("   ✅ Todos los usuarios eliminados")
        else:
            print("   ℹ️  No hay usuarios existentes")
        
        # 2. Crear nuevo administrador del sistema
        print("\n👑 CREANDO NUEVO ADMINISTRADOR DEL SISTEMA...")
        
        # Hash de la contraseña (usando método simple para este script)
        password_hash = hash_password("R@pi_2025**")
        
        # Insertar nuevo administrador
        cur.execute("""
            INSERT INTO users (email, nombre, apellido, hashed_password, rol, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            "itmaster@rapicreditca.com",
            "IT",
            "Master", 
            password_hash,
            "ADMINISTRADOR_GENERAL",
            True,
            datetime.utcnow()
        ))
        
        conn.commit()
        print("✅ Administrador del sistema creado exitosamente\n")
        
        # 3. Verificar creación
        cur.execute("SELECT COUNT(*) FROM users")
        total_usuarios = cur.fetchone()[0]
        print(f"🔍 VERIFICACIÓN: Total usuarios: {total_usuarios}")
        
        if total_usuarios == 1:
            print("✅ Sistema actualizado correctamente")
        else:
            print("❌ Error en la actualización")
        
        # 4. Mostrar información
        print("\n📋 CREDENCIALES DEL ADMINISTRADOR DEL SISTEMA:")
        print("   📧 Email:    itmaster@rapicreditca.com")
        print("   🔒 Password: R@pi_2025**")
        print("   👤 Nombre:   IT Master")
        print("   🎭 Rol:      ADMINISTRADOR_GENERAL")
        print("   ✓  Activo:   Sí")
        
        print("\n🌐 INFORMACIÓN DE ACCESO:")
        print("   🏠 URL del sistema: https://pagos-f2qf.onrender.com")
        print("   📖 Documentación: https://pagos-f2qf.onrender.com/docs")
        print("   🔐 Endpoint de login: POST /api/v1/auth/login")
        
        print("\n🧪 PRUEBA DE LOGIN:")
        print("   curl -X POST 'https://pagos-f2qf.onrender.com/api/v1/auth/login' \\")
        print("        -H 'Content-Type: application/json' \\")
        print('        -d \'{"email":"itmaster@rapicreditca.com","password":"R@pi_2025**"}\'')
        
        print("\n⚠️  IMPORTANTE:")
        print("   1. 🔐 Estas son las únicas credenciales válidas")
        print("   2. 🚫 Solo usuarios registrados pueden acceder")
        print("   3. 🛡️  Sistema completamente protegido")
        
        print("\n" + "="*70 + "\n")
        
        cur.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error actualizando sistema: {e}\n")
        return False


if __name__ == "__main__":
    print("🚀 INICIANDO ACTUALIZACIÓN DEL SISTEMA DE USUARIOS")
    
    success = update_admin_system()
    
    if success:
        print("✅ SISTEMA ACTUALIZADO EXITOSAMENTE")
    else:
        print("❌ ERROR EN LA ACTUALIZACIÓN DEL SISTEMA")
