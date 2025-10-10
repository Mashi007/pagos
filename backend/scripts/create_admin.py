# backend/scripts/create_admin.py
"""
Script para crear usuario administrador inicial
Ejecutar: python scripts/create_admin.py
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


def create_admin_user():
    """Crea el usuario administrador inicial"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*50)
        print("🔧 CREACIÓN DE USUARIO ADMINISTRADOR")
        print("="*50 + "\n")
        
        # Verificar si ya existe un admin
        existing_admin = db.query(User).filter(User.rol == UserRole.ADMIN).first()
        
        if existing_admin:
            print(f"ℹ️  Ya existe un usuario ADMIN:")
            print(f"   📧 Email: {existing_admin.email}")
            print(f"   👤 Nombre: {existing_admin.full_name}")
            print(f"   📅 Creado: {existing_admin.created_at}")
            print("\n❌ No se creó un nuevo usuario\n")
            return
        
        # Crear admin
        admin = User(
            email="admin@sistema.com",
            nombre="Admin",
            apellido="Sistema",
            hashed_password=get_password_hash("Admin123!"),
            rol=UserRole.ADMIN,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("✅ Usuario ADMIN creado exitosamente\n")
        print("📋 CREDENCIALES:")
        print(f"   📧 Email:    {admin.email}")
        print(f"   🔒 Password: Admin123!")
        print(f"   👤 Nombre:   {admin.full_name}")
        print(f"   🎭 Rol:      {admin.rol}")
        print(f"   ✓  Activo:   {'Sí' if admin.is_active else 'No'}")
        print("\n⚠️  IMPORTANTE:")
        print("   1. Guarda estas credenciales")
        print("   2. Cambia la contraseña después del primer login")
        print("   3. No compartas estas credenciales")
        print("\n" + "="*50 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_admin_user()
