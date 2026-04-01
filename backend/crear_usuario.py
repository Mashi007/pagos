#!/usr/bin/env python3
"""
Script interactivo para crear usuarios - te pregunta los datos y genera SQL.
Uso: python crear_usuario.py
"""
import sys
import re
from datetime import datetime

def normalizar_email(email):
    """Normaliza email a minúsculas."""
    return email.lower().strip()

def validar_email(email):
    """Valida formato de email."""
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(patron, email) is not None

def validar_cedula(cedula):
    """Valida que la cédula no esté vacía."""
    return len(cedula.strip()) > 0 and len(cedula.strip()) <= 50

def validar_nombre(nombre):
    """Valida que el nombre no esté vacío."""
    return len(nombre.strip()) > 0 and len(nombre.strip()) <= 255

def validar_password(password):
    """Valida que password tenga al menos 6 caracteres."""
    return len(password) >= 6

def validar_rol(rol):
    """Valida que el rol sea válido."""
    return rol in ['admin', 'manager', 'operator', 'viewer']

def hacer_pregunta(pregunta, validador, tipo='string'):
    """Hace una pregunta y valida la respuesta."""
    while True:
        try:
            respuesta = input(f"\n{pregunta}: ").strip()
            
            if not respuesta:
                print("❌ Campo obligatorio, no puede estar vacío")
                continue
            
            if not validador(respuesta):
                if tipo == 'email':
                    print("❌ Email inválido. Use formato: usuario@empresa.com")
                elif tipo == 'password':
                    print("❌ Password debe tener al menos 6 caracteres")
                elif tipo == 'cedula':
                    print("❌ Cédula debe tener 1-50 caracteres")
                elif tipo == 'nombre':
                    print("❌ Nombre debe tener 1-255 caracteres")
                elif tipo == 'rol':
                    print("❌ Rol inválido. Debe ser: admin, manager, operator o viewer")
                continue
            
            return respuesta
        except KeyboardInterrupt:
            print("\n\n❌ Operación cancelada")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error: {e}")

def generar_hash_password(password):
    """
    Genera un hash de password usando bcrypt.
    NOTA: Para uso real, ejecutar el hash en Python:
    python -c "from app.core.security import get_password_hash; print(get_password_hash('PASSWORD'))"
    """
    print("\n⚠️  IMPORTANTE: El password debe ser hasheado con bcrypt")
    print("   Ejecuta esto en terminal Python:")
    print(f"   python -c \"from app.core.security import get_password_hash; print(get_password_hash('{password}'))\"")
    
    hash_password = input("\nPega aquí el hash generado: ").strip()
    if not hash_password or len(hash_password) < 50:
        print("❌ Hash inválido o incompleto")
        return generar_hash_password(password)
    
    return hash_password

def preguntar_usuarios():
    """Pregunta interactivamente por los usuarios."""
    usuarios = []
    
    print("\n" + "="*70)
    print("  CREAR USUARIO - FORMULARIO INTERACTIVO")
    print("="*70)
    
    while True:
        print(f"\n--- USUARIO #{len(usuarios) + 1} ---")
        
        # Email
        email = hacer_pregunta(
            "📧 Email (ej: usuario@empresa.com)",
            validar_email,
            'email'
        )
        email = normalizar_email(email)
        
        # Cédula
        cedula = hacer_pregunta(
            "🆔 Cédula (ej: 12345678-9)",
            validar_cedula,
            'cedula'
        )
        cedula = cedula.strip()
        
        # Nombre
        nombre = hacer_pregunta(
            "👤 Nombre Completo (Nombre y Apellido, ej: Juan Pérez García)",
            validar_nombre,
            'nombre'
        )
        nombre = nombre.strip()
        
        # Cargo (opcional)
        cargo_input = input("\n💼 Cargo (opcional, Enter para omitir): ").strip()
        cargo = cargo_input if cargo_input else None
        
        # Rol
        print("\n🔐 Roles disponibles:")
        print("   - admin     : Acceso total")
        print("   - manager   : Gestión operativa")
        print("   - operator  : Operaciones básicas")
        print("   - viewer    : Solo lectura (default)")
        
        rol = hacer_pregunta(
            "Selecciona rol (admin/manager/operator/viewer)",
            validar_rol,
            'rol'
        )
        rol = rol.lower()
        
        # Password
        password = hacer_pregunta(
            "🔑 Password (mínimo 6 caracteres)",
            validar_password,
            'password'
        )
        
        # Generar hash
        print("\n🔐 Generando hash de password...")
        password_hash = generar_hash_password(password)
        
        # Agregar usuario
        usuario = {
            'email': email,
            'cedula': cedula,
            'nombre': nombre,
            'cargo': cargo,
            'rol': rol,
            'password_hash': password_hash,
        }
        usuarios.append(usuario)
        
        print(f"\n✅ Usuario '{email}' agregado")
        
        # Preguntar si agregar otro
        otro = input("\n¿Agregar otro usuario? (s/n): ").strip().lower()
        if otro != 's' and otro != 'si':
            break
    
    return usuarios

