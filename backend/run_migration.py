"""
Script para ejecutar migracion SQL - Crear tabla csrf_tokens
"""

import os
import sys
from pathlib import Path

# Agregar backend al path
sys.path.insert(0, str(Path(__file__).parent))

# Importar configuracion y engine de BD
from app.core.config import settings
from app.core.database import engine
from sqlalchemy import text

def execute_migration():
    """Ejecutar script SQL para crear tabla csrf_tokens"""
    
    # Leer archivo SQL
    sql_file = Path(__file__).parent / "sql_migrate_csrf_tokens.sql"
    
    if not sql_file.exists():
        print(f"[ERROR] Archivo no encontrado: {sql_file}")
        return False
    
    print(f"[INFO] Leyendo SQL de: {sql_file}")
    
    with open(sql_file, "r", encoding="utf-8") as f:
        sql_content = f.read()
    
    # Separar comentarios y ejecutar
    statements = []
    current_stmt = ""
    
    for line in sql_content.split("\n"):
        line = line.strip()
        
        # Ignorar comentarios
        if line.startswith("--") or line.startswith("/*"):
            continue
        
        if line:
            current_stmt += line + " "
            
            # Si termina en ; es fin de statement
            if line.endswith(";"):
                statements.append(current_stmt.strip())
                current_stmt = ""
    
    if current_stmt:
        statements.append(current_stmt.strip())
    
    print(f"[INFO] {len(statements)} statements SQL encontrados")
    
    # Ejecutar statements
    try:
        with engine.connect() as connection:
            for i, stmt in enumerate(statements, 1):
                if stmt and not stmt.startswith("SELECT"):
                    print(f"[{i}/{len(statements)}] Ejecutando: {stmt[:80]}...")
                    connection.execute(text(stmt))
                elif stmt and stmt.startswith("SELECT"):
                    print(f"[{i}/{len(statements)}] Verificando: {stmt[:80]}...")
                    result = connection.execute(text(stmt))
                    row = result.fetchone()
                    if row:
                        print(f"    Resultado: {row[0]}")
            
            # Commit
            connection.commit()
            print("\n[OK] Transaccion completada exitosamente")
            
    except Exception as e:
        print(f"\n[ERROR] Error al ejecutar SQL: {type(e).__name__}: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    print("[*] MIGRACION SQL - Crear tabla csrf_tokens")
    print(f"[*] Base de datos: {settings.DATABASE_URL[:50]}...")
    print()
    
    success = execute_migration()
    
    if success:
        print("\n[EXITO] Tabla csrf_tokens creada correctamente")
        print("[INFO] Aplicacion lista para usar CSRF protection")
        sys.exit(0)
    else:
        print("\n[FALLO] Error al crear tabla csrf_tokens")
        sys.exit(1)
