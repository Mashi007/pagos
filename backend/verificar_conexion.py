#!/usr/bin/env python3
"""
Script para verificar conexión a base de datos
"""
from app.db.session import engine
from sqlalchemy import text

def verificar_conexion():
    try:
        with engine.connect() as conn:
            result = conn.execute(text('SELECT current_database()'))
            db_name = result.fetchone()[0]
            print(f"✅ BD Conectada: {db_name}")
            
            # Verificar tabla clientes
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'clientes'"))
            columns = [row[0] for row in result.fetchall()]
            print(f"✅ Columnas en 'clientes': {columns}")
            
            # Verificar si existen las columnas problemáticas
            if 'concesionario' in columns:
                print("✅ Columna 'concesionario' existe")
            else:
                print("❌ Columna 'concesionario' NO existe")
                
            if 'analista' in columns:
                print("✅ Columna 'analista' existe")
            else:
                print("❌ Columna 'analista' NO existe")
                
            return True
            
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

if __name__ == "__main__":
    verificar_conexion()
