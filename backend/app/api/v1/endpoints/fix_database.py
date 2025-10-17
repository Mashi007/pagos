# backend/app/api/v1/endpoints/fix_database.py
"""
Endpoint temporal para corregir problemas de base de datos
Solo para uso en desarrollo/producción cuando sea necesario
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/fix-cargo-column")
def fix_cargo_column(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Corregir columna cargo faltante en tabla usuarios
    Solo para administradores
    """
    # Verificar que el usuario sea admin
    if current_user.rol != "ADMIN":
        raise HTTPException(
            status_code=403, 
            detail="Solo administradores pueden ejecutar esta corrección"
        )
    
    try:
        # Verificar si la columna cargo existe
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'usuarios' 
            AND column_name = 'cargo'
        """))
        
        if not result.fetchone():
            # La columna no existe, agregarla
            db.execute(text("ALTER TABLE usuarios ADD COLUMN cargo VARCHAR(100)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_usuarios_cargo ON usuarios(cargo)"))
            db.commit()
            
            return {
                "success": True,
                "message": "✅ Columna 'cargo' agregada exitosamente a tabla 'usuarios'",
                "action": "column_added"
            }
        else:
            return {
                "success": True,
                "message": "ℹ️ Columna 'cargo' ya existe en tabla 'usuarios'",
                "action": "column_exists"
            }
            
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error aplicando corrección: {str(e)}"
        )

@router.get("/check-database-structure")
def check_database_structure(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Verificar estructura de la base de datos
    Solo para administradores
    """
    if current_user.rol != "ADMIN":
        raise HTTPException(
            status_code=403, 
            detail="Solo administradores pueden verificar la estructura"
        )
    
    try:
        # Verificar estructura de tabla usuarios
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'usuarios' 
            ORDER BY ordinal_position
        """))
        
        columns = []
        for row in result:
            columns.append({
                "column_name": row[0],
                "data_type": row[1],
                "is_nullable": row[2],
                "column_default": row[3]
            })
        
        return {
            "success": True,
            "table": "usuarios",
            "columns": columns,
            "total_columns": len(columns)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error verificando estructura: {str(e)}"
        )

@router.post("/fix-auditorias-usuario-id")
def fix_auditorias_usuario_id(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Corregir columna usuario_id faltante en tabla auditorias
    Solo para administradores
    """
    # Verificar que el usuario sea admin
    if current_user.rol != "ADMIN":
        raise HTTPException(
            status_code=403, 
            detail="Solo administradores pueden ejecutar esta corrección"
        )
    
    try:
        # Verificar si la columna usuario_id existe
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'auditorias' 
            AND column_name = 'usuario_id'
        """))
        
        if not result.fetchone():
            # La columna no existe, agregarla
            db.execute(text("ALTER TABLE auditorias ADD COLUMN usuario_id INTEGER"))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_auditorias_usuario_id ON auditorias(usuario_id)"))
            
            # Intentar agregar foreign key constraint
            try:
                db.execute(text("""
                    ALTER TABLE auditorias 
                    ADD CONSTRAINT fk_auditorias_usuario_id 
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
                """))
            except Exception as fk_error:
                print(f"Warning: No se pudo crear la foreign key constraint: {fk_error}")
            
            db.commit()
            
            return {
                "success": True,
                "message": "✅ Columna 'usuario_id' agregada exitosamente a tabla 'auditorias'",
                "action": "column_added"
            }
        else:
            return {
                "success": True,
                "message": "ℹ️ Columna 'usuario_id' ya existe en tabla 'auditorias'",
                "action": "column_exists"
            }
            
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error aplicando corrección: {str(e)}"
        )
