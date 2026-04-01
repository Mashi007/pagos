#!/usr/bin/env python3
"""
Script para recuperar acceso - Crea usuario admin de emergencia en la BD
Uso: python recuperar_acceso.py
"""
import os
import sys

def obtener_credenciales_render():
    """Pide credenciales de conexión a Render."""
    print("\n" + "="*70)
    print("  RECUPERACIÓN DE ACCESO - CREAR ADMIN")
    print("="*70)
    
    print("\n📍 Necesitas la URL de conexión a PostgreSQL en Render")
    print("   Encuentra en: Dashboard Render → Base de datos → Internal Database URL")
    
    database_url = input("\n🔗 Pega aquí la DATABASE_URL: ").strip()
    
    if not database_url or "postgresql" not in database_url:
        print("❌ URL inválida. Debe comenzar con postgresql://")
        return None
    
    return database_url

def conectar_bd(database_url):
    """Conecta a la BD de Render."""
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        # Parsear URL
        parsed = urlparse(database_url)
        
        conexion = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path.lstrip('/'),
            user=parsed.username,
            password=parsed.password,
            sslmode='require'
        )
        
        print("✅ Conectado a Render PostgreSQL")
        return conexion
        
    except ImportError:
        print("❌ Falta instalar psycopg2")
        print("   Ejecuta: pip install psycopg2-binary")
        return None
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return None

def generar_hash_bcrypt(password):
    """Genera hash bcrypt para el password."""
    try:
        from app.core.security import get_password_hash
        return get_password_hash(password)
    except ImportError:
        print("❌ No se puede importar get_password_hash")
        print("   Asegúrate de estar en la carpeta backend con los requirements instalados")
        return None

def crear_admin_directo(conexion, email, cedula, nombre, password_hash):
    """Crea usuario admin directamente en la BD."""
    try:
        cursor = conexion.cursor()
        
        # Verificar si email ya existe
        cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email.lower(),))
        if cursor.fetchone():
            print(f"⚠️  Email {email} ya existe en la BD")
            cursor.close()
            return False
        
        # Verificar si cedula ya existe
        cursor.execute("SELECT id FROM usuarios WHERE cedula = %s", (cedula,))
        if cursor.fetchone():
            print(f"⚠️  Cédula {cedula} ya existe en la BD")
            cursor.close()
            return False
        
        # Insertar usuario admin
        sql = """
        INSERT INTO usuarios (
            email,
            cedula,
            password_hash,
            nombre,
            rol,
            is_active,
            created_at,
            updated_at
        ) VALUES (%s, %s, %s, %s, %s, true, NOW(), NOW())
        RETURNING id;
        """
        
        cursor.execute(sql, (
            email.lower(),
            cedula,
            password_hash,
            nombre,
            'admin'
        ))
        
        user_id = cursor.fetchone()[0]
        conexion.commit()
        cursor.close()
        
        print(f"\n✅ Usuario admin creado exitosamente!")
        print(f"   ID: {user_id}")
        print(f"   Email: {email.lower()}")
        print(f"   Nombre: {nombre}")
        print(f"   Rol: admin")
        
        return True
        
    except Exception as e:
        conexion.rollback()
        print(f"❌ Error al crear usuario: {e}")
        return False

def main():
    """Función principal."""
    try:
        # Obtener credenciales
        database_url = obtener_credenciales_render()
        if not database_url:
            return
        
        # Conectar a BD
        conexion = conectar_bd(database_url)
        if not conexion:
            return
        
        # Datos del admin
        print("\n" + "="*70)
        print("  DATOS DEL ADMIN DE RECUPERACIÓN")
        print("="*70)
        
        email = input("\n📧 Email del admin (ej: admin@empresa.com): ").strip().lower()
        if not email or "@" not in email:
            print("❌ Email inválido")
            conexion.close()
            return
        
        cedula = input("🆔 Cédula (ej: 99999999-9): ").strip()
        if not cedula:
            print("❌ Cédula requerida")
            conexion.close()
            return
        
        nombre = input("👤 Nombre completo (ej: Admin Sistema): ").strip()
        if not nombre:
            print("❌ Nombre requerido")
            conexion.close()
            return
        
        password = input("🔑 Password (mínimo 6 caracteres): ").strip()
        if len(password) < 6:
            print("❌ Password debe tener al menos 6 caracteres")
            conexion.close()
            return
        
        # Generar hash
        print("\n🔐 Generando hash bcrypt...")
        password_hash = generar_hash_bcrypt(password)
        
        if not password_hash:
            print("❌ No se pudo generar hash")
            conexion.close()
            return
        
        # Crear usuario
        if crear_admin_directo(conexion, email, cedula, nombre, password_hash):
            print("\n" + "="*70)
            print("  ✅ ¡ACCESO RECUPERADO!")
            print("="*70)
            print(f"""
Ya puedes ingresar con:
  Email: {email}
  Password: {password}

⚠️  CAMBIA ESTE PASSWORD INMEDIATAMENTE después de ingresar:
    Menu → Perfil/Usuarios → Cambiar Password
""")
        else:
            print("\n❌ No se pudo crear el usuario")
        
        conexion.close()
        
    except KeyboardInterrupt:
        print("\n\n❌ Operación cancelada")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
