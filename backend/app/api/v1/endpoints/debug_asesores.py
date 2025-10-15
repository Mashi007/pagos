"""
Endpoint de debug para investigar el problema con /asesores/activos
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.models.asesor import Asesor
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/debug-asesores-table")
def debug_asesores_table(db: Session = Depends(get_db)):
    """
    🔍 Debug: Verificar estructura y datos de tabla asesores
    """
    try:
        # 1. Verificar si la tabla existe
        result = db.execute(text("SELECT COUNT(*) as count FROM asesores"))
        count = result.fetchone()[0]
        
        # 2. Verificar estructura de la tabla
        result = db.execute(text("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'asesores' ORDER BY ordinal_position"))
        columns = result.fetchall()
        
        # 3. Verificar datos (si existen)
        asesores_data = []
        if count > 0:
            result = db.execute(text("SELECT id, nombre, apellido, especialidad, activo FROM asesores LIMIT 5"))
            asesores_data = result.fetchall()
        
        return {
            "message": "Debug info de tabla asesores",
            "table_exists": True,
            "total_records": count,
            "columns": [{"name": col[0], "type": col[1], "nullable": col[2]} for col in columns],
            "sample_data": [{"id": row[0], "nombre": row[1], "apellido": row[2], "especialidad": row[3], "activo": row[4]} for row in asesores_data] if asesores_data else [],
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error en debug asesores: {e}")
        return {
            "message": f"Error: {str(e)}",
            "table_exists": False,
            "status": "error"
        }

@router.get("/debug-asesores-query")
def debug_asesores_query(db: Session = Depends(get_db)):
    """
    🔍 Debug: Probar query específico del endpoint /activos
    """
    try:
        # Probar query exacto del endpoint
        query = db.query(Asesor).filter(Asesor.activo == True)
        asesores = query.all()
        
        # Probar to_dict() en cada asesor
        results = []
        for a in asesores:
            try:
                result = a.to_dict()
                results.append(result)
            except Exception as e:
                results.append({"error": f"Error en to_dict() para asesor {a.id}: {str(e)}"})
        
        return {
            "message": "Debug query asesores activos",
            "total_found": len(asesores),
            "results": results,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error en debug query: {e}")
        return {
            "message": f"Error en query: {str(e)}",
            "status": "error"
        }

@router.get("/debug-asesores-raw-sql")
def debug_asesores_raw_sql(db: Session = Depends(get_db)):
    """
    🔍 Debug: Query SQL directo
    """
    try:
        # Query SQL directo
        result = db.execute(text("SELECT id, nombre, apellido, especialidad, activo, created_at, updated_at FROM asesores WHERE activo = true"))
        rows = result.fetchall()
        
        return {
            "message": "Debug SQL directo",
            "total_found": len(rows),
            "data": [{"id": row[0], "nombre": row[1], "apellido": row[2], "especialidad": row[3], "activo": row[4], "created_at": str(row[5]), "updated_at": str(row[6])} for row in rows],
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error en debug SQL: {e}")
        return {
            "message": f"Error en SQL: {str(e)}",
            "status": "error"
        }
