#!/usr/bin/env python3
"""
CREAR USUARIO DE PRUEBA CON CONTRASEÑA CONOCIDA
Script para crear usuario admin con contraseña conocida
"""
import bcrypt
import sys
import os

# Agregar el directorio del backend al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from app.models.user import User
    from app.db.session import SessionLocal
    from sqlalchemy.exc import IntegrityError
    import logging
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    def create_test_user():
        """Crear usuario de prueba con credenciales conocidas"""
        db = SessionLocal()
        try:
            email = "admin@rapicredit.com"
            password = "admin123"
            
            # Verificar si ya existe
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                logger.info(f"✅ Usuario {email} ya existe")
                logger.info(f"📧 Email: {email}")
                logger.info(f"🔑 Contraseña: admin123")
                logger.info(f"👤 Rol: {existing_user.rol}")
                return True
            
            # Crear hash de contraseña
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # Crear usuario nuevo
            new_user = User(
                email=email,
                password_hash=password_hash.decode('utf-8'),
                nombre="Admin",
                apellido="Sistema",
                rol="ADMIN",
                activo=True
            )
            
            db.add(new_user)
            db.commit()
            
            logger.info(f"✅ Usuario {email} creado exitosamente")
            logger.info(f"📧 Email: {email}")
            logger.info(f"🔑 Contraseña: {password}")
            logger.info(f"👤 Rol: ADMIN")
            
            return True
            
        except IntegrityError as e:
            logger.error(f"❌ Error de integridad: {e}")
            db.rollback()
            return False
        except Exception as e:
            logger.error(f"❌ Error creando usuario: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def verify_user():
        """Verificar que el usuario existe y las credenciales son correctas"""
        db = SessionLocal()
        try:
            email = "admin@rapicredit.com"
            password = "admin123"
            
            user = db.query(User).filter(User.email == email).first()
            if not user:
                logger.error(f"❌ Usuario {email} no encontrado")
                return False
            
            # Verificar contraseña
            password_valid = bcrypt.checkpw(
                password.encode('utf-8'), 
                user.password_hash.encode('utf-8')
            )
            
            if password_valid:
                logger.info(f"✅ Usuario {email} verificado correctamente")
                logger.info(f"📧 Email: {email}")
                logger.info(f"🔑 Contraseña: {password}")
                logger.info(f"👤 Rol: {user.rol}")
                logger.info(f"✅ Activo: {user.activo}")
                return True
            else:
                logger.error(f"❌ Contraseña incorrecta para {email}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error verificando usuario: {e}")
            return False
        finally:
            db.close()
    
    def main():
        """Función principal"""
        print("🔧 CREANDO USUARIO DE PRUEBA CON CREDENCIALES CONOCIDAS")
        print("=" * 60)
        
        # Crear usuario
        print("\n1. Creando usuario de prueba...")
        success = create_test_user()
        
        if success:
            print("\n2. Verificando credenciales...")
            verify_success = verify_user()
            
            if verify_success:
                print("\n" + "=" * 60)
                print("✅ USUARIO DE PRUEBA CREADO Y VERIFICADO")
                print("📧 Email: admin@rapicredit.com")
                print("🔑 Contraseña: admin123")
                print("👤 Rol: ADMIN")
                print("🎯 Listo para probar login en la aplicación")
                print("=" * 60)
            else:
                print("\n❌ Error verificando usuario")
        else:
            print("\n❌ Error creando usuario")
    
    if __name__ == "__main__":
        main()

except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print("💡 Asegúrate de estar en el directorio correcto")
    print("💡 Ejecuta desde la raíz del proyecto")
except Exception as e:
    print(f"❌ Error general: {e}")
