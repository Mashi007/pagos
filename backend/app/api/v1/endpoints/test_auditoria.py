# backend/app/api/v1/endpoints/test_auditoria.py
"""
Endpoint de prueba para auditoría
Solo para diagnóstico de problemas
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.models.user import User
from app.utils.auditoria_helper import registrar_login_exitoso

router = APIRouter()

@router.post("/test-auditoria-login")
def test_auditoria_login(db: Session = Depends(get_db)):
    """Probar registro de auditoría de login"""
    try:
        # Obtener el usuario admin
        user = db.query(User).filter(User.email == 'itmaster@rapicreditca.com').first()
        
        if not user:
            return {"status": "error", "message": "Usuario no encontrado"}
        
        # Probar registro de auditoría
        auditoria = registrar_login_exitoso(
            db=db,
            usuario=user,
            ip_address="127.0.0.1",
            user_agent="Test Agent"
        )
        
        return {
            "status": "success", 
            "message": "Auditoría registrada exitosamente",
            "auditoria_id": auditoria.id,
            "usuario_email": auditoria.usuario_email
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "error_type": type(e).__name__}

@router.get("/test-auditoria-table-structure")
def test_auditoria_table_structure(db: Session = Depends(get_db)):
    """Verificar estructura de la tabla auditorias"""
    try:
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'auditorias'
            ORDER BY ordinal_position
        """)).fetchall()
        
        columns = [{"column_name": c[0], "data_type": c[1], "is_nullable": c[2]} for c in result]
        
        return {"status": "success", "table_name": "auditorias", "columns": columns}
    except Exception as e:
        return {"status": "error", "message": str(e)}
