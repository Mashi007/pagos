# backend/app/api/v1/endpoints/debug_auth.py
"""
Endpoint de debug para autenticación
Solo para diagnóstico de problemas
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.models.user import User

router = APIRouter()

@router.get("/test-simple-query")
def test_simple_query(db: Session = Depends(get_db)):
    """Probar consulta simple sin modelo User"""
    try:
        result = db.execute(text("SELECT 1 as test"))
        return {"status": "success", "test": result.fetchone()[0]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/test-user-count")
def test_user_count(db: Session = Depends(get_db)):
    """Probar conteo de usuarios sin SELECT completo"""
    try:
        result = db.execute(text("SELECT COUNT(*) FROM usuarios"))
        count = result.fetchone()[0]
        return {"status": "success", "user_count": count}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/test-user-query")
def test_user_query(db: Session = Depends(get_db)):
    """Probar consulta de usuario específico"""
    try:
        result = db.execute(text("""
            SELECT id, email, nombre, apellido, is_admin, is_active 
            FROM usuarios 
            WHERE email = 'itmaster@rapicreditca.com'
            LIMIT 1
        """))
        user = result.fetchone()
        
        if user:
            return {
                "status": "success", 
                "user": {
                    "id": user[0],
                    "email": user[1],
                    "nombre": user[2],
                    "apellido": user[3],
                    "is_admin": user[4],
                    "is_active": user[5]
                }
            }
        else:
            return {"status": "success", "message": "Usuario no encontrado"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/test-sqlalchemy-query")
def test_sqlalchemy_query(db: Session = Depends(get_db)):
    """Probar consulta con SQLAlchemy ORM"""
    try:
        # Consulta específica solo con columnas necesarias
        user = db.query(User.id, User.email, User.nombre, User.apellido, User.is_admin, User.is_active).filter(
            User.email == 'itmaster@rapicreditca.com'
        ).first()
        
        if user:
            return {
                "status": "success", 
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "nombre": user.nombre,
                    "apellido": user.apellido,
                    "is_admin": user.is_admin,
                    "is_active": user.is_active
                }
            }
        else:
            return {"status": "success", "message": "Usuario no encontrado"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
