#!/usr/bin/env python3
"""
Script para cambiar la contraseña de un usuario específico
"""

import sys
import os
from sqlalchemy.orm import Session

# Agregar el directorio del backend al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from app.utils.validators import validate_password_strength

def cambiar_password_usuario(email: str, nueva_password: str):
    """Cambiar contraseña de un usuario específico"""
    db = SessionLocal()
    
    try:
        # Buscar usuario por email
        usuario = db.query(User).filter(User.email == email.lower().strip()).first()
        
        if not usuario:
            print(f"❌ ERROR - Usuario no encontrado: {email}")
            return False
        
        print(f"✅ Usuario encontrado: {usuario.email}")
        print(f"   Nombre: {usuario.nombre} {usuario.apellido}")
        print(f"   Rol: {usuario.rol}")
        print(f"   Admin: {usuario.is_admin}")
        print(f"   Activo: {usuario.is_active}")
        
        # Validar nueva contraseña
        is_valid, message = validate_password_strength(nueva_password)
        if not is_valid:
            print(f"❌ ERROR - La contraseña no cumple con los requisitos: {message}")
            return False
        
        # Actualizar contraseña
        usuario.hashed_password = get_password_hash(nueva_password)
        
        # Actualizar updated_at
        from datetime import datetime
        usuario.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(usuario)
        
        print(f"✅ Contraseña actualizada exitosamente para: {email}")
        print(f"   Nueva contraseña: {nueva_password}")
        return True
        
    except Exception as e:
        print(f"❌ ERROR - Error al actualizar contraseña: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python cambiar_password_usuario.py <email> <nueva_password>")
        print("\nEjemplo:")
        print("  python cambiar_password_usuario.py itmaster@rapicreditca.com Casa1803+")
        sys.exit(1)
    
    email = sys.argv[1]
    nueva_password = sys.argv[2]
    
    print(f"🔄 Cambiando contraseña para: {email}")
    print(f"   Nueva contraseña: {nueva_password}")
    print()
    
    success = cambiar_password_usuario(email, nueva_password)
    
    if success:
        print("\n✅ Proceso completado exitosamente")
        sys.exit(0)
    else:
        print("\n❌ Proceso falló")
        sys.exit(1)

