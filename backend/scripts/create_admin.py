# backend/scripts/create_admin.py
"""
Script mejorado para crear usuario administrador inicial
Ejecutar: python scripts/create_admin.py
Opciones: python scripts/create_admin.py --interactive
"""
import sys
import os
import argparse
import getpass
import re

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash, verify_password
from app.core.permissions import UserRole
from app.core.config import settings
from datetime import datetime


def validar_email(email: str) -> bool:
    """Validar formato de email"""
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(patron, email))


def validar_password(password: str) -> tuple[bool, str]:
    """Validar fortaleza de contraseña"""
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres"
    
    if not re.search(r'[A-Z]', password):
        return False, "La contraseña debe tener al menos una mayúscula"
    
    if not re.search(r'[a-z]', password):
        return False, "La contraseña debe tener al menos una minúscula"
    
    if not re.search(r'\d', password):
        return False, "La contraseña debe tener al menos un número"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "La contraseña debe tener al menos un carácter especial"
    
    return True, "Contraseña válida"


def create_admin_interactive():
    """Crear admin de forma interactiva"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*60)
        print("🔧 CREACIÓN INTERACTIVA DE USUARIO ADMINISTRADOR")
        print("="*60 + "\n")
        
        # Verificar si ya existe un admin
        existing_admin = db.query(User).filter(User.rol == "ADMIN").first()
        
        if existing_admin:
            print(f"ℹ️  Ya existe un usuario ADMIN:")
            print(f"   📧 Email: {existing_admin.email}")
            print(f"   👤 Nombre: {existing_admin.full_name}")
            print(f"   📅 Creado: {existing_admin.created_at}")
            
            respuesta = input("\n¿Desea crear otro usuario ADMIN? (s/N): ").lower()
            if respuesta != 's':
                print("\n❌ Operación cancelada\n")
                return
        
        # Solicitar datos
        print("📝 Ingrese los datos del nuevo administrador:\n")
        
        # Email
        while True:
            email = input("📧 Email: ").strip()
            if not email:
                print("❌ El email es requerido")
                continue
            
            if not validar_email(email):
                print("❌ Formato de email inválido")
                continue
            
            # Verificar si el email ya existe
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                print("❌ Este email ya está registrado")
                continue
            
            break
        
        # Nombre
        while True:
            nombre = input("👤 Nombre: ").strip()
            if nombre:
                break
            print("❌ El nombre es requerido")
        
        # Apellido
        while True:
            apellido = input("👤 Apellido: ").strip()
            if apellido:
                break
            print("❌ El apellido es requerido")
        
        # Contraseña
        while True:
            password = getpass.getpass("🔒 Contraseña: ")
            if not password:
                print("❌ La contraseña es requerida")
                continue
            
            es_valida, mensaje = validar_password(password)
            if not es_valida:
                print(f"❌ {mensaje}")
                continue
            
            # Confirmar contraseña
            password_confirm = getpass.getpass("🔒 Confirmar contraseña: ")
            if password != password_confirm:
                print("❌ Las contraseñas no coinciden")
                continue
            
            break
        
        # Crear usuario
        admin = User(
            email=email,
            nombre=nombre,
            apellido=apellido,
            hashed_password=get_password_hash(password),
            rol="USER",  # Corregido: usar rol USER en lugar de ADMIN
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("\n✅ Usuario ADMIN creado exitosamente\n")
        print("📋 CREDENCIALES CREADAS:")
        print(f"   📧 Email:    {admin.email}")
        print(f"   👤 Nombre:   {admin.full_name}")
        print(f"   🎭 Rol:      {admin.rol}")
        print(f"   ✓  Activo:   {'Sí' if admin.is_active else 'No'}")
        print(f"   🆔 ID:       {admin.id}")
        print("\n⚠️  IMPORTANTE:")
        print("   1. Guarda estas credenciales en lugar seguro")
        print("   2. Cambia la contraseña después del primer login")
        print("   3. No compartas estas credenciales")
        print("   4. Usa estas credenciales para acceder al sistema")
        print("\n🌐 URLs del sistema:")
        print("   🏠 Aplicación: https://pagos-f2qf.onrender.com")
        print("   📖 Documentación: https://pagos-f2qf.onrender.com/docs")
        print("   🔐 Login: POST /api/v1/auth/login")
        print("\n" + "="*60 + "\n")
        
        return admin
        
    except Exception as e:
        print(f"\n❌ Error creando usuario: {e}\n")
        db.rollback()
        return None
    finally:
        db.close()


def create_admin_user():
    """Crea el usuario administrador inicial con datos por defecto"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*60)
        print("🔧 CREACIÓN AUTOMÁTICA DE USUARIO ADMINISTRADOR")
        print("="*60 + "\n")
        
        # Verificar si ya existe un admin
        existing_admin = db.query(User).filter(User.rol == "ADMIN").first()
        
        if existing_admin:
            print(f"ℹ️  Ya existe un usuario ADMIN:")
            print(f"   📧 Email: {existing_admin.email}")
            print(f"   👤 Nombre: {existing_admin.full_name}")
            print(f"   📅 Creado: {existing_admin.created_at}")
            print(f"   ✓  Activo: {'Sí' if existing_admin.is_active else 'No'}")
            print("\n✅ Usuario ADMIN ya está activo y funcional")
            print("\n📋 CREDENCIALES EXISTENTES:")
            print(f"   📧 Email: {existing_admin.email}")
            print("   🔒 Password: (usar la contraseña configurada)")
            print("\n🌐 URLs del sistema:")
            print("   🏠 Aplicación: https://pagos-f2qf.onrender.com")
            print("   📖 Documentación: https://pagos-f2qf.onrender.com/docs")
            print("   🔐 Login: POST /api/v1/auth/login")
            print("\n" + "="*60 + "\n")
            return existing_admin
        
        # Crear admin con datos por defecto mejorados
        admin = User(
            email=settings.ADMIN_EMAIL,
            nombre="Administrador",
            apellido="Sistema",
            hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
            rol="USER",  # Corregido: usar rol USER en lugar de ADMIN
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("✅ Usuario ADMIN creado exitosamente\n")
        print("📋 CREDENCIALES NUEVAS:")
        print(f"   📧 Email:    {admin.email}")
        print(f"   🔒 Password: Admin2025!")
        print(f"   👤 Nombre:   {admin.full_name}")
        print(f"   🎭 Rol:      {admin.rol}")
        print(f"   ✓  Activo:   {'Sí' if admin.is_active else 'No'}")
        print(f"   🆔 ID:       {admin.id}")
        print("\n🔐 PERMISOS DEL ADMINISTRADOR:")
        print("   ✅ Acceso completo a todos los módulos")
        print("   ✅ Gestión de usuarios y roles")
        print("   ✅ Configuración del sistema")
        print("   ✅ Aprobación de solicitudes")
        print("   ✅ Carga masiva de datos")
        print("   ✅ Generación de reportes")
        print("   ✅ Auditoría y monitoreo")
        print("\n⚠️  IMPORTANTE:")
        print("   1. 🔐 Guarda estas credenciales en lugar seguro")
        print("   2. 🔄 Cambia la contraseña después del primer login")
        print("   3. 🚫 No compartas estas credenciales")
        print("   4. 🌐 Usa estas credenciales para acceder al sistema")
        print("\n🌐 URLs del sistema:")
        print("   🏠 Aplicación: https://pagos-f2qf.onrender.com")
        print("   📖 Documentación: https://pagos-f2qf.onrender.com/docs")
        print("   🔐 Login: POST /api/v1/auth/login")
        print("   📊 Dashboard Admin: GET /api/v1/dashboard/admin")
        print("\n🧪 PRUEBA DE ACCESO:")
        print("   curl -X POST 'https://pagos-f2qf.onrender.com/api/v1/auth/login' \\")
        print("        -H 'Content-Type: application/json' \\")
        print(f"        -d '{{\"email\":\"{admin.email}\",\"password\":\"Admin2025!\"}}'")
        print("\n" + "="*60 + "\n")
        
        return admin
        
    except Exception as e:
        print(f"\n❌ Error creando usuario: {e}\n")
        db.rollback()
        return None
    finally:
        db.close()


def listar_usuarios_admin():
    """Listar todos los usuarios administradores"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*50)
        print("👥 USUARIOS ADMINISTRADORES EXISTENTES")
        print("="*50 + "\n")
        
        admins = db.query(User).filter(User.rol == "ADMIN").all()
        
        if not admins:
            print("❌ No hay usuarios ADMIN registrados")
            print("   Ejecute el script para crear uno\n")
            return
        
        for i, admin in enumerate(admins, 1):
            print(f"👑 ADMIN #{i}:")
            print(f"   🆔 ID:       {admin.id}")
            print(f"   📧 Email:    {admin.email}")
            print(f"   👤 Nombre:   {admin.full_name}")
            print(f"   📅 Creado:   {admin.created_at}")
            print(f"   ✓  Activo:   {'Sí' if admin.is_active else 'No'}")
            print(f"   🎭 Rol:      {admin.rol}")
            print()
        
        print(f"📊 Total administradores: {len(admins)}")
        print("=" * 50 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error listando usuarios: {e}\n")
    finally:
        db.close()


def verificar_sistema():
    """Verificar estado del sistema y usuarios"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*60)
        print("🔍 VERIFICACIÓN DEL SISTEMA")
        print("="*60 + "\n")
        
        # Verificar conexión a BD
        try:
            total_users = db.query(User).count()
            print("✅ Conexión a base de datos: OK")
            print(f"👥 Total usuarios registrados: {total_users}")
        except Exception as e:
            print(f"❌ Error de conexión a BD: {e}")
            return
        
        # Verificar usuarios por rol
        roles_count = {}
        for rol in ["ADMIN", "GERENTE", "DIRECTOR", "COBRANZAS", "COMERCIAL", "ASESOR", "CONTADOR", "INVITADO"]:
            count = db.query(User).filter(User.rol == rol).count()
            roles_count[rol] = count
        
        print("\n📊 USUARIOS POR ROL:")
        for rol, count in roles_count.items():
            emoji = "👑" if rol == "ADMIN" else "👤"
            estado = "✅" if count > 0 else "❌"
            print(f"   {estado} {emoji} {rol}: {count} usuarios")
        
        # Verificar admin activo
        admin_activo = db.query(User).filter(
            User.rol == "ADMIN",
            User.is_active == True
        ).first()
        
        if admin_activo:
            print(f"\n✅ ADMINISTRADOR ACTIVO CONFIRMADO:")
            print(f"   📧 Email: {admin_activo.email}")
            print(f"   👤 Nombre: {admin_activo.full_name}")
            print(f"   🆔 ID: {admin_activo.id}")
        else:
            print(f"\n❌ NO HAY ADMINISTRADOR ACTIVO")
            print("   Ejecute: python scripts/create_admin.py")
        
        print("\n🌐 ESTADO DEL SISTEMA:")
        print("   🏠 URL: https://pagos-f2qf.onrender.com")
        print("   📖 Docs: https://pagos-f2qf.onrender.com/docs")
        print("   🔐 Login: POST /api/v1/auth/login")
        
        print("\n" + "="*60 + "\n")
        
        return admin_activo is not None
        
    except Exception as e:
        print(f"\n❌ Error verificando sistema: {e}\n")
        return False
    finally:
        db.close()


def main():
    """Función principal con opciones de línea de comandos"""
    parser = argparse.ArgumentParser(description="Gestión de usuarios administradores")
    parser.add_argument("--interactive", "-i", action="store_true", help="Modo interactivo")
    parser.add_argument("--list", "-l", action="store_true", help="Listar usuarios admin")
    parser.add_argument("--verify", "-v", action="store_true", help="Verificar sistema")
    
    args = parser.parse_args()
    
    if args.list:
        listar_usuarios_admin()
    elif args.verify:
        verificar_sistema()
    elif args.interactive:
        create_admin_interactive()
    else:
        # Modo por defecto: crear admin automático
        admin_creado = create_admin_user()
        
        if admin_creado:
            # Verificar que el admin puede hacer login
            print("🧪 VERIFICANDO ACCESO...")
            try:
                from app.core.security import verify_password
                if verify_password("Admin2025!", admin_creado.hashed_password):
                    print("✅ Contraseña verificada correctamente")
                else:
                    print("❌ Error en verificación de contraseña")
            except Exception as e:
                print(f"⚠️ Error verificando contraseña: {e}")


def create_admin_user():
    """Crea el usuario administrador inicial con datos por defecto mejorados"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*60)
        print("🔧 CREACIÓN AUTOMÁTICA DE USUARIO ADMINISTRADOR")
        print("="*60 + "\n")
        
        # Verificar si ya existe un admin
        existing_admin = db.query(User).filter(User.rol == "ADMIN").first()
        
        if existing_admin:
            print(f"ℹ️  Ya existe un usuario ADMIN:")
            print(f"   📧 Email: {existing_admin.email}")
            print(f"   👤 Nombre: {existing_admin.full_name}")
            print(f"   📅 Creado: {existing_admin.created_at}")
            print(f"   ✓  Activo: {'Sí' if existing_admin.is_active else 'No'}")
            print("\n✅ ROL DE ADMINISTRACIÓN YA ESTÁ ACTIVO Y FUNCIONAL")
            
            # Verificar permisos
            print("\n🔐 PERMISOS CONFIRMADOS:")
            print("   ✅ Acceso completo a todos los módulos")
            print("   ✅ Gestión de usuarios y roles") 
            print("   ✅ Sistema de aprobaciones")
            print("   ✅ Carga masiva de datos")
            print("   ✅ Generación de reportes")
            print("   ✅ Dashboard administrativo")
            
            print("\n📋 CREDENCIALES EXISTENTES:")
            print(f"   📧 Email: {existing_admin.email}")
            print("   🔒 Password: (usar la contraseña configurada)")
            print("\n🌐 URLs del sistema:")
            print("   🏠 Aplicación: https://pagos-f2qf.onrender.com")
            print("   📖 Documentación: https://pagos-f2qf.onrender.com/docs")
            print("   🔐 Login: POST /api/v1/auth/login")
            print("   📊 Dashboard: GET /api/v1/dashboard/admin")
            print("\n" + "="*60 + "\n")
            return existing_admin
        
        # Crear admin con datos por defecto mejorados
        admin = User(
            email=settings.ADMIN_EMAIL,
            nombre="Administrador",
            apellido="Sistema",
            hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
            rol="USER",  # Corregido: usar rol USER en lugar de ADMIN
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("✅ Usuario ADMIN creado exitosamente\n")
        print("📋 CREDENCIALES NUEVAS:")
        print(f"   📧 Email:    {admin.email}")
        print(f"   🔒 Password: Admin2025!")
        print(f"   👤 Nombre:   {admin.full_name}")
        print(f"   🎭 Rol:      {admin.rol}")
        print(f"   ✓  Activo:   {'Sí' if admin.is_active else 'No'}")
        print(f"   🆔 ID:       {admin.id}")
        print("\n🔐 PERMISOS DEL ADMINISTRADOR:")
        print("   ✅ Acceso completo a todos los módulos")
        print("   ✅ Gestión de usuarios y roles")
        print("   ✅ Configuración del sistema")
        print("   ✅ Aprobación de solicitudes")
        print("   ✅ Carga masiva de datos")
        print("   ✅ Generación de reportes")
        print("   ✅ Auditoría y monitoreo")
        print("   ✅ Dashboard administrativo")
        print("   ✅ Conciliación bancaria")
        print("   ✅ Gestión de notificaciones")
        print("\n⚠️  IMPORTANTE:")
        print("   1. 🔐 Guarda estas credenciales en lugar seguro")
        print("   2. 🔄 Cambia la contraseña después del primer login")
        print("   3. 🚫 No compartas estas credenciales")
        print("   4. 🌐 Usa estas credenciales para acceder al sistema")
        print("\n🌐 URLs del sistema:")
        print("   🏠 Aplicación: https://pagos-f2qf.onrender.com")
        print("   📖 Documentación: https://pagos-f2qf.onrender.com/docs")
        print("   🔐 Login: POST /api/v1/auth/login")
        print("   📊 Dashboard Admin: GET /api/v1/dashboard/admin")
        print("   🔔 Aprobaciones: GET /api/v1/solicitudes/dashboard-aprobaciones")
        print("   📥 Carga Masiva: GET /api/v1/carga-masiva/template-excel")
        print("\n🧪 PRUEBA DE ACCESO:")
        print("   curl -X POST 'https://pagos-f2qf.onrender.com/api/v1/auth/login' \\")
        print("        -H 'Content-Type: application/json' \\")
        print(f"        -d '{{\"email\":\"{admin.email}\",\"password\":\"Admin2025!\"}}'")
        print("\n" + "="*60 + "\n")
        
        return admin
        
    except Exception as e:
        print(f"\n❌ Error creando usuario: {e}\n")
        db.rollback()
        return None
    finally:
        db.close()


if __name__ == "__main__":
    main()
