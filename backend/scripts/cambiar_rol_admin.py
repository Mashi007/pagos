#!/usr/bin/env python3
"""
Script para cambiar rol de usuario a ADMIN
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import get_db
from app.models.user import User
from sqlalchemy.orm import Session

def cambiar_rol_a_admin():
    """Cambiar el rol del usuario itmaster@rapicreditca.com a ADMIN"""
    
    print("🔧 CAMBIANDO ROL DE USUARIO A ADMIN")
    print("=" * 50)
    
    db = next(get_db())
    
    try:
        # Buscar el usuario
        usuario = db.query(User).filter(User.email == "itmaster@rapicreditca.com").first()
        
        if not usuario:
            print("❌ Usuario no encontrado")
            return False
        
        print(f"👤 Usuario encontrado: {usuario.email}")
        print(f"📧 Email: {usuario.email}")
        print(f"👤 Nombre: {usuario.nombre} {usuario.apellido}")
        print(f"🔑 Rol actual: {usuario.rol}")
        print(f"✅ Activo: {usuario.is_active}")
        
        # Cambiar rol a ADMIN
        usuario.rol = "ADMIN"
        db.commit()
        
        print(f"✅ Rol cambiado a: {usuario.rol}")
        print("🎉 ¡Usuario ahora es ADMINISTRADOR!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    cambiar_rol_a_admin()
