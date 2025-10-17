# backend/app/api/v1/endpoints/test_auth.py
"""
Endpoint temporal para probar autenticación sin dependencias complejas
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()

@router.get("/test-db-connection")
def test_db_connection(db: Session = Depends(get_db)):
    """Probar conexión a base de datos"""
    try:
        result = db.execute(text("SELECT 1 as test"))
        return {"status": "success", "message": "Database connection OK", "test": result.fetchone()[0]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/test-user-table")
def test_user_table(db: Session = Depends(get_db)):
    """Probar estructura de tabla usuarios"""
    try:
        # Verificar estructura de tabla usuarios
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'usuarios' 
            ORDER BY ordinal_position
        """))
        
        columns = []
        for row in result:
            columns.append({
                "column_name": row[0],
                "data_type": row[1],
                "is_nullable": row[2]
            })
        
        return {"status": "success", "columns": columns}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/test-user-query")
def test_user_query(db: Session = Depends(get_db)):
    """Probar consulta simple de usuarios"""
    try:
        result = db.execute(text("SELECT id, email, nombre FROM usuarios LIMIT 1"))
        user = result.fetchone()
        
        if user:
            return {"status": "success", "user": {"id": user[0], "email": user[1], "nombre": user[2]}}
        else:
            return {"status": "success", "message": "No users found"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
