#!/usr/bin/env python3
"""
Script para actualizar el usuario administrador a las credenciales correctas
"""

import sys
import os
from sqlalchemy.orm import Session

# Agregar el directorio del backend al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def actualizar_admin():
    """Actualizar usuario admin a las credenciales correctas"""
    db = SessionLocal()
    
    try:
        # Buscar usuario admin existente
        admin_user = db.query(User).filter(User.email == "itmaster@rapicreditca.com").first()
        
        if admin_user:
            print(f"OK - Usuario admin encontrado: {admin_user.email}")
            print(f"   Nombre: {admin_user.nombre} {admin_user.apellido}")
            print(f"   Rol: {admin_user.rol}")
            print(f"   Admin: {admin_user.is_admin}")
            print(f"   Activo: {admin_user.is_active}")
            
            # Actualizar contraseña
            admin_user.hashed_password = get_password_hash("Casa1803+")
            admin_user.is_admin = True
            admin_user.is_active = True
            admin_user.rol = "ADMIN"
            
            db.commit()
            print("OK - Usuario admin actualizado exitosamente")
            
        else:
            print("ERROR - Usuario admin no encontrado")
            
            # Crear nuevo usuario admin
            admin_user = User(
                email="itmaster@rapicreditca.com",
                hashed_password=get_password_hash("Casa1803+"),
                rol="ADMIN",
                is_admin=True,
                is_active=True,
                nombre="IT Master",
                apellido="RapiCredit",
            )
            
            db.add(admin_user)
            db.commit()
            print("OK - Usuario admin creado exitosamente")
            
        # Verificar otros usuarios admin
        print("\nUsuarios administradores en el sistema:")
        admins = db.query(User).filter(User.is_admin == True).all()
        
        for admin in admins:
            print(f"   - {admin.email} ({admin.nombre} {admin.apellido}) - Activo: {admin.is_active}")
            
    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    actualizar_admin()
