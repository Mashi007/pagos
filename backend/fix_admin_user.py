"""
Script para corregir el usuario administrador
Actualiza admin@financiamiento.com a itmaster@rapicreditca.com
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from datetime import datetime

def fix_admin_user():
    """Corrige el usuario administrador"""
    db = SessionLocal()
    
    try:
        print("🔍 Buscando usuarios administradores...")
        
        # Buscar todos los usuarios admin
        admins = db.query(User).filter(User.rol == "ADMINISTRADOR_GENERAL").all()
        
        if not admins:
            print("❌ No se encontraron usuarios administradores")
            return False
        
        print(f"📋 Encontrados {len(admins)} usuarios administradores:")
        for admin in admins:
            print(f"   - {admin.email} (ID: {admin.id})")
        
        # Buscar el usuario correcto
        correct_admin = db.query(User).filter(User.email == "itmaster@rapicreditca.com").first()
        
        if correct_admin:
            print("✅ Usuario itmaster@rapicreditca.com ya existe")
            print(f"   - ID: {correct_admin.id}")
            print(f"   - Activo: {correct_admin.is_active}")
            print(f"   - Rol: {correct_admin.rol}")
            return True
        
        # Si no existe, actualizar el admin@financiamiento.com
        old_admin = db.query(User).filter(User.email == "admin@financiamiento.com").first()
        
        if old_admin:
            print("🔄 Actualizando admin@financiamiento.com a itmaster@rapicreditca.com...")
            
            old_admin.email = "itmaster@rapicreditca.com"
            old_admin.nombre = "IT Master"
            old_admin.apellido = "Sistema"
            old_admin.hashed_password = get_password_hash("R@pi_2025**")
            old_admin.rol = "ADMINISTRADOR_GENERAL"
            old_admin.is_active = True
            old_admin.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(old_admin)
            
            print("✅ Usuario actualizado exitosamente:")
            print(f"   - Email: {old_admin.email}")
            print(f"   - Password: R@pi_2025**")
            print(f"   - Rol: {old_admin.rol}")
            
            return True
        else:
            print("❌ No se encontró admin@financiamiento.com")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Iniciando corrección de usuario administrador...")
    success = fix_admin_user()
    
    if success:
        print("\n✅ Usuario administrador corregido exitosamente")
        print("🔑 Credenciales:")
        print("   Email: itmaster@rapicreditca.com")
        print("   Password: R@pi_2025**")
    else:
        print("\n❌ Error corrigiendo usuario administrador")
        sys.exit(1)
