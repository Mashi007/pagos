#!/usr/bin/env python3
"""
Script para ejecutar migración con configuración mínima
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os

def ejecutar_migracion():
    """Ejecutar migración para agregar columnas a clientes"""
    
    # CONFIGURACIÓN MÍNIMA - AJUSTAR SEGÚN TU BD
    DB_CONFIG = {
        'host': 'localhost',
        'port': 5432,
        'database': 'rapicredit',
        'user': 'postgres',
        'password': 'password'
    }
    
    try:
        # Conectar a la base de datos
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("Conectado a la base de datos")
        
        # Verificar si la tabla clientes existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'clientes'
            );
        """)
        
        tabla_existe = cursor.fetchone()[0]
        
        if not tabla_existe:
            print("ERROR: La tabla 'clientes' no existe")
            return False
            
        print("La tabla 'clientes' existe")
        
        # Verificar columnas existentes
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'clientes'
        """)
        
        columnas_existentes = [row[0] for row in cursor.fetchall()]
        print(f"Columnas existentes: {columnas_existentes}")
        
        # Agregar columna concesionario si no existe
        if 'concesionario' not in columnas_existentes:
            print("Agregando columna 'concesionario'...")
            cursor.execute("""
                ALTER TABLE clientes 
                ADD COLUMN concesionario VARCHAR(100);
            """)
            cursor.execute("""
                CREATE INDEX idx_clientes_concesionario 
                ON clientes (concesionario);
            """)
            print("Columna 'concesionario' agregada")
        else:
            print("Columna 'concesionario' ya existe")
            
        # Agregar columna analista si no existe
        if 'analista' not in columnas_existentes:
            print("Agregando columna 'analista'...")
            cursor.execute("""
                ALTER TABLE clientes 
                ADD COLUMN analista VARCHAR(100);
            """)
            cursor.execute("""
                CREATE INDEX idx_clientes_analista 
                ON clientes (analista);
            """)
            print("Columna 'analista' agregada")
        else:
            print("Columna 'analista' ya existe")
            
        # Verificar estructura final
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'clientes'
            ORDER BY ordinal_position;
        """)
        
        columnas_finales = [row[0] for row in cursor.fetchall()]
        print(f"Estructura final: {columnas_finales}")
        
        cursor.close()
        conn.close()
        
        print("Migracion completada exitosamente")
        return True
        
    except Exception as e:
        print(f"Error en migracion: {e}")
        return False

if __name__ == "__main__":
    print("Iniciando migracion de base de datos...")
    print("IMPORTANTE: Ajusta la configuracion DB_CONFIG en el script")
    print("Para local: host='localhost', database='rapicredit', user='postgres', password='password'")
    print()
    
    success = ejecutar_migracion()
    
    if success:
        print("Migracion exitosa - Las columnas fueron agregadas")
    else:
        print("Migracion fallida - Revisa la configuracion de BD")
