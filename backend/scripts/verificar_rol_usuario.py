#!/usr/bin/env python3
"""
Script para verificar el rol de un usuario específico
"""

import sys
import os

# Agregar el directorio del backend al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.user import User

def verificar_rol_usuario(email: str):
    """Verificar el rol de un usuario por su email"""
    db = SessionLocal()

    try:
        # Buscar usuario por email
        usuario = db.query(User).filter(User.email == email).first()

        if not usuario:
            print(f"❌ Usuario no encontrado: {email}")
            return None

        print(f"\n{'='*60}")
        print(f"📧 INFORMACIÓN DEL USUARIO")
        print(f"{'='*60}")
        print(f"Email:           {usuario.email}")
        print(f"Nombre:          {usuario.nombre} {usuario.apellido}")
        print(f"Rol (campo):     {usuario.rol}")
        print(f"Es Admin:        {'✅ SÍ' if usuario.is_admin else '❌ NO'}")
        print(f"Cargo:           {usuario.cargo or 'No especificado'}")
        print(f"Activo:          {'✅ SÍ' if usuario.is_active else '❌ NO'}")
        print(f"Fecha creación:  {usuario.created_at}")
        print(f"{'='*60}")

        # Determinar el rol efectivo
        if usuario.is_admin:
            rol_efectivo = "ADMIN (Administrador - Acceso completo)"
        else:
            rol_efectivo = f"USER (Usuario - Acceso limitado) - Rol en BD: {usuario.rol}"

        print(f"\n🎯 ROL EFECTIVO: {rol_efectivo}")
        print(f"\n")

        return usuario

    except Exception as e:
        print(f"❌ Error consultando usuario: {e}")
        return None
    finally:
        db.close()

if __name__ == "__main__":
    # Email a verificar
    email = "operaciones@rapicreditca.com"

    if len(sys.argv) > 1:
        email = sys.argv[1]

    verificar_rol_usuario(email)