def generar_sql(usuarios):
    """Genera SQL INSERT para los usuarios."""
    ahora = datetime.utcnow().isoformat()
    sqls = []
    
    print("\n" + "="*70)
    print("  SQL GENERADO")
    print("="*70)
    
    for usuario in usuarios:
        sql = f"""INSERT INTO usuarios (
    email,
    cedula,
    password_hash,
    nombre,
    cargo,
    rol,
    is_active,
    created_at,
    updated_at
) VALUES (
    '{usuario['email']}',
    '{usuario['cedula']}',
    '{usuario['password_hash']}',
    '{usuario['nombre']}',
    {f"'{usuario['cargo']}'" if usuario['cargo'] else 'NULL'},
    '{usuario['rol']}',
    true,
    '{ahora}',
    '{ahora}'
);"""
        sqls.append(sql)
        print(f"\n-- Usuario: {usuario['email']}")
        print(sql)
    
    return sqls

def generar_archivo_sql(usuarios):
    """Genera archivo .sql con los INSERT."""
    ahora = datetime.utcnow()
    timestamp = ahora.strftime('%Y%m%d_%H%M%S')
    nombre_archivo = f"crear_usuarios_{timestamp}.sql"
    
    ahora_iso = ahora.isoformat()
    
    contenido = """-- ============================================================================
-- Script de inserción de usuarios
-- Generado automáticamente
-- ============================================================================

BEGIN;

"""
    
    for usuario in usuarios:
        contenido += f"""INSERT INTO usuarios (
    email,
    cedula,
    password_hash,
    nombre,
    cargo,
    rol,
    is_active,
    created_at,
    updated_at
) VALUES (
    '{usuario['email']}',
    '{usuario['cedula']}',
    '{usuario['password_hash']}',
    '{usuario['nombre']}',
    {f"'{usuario['cargo']}'" if usuario['cargo'] else 'NULL'},
    '{usuario['rol']}',
    true,
    '{ahora_iso}',
    '{ahora_iso}'
);

"""
    
    contenido += """-- Verificar usuarios creados
SELECT email, nombre, rol, is_active FROM usuarios WHERE created_at >= NOW() - INTERVAL '1 minute';

COMMIT;
"""
    
    try:
        with open(nombre_archivo, 'w', encoding='utf-8') as f:
            f.write(contenido)
        print(f"\n✅ Archivo guardado: {nombre_archivo}")
        return nombre_archivo
    except Exception as e:
        print(f"❌ Error guardando archivo: {e}")
        return None

def main():
    """Función principal."""
    try:
        # Preguntar usuarios
        usuarios = preguntar_usuarios()
        
        if not usuarios:
            print("\n❌ No se ingresaron usuarios")
            return
        
        print(f"\n✅ Total de usuarios: {len(usuarios)}")
        
        # Generar SQL
        sqls = generar_sql(usuarios)
        
        # Guardar en archivo
        archivo = generar_archivo_sql(usuarios)
        
        # Mostrar instrucciones
        print("\n" + "="*70)
        print("  INSTRUCCIONES DE EJECUCIÓN")
        print("="*70)
        print(f"""
1️⃣  Archivo SQL creado: {archivo}

2️⃣  Ejecuta en PostgreSQL:
    psql -U usuario -d base_datos -f {archivo}

3️⃣  O copia y pega el SQL anterior directamente en tu cliente SQL

4️⃣  Verifica que se crearon los usuarios:
    SELECT email, nombre, rol FROM usuarios WHERE created_at >= NOW() - INTERVAL '1 minute';

✅ ¡Listo! Los usuarios están listos en la BD
""")
        
    except KeyboardInterrupt:
        print("\n\n❌ Operación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
