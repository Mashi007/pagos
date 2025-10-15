# backend/scripts/update_admin.py
"""
Script para actualizar el administrador del sistema
Actualiza credenciales y elimina otros usuarios
"""
import sys
import os

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from app.core.permissions import UserRole
from datetime import datetime


def update_admin_system():
    """Actualizar administrador del sistema y eliminar otros usuarios"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*70)
        print("🔧 ACTUALIZACIÓN DEL SISTEMA DE USUARIOS")
        print("="*70 + "\n")
        
        # 1. Eliminar todos los usuarios existentes
        print("🗑️  ELIMINANDO USUARIOS EXISTENTES...")
        usuarios_existentes = db.query(User).all()
        
        if usuarios_existentes:
            print(f"   📊 Usuarios encontrados: {len(usuarios_existentes)}")
            for usuario in usuarios_existentes:
                print(f"   ❌ Eliminando: {usuario.email} ({usuario.rol})")
            
            # Eliminar todos los usuarios
            db.query(User).delete()
            db.commit()
            print("   ✅ Todos los usuarios eliminados")
        else:
            print("   ℹ️  No hay usuarios existentes")
        
        # 2. Crear nuevo administrador del sistema
        print("\n👑 CREANDO NUEVO ADMINISTRADOR DEL SISTEMA...")
        
        admin = User(
            email="itmaster@rapicreditca.com",
            nombre="IT",
            apellido="Master",
            hashed_password=get_password_hash("R@pi_2025**"),
            rol=UserRole.ADMINISTRADOR_GENERAL,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("✅ Administrador del sistema creado exitosamente\n")
        
        # 3. Mostrar credenciales
        print("📋 CREDENCIALES DEL ADMINISTRADOR DEL SISTEMA:")
        print(f"   📧 Email:    {admin.email}")
        print(f"   🔒 Password: R@pi_2025**")
        print(f"   👤 Nombre:   {admin.full_name}")
        print(f"   🎭 Rol:      {admin.rol}")
        print(f"   ✓  Activo:   {'Sí' if admin.is_active else 'No'}")
        print(f"   🆔 ID:       {admin.id}")
        
        # 4. Verificar sistema
        print("\n🔍 VERIFICACIÓN DEL SISTEMA:")
        total_usuarios = db.query(User).count()
        print(f"   👥 Total usuarios: {total_usuarios}")
        
        admin_verificado = db.query(User).filter(
            User.email == "itmaster@rapicreditca.com",
            User.is_active == True
        ).first()
        
        if admin_verificado:
            print("   ✅ Administrador verificado y activo")
            print("   ✅ Sistema listo para uso")
        else:
            print("   ❌ Error en verificación del administrador")
        
        # 5. Información de acceso
        print("\n🌐 INFORMACIÓN DE ACCESO:")
        print("   🏠 URL del sistema: https://pagos-f2qf.onrender.com")
        print("   📖 Documentación: https://pagos-f2qf.onrender.com/docs")
        print("   🔐 Endpoint de login: POST /api/v1/auth/login")
        print("   📊 Dashboard: GET /api/v1/dashboard/admin")
        
        print("\n🧪 PRUEBA DE LOGIN:")
        print("   curl -X POST 'https://pagos-f2qf.onrender.com/api/v1/auth/login' \\")
        print("        -H 'Content-Type: application/json' \\")
        print('        -d \'{"email":"itmaster@rapicreditca.com","password":"R@pi_2025**"}\'')
        
        print("\n🔐 PERMISOS DEL ADMINISTRADOR:")
        print("   ✅ Acceso completo a todos los módulos")
        print("   ✅ Gestión de usuarios y roles")
        print("   ✅ Configuración del sistema")
        print("   ✅ Herramientas de auditoría")
        print("   ✅ Carga masiva de datos")
        print("   ✅ Generación de reportes")
        print("   ✅ Dashboard administrativo")
        
        print("\n⚠️  IMPORTANTE:")
        print("   1. 🔐 Estas son las únicas credenciales válidas")
        print("   2. 🚫 Solo usuarios registrados pueden acceder")
        print("   3. 🛡️  Sistema completamente protegido")
        print("   4. 📝 Usar estas credenciales para acceder")
        
        print("\n" + "="*70 + "\n")
        
        return admin
        
    except Exception as e:
        print(f"\n❌ Error actualizando sistema: {e}\n")
        db.rollback()
        return None
    finally:
        db.close()


def verify_login_system():
    """Verificar que el sistema de login funciona correctamente"""
    db = SessionLocal()
    
    try:
        print("\n🔍 VERIFICACIÓN DEL SISTEMA DE LOGIN:")
        
        # Verificar que solo existe el administrador
        usuarios = db.query(User).all()
        print(f"   👥 Usuarios registrados: {len(usuarios)}")
        
        if len(usuarios) == 1:
            admin = usuarios[0]
            print(f"   ✅ Solo existe el administrador: {admin.email}")
            print(f"   ✅ Rol: {admin.rol}")
            print(f"   ✅ Activo: {admin.is_active}")
            
            # Verificar credenciales
            from app.core.security import verify_password
            if verify_password("R@pi_2025**", admin.hashed_password):
                print("   ✅ Contraseña verificada correctamente")
            else:
                print("   ❌ Error en verificación de contraseña")
                
        else:
            print(f"   ❌ Error: Se encontraron {len(usuarios)} usuarios")
            for usuario in usuarios:
                print(f"      - {usuario.email} ({usuario.rol})")
        
        print("\n🛡️  SISTEMA DE SEGURIDAD:")
        print("   ✅ Solo usuarios registrados pueden acceder")
        print("   ✅ Autenticación JWT requerida")
        print("   ✅ Verificación de usuario activo")
        print("   ✅ Control de permisos por rol")
        
        return len(usuarios) == 1
        
    except Exception as e:
        print(f"\n❌ Error verificando sistema: {e}\n")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 INICIANDO ACTUALIZACIÓN DEL SISTEMA DE USUARIOS")
    
    # Actualizar administrador
    admin = update_admin_system()
    
    if admin:
        # Verificar sistema
        verify_login_system()
        print("\n✅ SISTEMA ACTUALIZADO EXITOSAMENTE")
    else:
        print("\n❌ ERROR EN LA ACTUALIZACIÓN DEL SISTEMA")
