#!/usr/bin/env python3
"""
Script para probar la conexión a la base de datos
"""
import os
import sys
from sqlalchemy import create_engine, text

# Añadir el directorio del backend al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_database_connection():
    """Prueba la conexión a la base de datos"""
    try:
        # Obtener DATABASE_URL del entorno
        database_url = os.getenv('DATABASE_URL')
        
        if not database_url:
            print("❌ DATABASE_URL no está configurada")
            return False
        
        print(f"🔗 Probando conexión a: {database_url.split('@')[0]}@***")
        
        # Crear engine
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0,
            pool_timeout=10,
            pool_recycle=300,
            connect_args={
                "connect_timeout": 10,
                "application_name": "test_connection"
            }
        )
        
        # Probar conexión
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            
            if row and row[0] == 1:
                print("✅ Conexión exitosa a la base de datos")
                return True
            else:
                print("❌ Respuesta inesperada de la base de datos")
                return False
                
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Probando conexión a base de datos...")
    success = test_database_connection()
    
    if success:
        print("🎉 Base de datos funcionando correctamente")
        sys.exit(0)
    else:
        print("💥 Base de datos no disponible")
        sys.exit(1)
