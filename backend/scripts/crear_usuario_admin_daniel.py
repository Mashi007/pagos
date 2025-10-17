#!/usr/bin/env python3
"""
Script para crear usuario administrador Daniel Casañas
Inserta directamente en la base de datos con hash de contraseña
"""
import sys
import os
from datetime import datetime

# Agregar el directorio backend al path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.core.security import get_password_hash
from app.core.permissions import UserRole

def crear_usuario_admin():
    """Crear usuario administrador Daniel Casañas"""
    
    # Datos del usuario
    datos_usuario = {
        "nombre": "Daniel",
        "apellido": "Casañas", 
        "email": "itmaster@rapicreditca.com",
        "password": "R@pi_2025**",
        "rol": UserRole.ADMIN,
        "cargo": "Consultor Tecnología",
        "is_active": True
    }
    
    print("🔧 Creando usuario administrador...")
    print(f"📧 Email: {datos_usuario['email']}")
    print(f"👤 Nombre: {datos_usuario['nombre']} {datos_usuario['apellido']}")
    print(f"🛡️ Rol: {datos_usuario['rol']}")
    print(f"💼 Cargo: {datos_usuario['cargo']}")
    
    # Obtener sesión de base de datos
    db = next(get_db())
    
    try:
        # Verificar si el usuario ya existe
        usuario_existente = db.query(User).filter(User.email == datos_usuario['email']).first()
        
        if usuario_existente:
            print(f"⚠️ El usuario {datos_usuario['email']} ya existe")
            print(f"🔄 Actualizando datos del usuario existente...")
            
            # Actualizar datos del usuario existente
            usuario_existente.nombre = datos_usuario['nombre']
            usuario_existente.apellido = datos_usuario['apellido']
            usuario_existente.hashed_password = get_password_hash(datos_usuario['password'])
            usuario_existente.rol = datos_usuario['rol']
            usuario_existente.cargo = datos_usuario['cargo']
            usuario_existente.is_active = datos_usuario['is_active']
            usuario_existente.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(usuario_existente)
            
            print(f"✅ Usuario actualizado exitosamente")
            print(f"🆔 ID: {usuario_existente.id}")
            print(f"📅 Actualizado: {usuario_existente.updated_at}")
            
        else:
            print(f"🆕 Creando nuevo usuario...")
            
            # Crear nuevo usuario
            nuevo_usuario = User(
                nombre=datos_usuario['nombre'],
                apellido=datos_usuario['apellido'],
                email=datos_usuario['email'],
                hashed_password=get_password_hash(datos_usuario['password']),
                rol=datos_usuario['rol'],
                cargo=datos_usuario['cargo'],
                is_active=datos_usuario['is_active'],
                created_at=datetime.utcnow()
            )
            
            db.add(nuevo_usuario)
            db.commit()
            db.refresh(nuevo_usuario)
            
            print(f"✅ Usuario creado exitosamente")
            print(f"🆔 ID: {nuevo_usuario.id}")
            print(f"📅 Creado: {nuevo_usuario.created_at}")
        
        # Verificar creación/actualización
        usuario_final = db.query(User).filter(User.email == datos_usuario['email']).first()
        
        print(f"\n📋 RESUMEN DEL USUARIO:")
        print(f"🆔 ID: {usuario_final.id}")
        print(f"👤 Nombre completo: {usuario_final.full_name}")
        print(f"📧 Email: {usuario_final.email}")
        print(f"🛡️ Rol: {usuario_final.rol}")
        print(f"💼 Cargo: {usuario_final.cargo}")
        print(f"✅ Activo: {usuario_final.is_active}")
        print(f"📅 Creado: {usuario_final.created_at}")
        print(f"📅 Actualizado: {usuario_final.updated_at}")
        
        # Verificar permisos de ADMIN
        from app.core.permissions import has_permission, Permission
        puede_crear_usuarios = has_permission(usuario_final.rol, Permission.USER_CREATE_ADMIN)
        puede_cambiar_estado = has_permission(usuario_final.rol, Permission.USER_CHANGE_STATUS)
        
        print(f"\n🔐 PERMISOS DE ADMINISTRADOR:")
        print(f"👥 Puede crear usuarios: {puede_crear_usuarios}")
        print(f"🔄 Puede cambiar estados: {puede_cambiar_estado}")
        
        if puede_crear_usuarios and puede_cambiar_estado:
            print(f"✅ Usuario configurado correctamente como ADMINISTRADOR")
        else:
            print(f"❌ Error: Usuario no tiene permisos de administrador")
        
        return usuario_final
        
    except Exception as e:
        print(f"❌ Error creando usuario: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    try:
        usuario = crear_usuario_admin()
        print(f"\n🎉 PROCESO COMPLETADO EXITOSAMENTE")
        print(f"🔗 El usuario puede iniciar sesión en: https://rapicredit.onrender.com/login")
        print(f"📧 Email: {usuario.email}")
        print(f"🔑 Contraseña: R@pi_2025**")
        
    except Exception as e:
        print(f"💥 Error fatal: {e}")
        sys.exit(1)
