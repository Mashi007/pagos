#!/usr/bin/env python3
"""
Script para verificar el rol del usuario Daniel Casañas
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.core.permissions import UserRole

def verificar_rol_daniel():
    """Verificar el rol del usuario Daniel"""
    db = next(get_db())
    
    try:
        # Buscar usuario Daniel
        user = db.query(User).filter(User.email == 'itmaster@rapicreditca.com').first()
        
        if not user:
            print("❌ ERROR: Usuario Daniel no encontrado")
            return False
        
        print(f"✅ Usuario encontrado: {user.full_name}")
        print(f"📧 Email: {user.email}")
        print(f"👤 Rol actual: {user.rol}")
        print(f"💼 Cargo: {user.cargo}")
        print(f"🟢 Activo: {user.is_active}")
        print(f"📅 Último login: {user.last_login}")
        
        # Verificar si el rol es correcto
        if user.rol == UserRole.ADMIN:
            print("✅ Rol ADMIN correcto")
        else:
            print(f"❌ Rol incorrecto. Debería ser ADMIN, pero es {user.rol}")
            return False
        
        # Verificar todos los usuarios en el sistema
        print("\n📋 Todos los usuarios en el sistema:")
        usuarios = db.query(User).all()
        for u in usuarios:
            print(f"  - {u.full_name} ({u.email}) - Rol: {u.rol} - Activo: {u.is_active}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🔍 Verificando rol del usuario Daniel...")
    success = verificar_rol_daniel()
    if success:
        print("\n✅ Verificación completada exitosamente")
    else:
        print("\n❌ Verificación falló")
        sys.exit(1)
