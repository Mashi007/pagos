#!/usr/bin/env python3
"""
Script simple para consultar el rol del usuario Daniel
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User

def consultar_rol_daniel():
    """Consultar el rol del usuario Daniel"""
    db = next(get_db())
    
    try:
        # Buscar usuario Daniel
        user = db.query(User).filter(User.email == 'itmaster@rapicreditca.com').first()
        
        if not user:
            print("❌ Usuario Daniel no encontrado")
            return
        
        print("=" * 50)
        print("👤 INFORMACIÓN DEL USUARIO")
        print("=" * 50)
        print(f"📧 Email: {user.email}")
        print(f"👤 Nombre: {user.full_name}")
        print(f"🎭 Rol: {user.rol}")
        print(f"💼 Cargo: {user.cargo}")
        print(f"🟢 Estado: {'Activo' if user.is_active else 'Inactivo'}")
        print(f"📅 Último login: {user.last_login}")
        print("=" * 50)
        
        # Mostrar todos los usuarios
        print("\n📋 TODOS LOS USUARIOS EN EL SISTEMA:")
        print("-" * 50)
        usuarios = db.query(User).all()
        for u in usuarios:
            estado = "🟢" if u.is_active else "🔴"
            print(f"{estado} {u.full_name} - {u.email} - Rol: {u.rol}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    consultar_rol_daniel()
