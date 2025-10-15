"""
Endpoint SQL directo para eliminar admin@financiamiento.com
"""
from fastapi import APIRouter, Depends, HTTPException
from app.core.config import settings
import psycopg2
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/delete-wrong-admin")
def delete_wrong_admin():
    """
    🗑️ Eliminar admin@financiamiento.com usando SQL directo
    """
    try:
        # Conectar directamente a PostgreSQL
        conn = psycopg2.connect(
            host=settings.DATABASE_HOST,
            database=settings.DATABASE_NAME,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            port=settings.DATABASE_PORT
        )
        
        cursor = conn.cursor()
        
        # 1. Verificar si existe admin@financiamiento.com
        cursor.execute("SELECT id, email, rol FROM users WHERE email = %s", ("admin@financiamiento.com",))
        wrong_admin = cursor.fetchone()
        
        if wrong_admin:
            admin_id, email, rol = wrong_admin
            logger.info(f"🗑️ Eliminando: {email} (ID: {admin_id}, Rol: {rol})")
            
            # 2. Eliminar el usuario
            cursor.execute("DELETE FROM users WHERE email = %s", ("admin@financiamiento.com",))
            deleted_rows = cursor.rowcount
            
            if deleted_rows > 0:
                logger.info(f"✅ Usuario {email} eliminado exitosamente")
                
                # 3. Verificar que se eliminó
                cursor.execute("SELECT COUNT(*) FROM users WHERE email = %s", ("admin@financiamiento.com",))
                remaining_count = cursor.fetchone()[0]
                
                if remaining_count > 0:
                    raise Exception("Error: El usuario aún existe después de eliminarlo")
                
                # 4. Verificar usuarios restantes
                cursor.execute("SELECT id, email, rol, is_active FROM users WHERE rol = 'ADMINISTRADOR_GENERAL'")
                remaining_admins = cursor.fetchall()
                
                conn.commit()
                cursor.close()
                conn.close()
                
                result = {
                    "message": f"✅ Usuario admin@financiamiento.com eliminado exitosamente",
                    "deleted_user": {
                        "id": admin_id,
                        "email": email,
                        "role": rol
                    },
                    "remaining_admins": len(remaining_admins),
                    "remaining_admin_details": []
                }
                
                for admin in remaining_admins:
                    result["remaining_admin_details"].append({
                        "id": admin[0],
                        "email": admin[1],
                        "role": admin[2],
                        "active": admin[3]
                    })
                
                return result
            else:
                raise Exception("No se pudo eliminar el usuario")
        else:
            logger.info("✅ admin@financiamiento.com no existe")
            
            cursor.close()
            conn.close()
            
            return {
                "message": "✅ admin@financiamiento.com no existe",
                "status": "already_clean"
            }
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/create-correct-admin")
def create_correct_admin():
    """
    📝 Crear itmaster@rapicreditca.com usando SQL directo
    """
    try:
        # Conectar directamente a PostgreSQL
        conn = psycopg2.connect(
            host=settings.DATABASE_HOST,
            database=settings.DATABASE_NAME,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            port=settings.DATABASE_PORT
        )
        
        cursor = conn.cursor()
        
        # 1. Verificar si ya existe itmaster@rapicreditca.com
        cursor.execute("SELECT id, email, rol, is_active FROM users WHERE email = %s", ("itmaster@rapicreditca.com",))
        existing_admin = cursor.fetchone()
        
        if existing_admin:
            admin_id, email, rol, is_active = existing_admin
            logger.info(f"✅ Usuario ya existe: {email} (ID: {admin_id}, Activo: {is_active})")
            
            cursor.close()
            conn.close()
            
            return {
                "message": "✅ itmaster@rapicreditca.com ya existe",
                "admin": {
                    "id": admin_id,
                    "email": email,
                    "role": rol,
                    "active": is_active
                },
                "status": "already_exists"
            }
        
        # 2. Crear el usuario
        logger.info("📝 Creando itmaster@rapicreditca.com...")
        
        # Hash de la contraseña (usando bcrypt)
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password = pwd_context.hash("R@pi_2025**")
        
        cursor.execute("""
            INSERT INTO users (email, nombre, apellido, hashed_password, rol, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            RETURNING id
        """, (
            "itmaster@rapicreditca.com",
            "IT Master",
            "Sistema",
            hashed_password,
            "ADMINISTRADOR_GENERAL",
            True
        ))
        
        new_admin_id = cursor.fetchone()[0]
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Usuario itmaster@rapicreditca.com creado con ID: {new_admin_id}")
        
        return {
            "message": "✅ itmaster@rapicreditca.com creado exitosamente",
            "admin": {
                "id": new_admin_id,
                "email": "itmaster@rapicreditca.com",
                "role": "ADMINISTRADOR_GENERAL",
                "active": True
            },
            "login_credentials": {
                "email": "itmaster@rapicreditca.com",
                "password": "R@pi_2025**",
                "role": "ADMINISTRADOR_GENERAL"
            },
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/fix-complete")
def fix_complete():
    """
    🔧 Fix completo: eliminar incorrecto + crear correcto
    """
    try:
        # Conectar directamente a PostgreSQL
        conn = psycopg2.connect(
            host=settings.DATABASE_HOST,
            database=settings.DATABASE_NAME,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            port=settings.DATABASE_PORT
        )
        
        cursor = conn.cursor()
        
        # 1. Eliminar admin@financiamiento.com
        cursor.execute("SELECT id FROM users WHERE email = %s", ("admin@financiamiento.com",))
        wrong_admin = cursor.fetchone()
        
        if wrong_admin:
            logger.info(f"🗑️ Eliminando admin@financiamiento.com...")
            cursor.execute("DELETE FROM users WHERE email = %s", ("admin@financiamiento.com",))
            deleted = True
        else:
            logger.info("✅ admin@financiamiento.com no existe")
            deleted = False
        
        # 2. Crear itmaster@rapicreditca.com si no existe
        cursor.execute("SELECT id FROM users WHERE email = %s", ("itmaster@rapicreditca.com",))
        correct_admin = cursor.fetchone()
        
        if correct_admin:
            logger.info("✅ itmaster@rapicreditca.com ya existe")
            created = False
        else:
            logger.info("📝 Creando itmaster@rapicreditca.com...")
            
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            hashed_password = pwd_context.hash("R@pi_2025**")
            
            cursor.execute("""
                INSERT INTO users (email, nombre, apellido, hashed_password, rol, is_active, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
            """, (
                "itmaster@rapicreditca.com",
                "IT Master",
                "Sistema",
                hashed_password,
                "ADMINISTRADOR_GENERAL",
                True
            ))
            
            new_admin_id = cursor.fetchone()[0]
            created = True
        
        # 3. Estado final
        cursor.execute("SELECT id, email, rol, is_active FROM users WHERE rol = 'ADMINISTRADOR_GENERAL'")
        final_admins = cursor.fetchall()
        
        conn.commit()
        cursor.close()
        conn.close()
        
        result = {
            "message": "✅ Fix completo ejecutado exitosamente",
            "actions": {
                "deleted_wrong_admin": deleted,
                "created_correct_admin": created
            },
            "final_state": {
                "total_admins": len(final_admins),
                "admins": []
            },
            "login_credentials": {
                "email": "itmaster@rapicreditca.com",
                "password": "R@pi_2025**",
                "role": "ADMINISTRADOR_GENERAL"
            }
        }
        
        for admin in final_admins:
            result["final_state"]["admins"].append({
                "id": admin[0],
                "email": admin[1],
                "role": admin[2],
                "active": admin[3]
            })
        
        logger.info("✅ Fix completo ejecutado exitosamente")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
