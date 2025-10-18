# backend/app/api/v1/endpoints/fix_admin_definitive.py
"""
Endpoint DEFINITIVO para corregir usuarios administradores
NO es temporal - es la solución permanente
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db
from app.models.user import User

router = APIRouter()

@router.post("/fix-admin-definitive")
def fix_admin_definitive(db: Session = Depends(get_db)):
    """
    SOLUCIÓN DEFINITIVA: Corregir usuarios administradores
    NO es temporal - es la solución permanente
    
    Marca como administradores a:
    - itmaster@rapicreditca.com
    - admin@rapicredit.com
    - admin@sistema.com
    - daniel@rapicredit.com
    """
    try:
        connection = db.connection()
        
        # Lista de usuarios que DEBEN ser administradores
        admin_emails = [
            'itmaster@rapicreditca.com',
            'admin@rapicredit.com',
            'admin@sistema.com',
            'daniel@rapicredit.com'
        ]
        
        results = []
        
        # Marcar usuarios específicos como administradores
        for email in admin_emails:
            result = connection.execute(text(f"""
                UPDATE usuarios 
                SET is_admin = TRUE, updated_at = NOW()
                WHERE email = '{email}' AND is_active = TRUE
            """))
            
            if result.rowcount > 0:
                results.append({
                    "email": email,
                    "status": "success",
                    "message": "Marcado como administrador"
                })
            else:
                results.append({
                    "email": email,
                    "status": "warning",
                    "message": "No encontrado o inactivo"
                })
        
        # Verificar que al menos un usuario sea administrador
        admin_count = connection.execute(text("SELECT COUNT(*) FROM usuarios WHERE is_admin = TRUE")).scalar()
        
        if admin_count == 0:
            # Crear usuario administrador por defecto
            connection.execute(text("""
                INSERT INTO usuarios (
                    email, nombre, apellido, hashed_password, 
                    is_admin, is_active, created_at
                ) VALUES (
                    'admin@rapicredit.com',
                    'Administrador',
                    'Sistema',
                    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4VqZ8K5K2C', -- admin123
                    TRUE,
                    TRUE,
                    NOW()
                )
                ON CONFLICT (email) DO UPDATE SET
                    is_admin = TRUE,
                    is_active = TRUE,
                    updated_at = NOW()
            """))
            results.append({
                "email": "admin@rapicredit.com",
                "status": "created",
                "message": "Usuario administrador por defecto creado"
            })
        
        # Verificación final
        final_admin_count = connection.execute(text("SELECT COUNT(*) FROM usuarios WHERE is_admin = TRUE")).scalar()
        
        # Mostrar lista de administradores
        admins = connection.execute(text("""
            SELECT email, nombre, apellido, is_active 
            FROM usuarios 
            WHERE is_admin = TRUE 
            ORDER BY email
        """)).fetchall()
        
        admin_list = []
        for admin in admins:
            admin_list.append({
                "email": admin.email,
                "nombre": admin.nombre,
                "apellido": admin.apellido,
                "is_active": admin.is_active
            })
        
        return {
            "status": "success",
            "message": "SOLUCIÓN DEFINITIVA COMPLETADA",
            "total_administradores": final_admin_count,
            "usuarios_corregidos": results,
            "lista_administradores": admin_list
        }
            
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante la corrección: {str(e)}"
        )
