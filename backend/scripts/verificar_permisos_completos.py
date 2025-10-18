# backend/scripts/verificar_permisos_completos.py
"""
Script para verificar que el usuario admin tenga TODOS los permisos necesarios
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import get_db
from app.models.user import User
from app.core.permissions_simple import get_user_permissions, ADMIN_PERMISSIONS, Permission
from sqlalchemy.orm import Session

def verificar_permisos_admin():
    """
    Verificar que el usuario admin tenga TODOS los permisos necesarios
    """
    print("🔍 VERIFICANDO PERMISOS COMPLETOS DEL SISTEMA")
    print("=" * 60)
    
    # Obtener permisos de admin
    admin_permissions = get_user_permissions(user_is_admin=True)
    
    print(f"📊 TOTAL DE PERMISOS ADMIN: {len(admin_permissions)}")
    print()
    
    # Verificar permisos críticos
    permisos_criticos = [
        Permission.VIEW_DASHBOARD,
        Permission.USER_CREATE,
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.CLIENTE_CREATE,
        Permission.CLIENTE_READ,
        Permission.CLIENTE_UPDATE,
        Permission.CLIENTE_DELETE,
        Permission.PRESTAMO_CREATE,
        Permission.PRESTAMO_READ,
        Permission.PRESTAMO_UPDATE,
        Permission.PRESTAMO_DELETE,
        Permission.PRESTAMO_APPROVE,
        Permission.PAGO_CREATE,
        Permission.PAGO_READ,
        Permission.PAGO_UPDATE,
        Permission.PAGO_DELETE,
        Permission.ANALISTA_CREATE,
        Permission.ANALISTA_READ,
        Permission.ANALISTA_UPDATE,
        Permission.ANALISTA_DELETE,
        Permission.CONCESIONARIO_CREATE,
        Permission.CONCESIONARIO_READ,
        Permission.CONCESIONARIO_UPDATE,
        Permission.CONCESIONARIO_DELETE,
        Permission.MODELO_CREATE,
        Permission.MODELO_READ,
        Permission.MODELO_UPDATE,
        Permission.MODELO_DELETE,
        Permission.REPORTE_READ,
        Permission.AUDIT_READ,
        Permission.CONFIG_READ,
        Permission.CONFIG_UPDATE,
        Permission.CONFIG_MANAGE,
    ]
    
    print("🔍 VERIFICANDO PERMISOS CRÍTICOS:")
    print("-" * 40)
    
    permisos_faltantes = []
    for permiso in permisos_criticos:
        if permiso in admin_permissions:
            print(f"✅ {permiso.value}")
        else:
            print(f"❌ {permiso.value} - FALTANTE")
            permisos_faltantes.append(permiso)
    
    print()
    print("📋 RESUMEN:")
    print(f"✅ Permisos presentes: {len(permisos_criticos) - len(permisos_faltantes)}")
    print(f"❌ Permisos faltantes: {len(permisos_faltantes)}")
    
    if permisos_faltantes:
        print()
        print("🚨 PERMISOS FALTANTES:")
        for permiso in permisos_faltantes:
            print(f"   - {permiso.value}")
        return False
    else:
        print()
        print("✅ TODOS LOS PERMISOS CRÍTICOS ESTÁN PRESENTES")
        return True

def verificar_usuario_admin_real():
    """
    Verificar usuario admin real en la base de datos
    """
    print()
    print("🔍 VERIFICANDO USUARIO ADMIN EN BASE DE DATOS")
    print("=" * 60)
    
    db = next(get_db())
    
    try:
        # Buscar usuarios admin
        usuarios_admin = db.query(User).filter(User.is_admin == True).all()
        
        print(f"👥 Usuarios admin encontrados: {len(usuarios_admin)}")
        
        for usuario in usuarios_admin:
            print(f"   📧 Email: {usuario.email}")
            print(f"   👤 Nombre: {usuario.nombre} {usuario.apellido}")
            print(f"   🔑 is_admin: {usuario.is_admin}")
            print(f"   ✅ Activo: {usuario.is_active}")
            print(f"   📅 Último login: {usuario.last_login}")
            print()
        
        if len(usuarios_admin) == 0:
            print("❌ NO HAY USUARIOS ADMIN EN LA BASE DE DATOS")
            return False
        else:
            print("✅ USUARIOS ADMIN ENCONTRADOS")
            return True
            
    except Exception as e:
        print(f"❌ Error verificando usuarios admin: {e}")
        return False
    finally:
        db.close()

def main():
    """
    Función principal
    """
    print("🚀 VERIFICACIÓN COMPLETA DE PERMISOS DEL SISTEMA")
    print("=" * 70)
    
    # Verificar permisos del sistema
    permisos_ok = verificar_permisos_admin()
    
    # Verificar usuario admin real
    usuario_ok = verificar_usuario_admin_real()
    
    print()
    print("📊 RESULTADO FINAL:")
    print("=" * 30)
    
    if permisos_ok and usuario_ok:
        print("✅ SISTEMA DE PERMISOS COMPLETO Y FUNCIONAL")
        print("✅ Usuario admin tiene todos los permisos necesarios")
        return True
    else:
        print("❌ PROBLEMAS DETECTADOS:")
        if not permisos_ok:
            print("   - Permisos del sistema incompletos")
        if not usuario_ok:
            print("   - No hay usuarios admin en la base de datos")
        return False

if __name__ == "__main__":
    main()
