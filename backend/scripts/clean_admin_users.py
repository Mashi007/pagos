"""
Script definitivo para limpiar usuarios administradores
ELIMINA admin@financiamiento.com y asegura que solo exista itmaster@rapicreditca.com
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from datetime import datetime

def clean_admin_users():
    """Limpia usuarios administradores - SOLO itmaster@rapicreditca.com debe existir"""
    db = SessionLocal()
    
    try:
        print("🧹 LIMPIEZA DEFINITIVA DE USUARIOS ADMINISTRADORES")
        print("="*60)
        
        # 1. Buscar todos los usuarios administradores
        admins = db.query(User).filter(User.rol == "ADMINISTRADOR_GENERAL").all()
        print(f"📋 Encontrados {len(admins)} usuarios administradores:")
        
        for admin in admins:
            print(f"   - {admin.email} (ID: {admin.id}, Activo: {admin.is_active})")
        
        # 2. Eliminar admin@financiamiento.com si existe
        old_admin = db.query(User).filter(User.email == "admin@financiamiento.com").first()
        
        if old_admin:
            print(f"\n🗑️ ELIMINANDO usuario incorrecto: {old_admin.email}")
            db.delete(old_admin)
            db.commit()
            print("✅ Usuario admin@financiamiento.com eliminado")
        else:
            print("\n✅ No existe admin@financiamiento.com - OK")
        
        # 3. Verificar/crear itmaster@rapicreditca.com
        correct_admin = db.query(User).filter(User.email == "itmaster@rapicreditca.com").first()
        
        if correct_admin:
            print(f"\n✅ Usuario correcto ya existe: {correct_admin.email}")
            print(f"   - ID: {correct_admin.id}")
            print(f"   - Activo: {correct_admin.is_active}")
            print(f"   - Rol: {correct_admin.rol}")
            
            # Asegurar que esté configurado correctamente
            if not correct_admin.is_active:
                correct_admin.is_active = True
                db.commit()
                print("✅ Usuario activado")
                
        else:
            print(f"\n📝 CREANDO usuario correcto: itmaster@rapicreditca.com")
            
            new_admin = User(
                email="itmaster@rapicreditca.com",
                nombre="IT Master",
                apellido="Sistema",
                hashed_password=get_password_hash("R@pi_2025**"),
                rol="ADMINISTRADOR_GENERAL",
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            db.add(new_admin)
            db.commit()
            db.refresh(new_admin)
            
            print("✅ Usuario itmaster@rapicreditca.com creado exitosamente")
        
        # 4. Verificación final
        print(f"\n🔍 VERIFICACIÓN FINAL:")
        final_admins = db.query(User).filter(User.rol == "ADMINISTRADOR_GENERAL").all()
        
        print(f"   Total administradores: {len(final_admins)}")
        
        for admin in final_admins:
            print(f"   ✅ {admin.email} (Activo: {admin.is_active})")
        
        # 5. Verificar que no queden referencias a admin@financiamiento.com
        remaining_old = db.query(User).filter(User.email == "admin@financiamiento.com").first()
        
        if remaining_old:
            print(f"\n❌ ERROR: Aún existe admin@financiamiento.com")
            return False
        else:
            print(f"\n✅ CONFIRMADO: No quedan referencias a admin@financiamiento.com")
        
        print(f"\n🎯 RESULTADO FINAL:")
        print(f"   ✅ Solo existe: itmaster@rapicreditca.com")
        print(f"   ✅ Password: R@pi_2025**")
        print(f"   ✅ Rol: ADMINISTRADOR_GENERAL")
        print(f"   ✅ Activo: True")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Iniciando limpieza definitiva de usuarios administradores...")
    success = clean_admin_users()
    
    if success:
        print("\n🎉 LIMPIEZA COMPLETADA EXITOSAMENTE")
        print("🔑 Credenciales finales:")
        print("   Email: itmaster@rapicreditca.com")
        print("   Password: R@pi_2025**")
        print("\n✅ Sistema listo para login")
    else:
        print("\n❌ Error en la limpieza")
        sys.exit(1)
