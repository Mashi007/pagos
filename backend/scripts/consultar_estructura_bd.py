#!/usr/bin/env python3
"""
Script para consultar la estructura real de la tabla usuarios
"""
import psycopg2
import os
from urllib.parse import urlparse

def conectar_bd():
    """Conectar a la base de datos usando DATABASE_URL"""
    try:
        # Intentar obtener DATABASE_URL del entorno
        database_url = os.getenv('DATABASE_URL')
        
        if not database_url:
            print("ERROR: Variable DATABASE_URL no encontrada")
            print("Configura la variable de entorno DATABASE_URL")
            return None
        
        # Parsear la URL
        parsed = urlparse(database_url)
        
        # Conectar
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path[1:],  # Remover el '/' inicial
            user=parsed.username,
            password=parsed.password,
            sslmode='require'
        )
        
        return conn
        
    except Exception as e:
        print(f"ERROR conectando a BD: {e}")
        return None

def consultar_estructura():
    """Consultar estructura de la tabla usuarios"""
    conn = conectar_bd()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        print("ESTRUCTURA DE LA TABLA USUARIOS")
        print("=" * 50)
        
        # 1. Ver todas las columnas
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length
            FROM information_schema.columns 
            WHERE table_name = 'usuarios' 
            ORDER BY ordinal_position
        """)
        
        columnas = cursor.fetchall()
        
        print("COLUMNAS ENCONTRADAS:")
        print("-" * 30)
        for col in columnas:
            nombre, tipo, nullable, default, max_length = col
            print(f"Campo: {nombre}")
            print(f"  Tipo: {tipo}")
            print(f"  Nullable: {nullable}")
            print(f"  Default: {default}")
            print(f"  Longitud: {max_length}")
            print()
        
        # 2. Verificar campos específicos
        print("VERIFICACIÓN DE CAMPOS ESPECÍFICOS:")
        print("-" * 40)
        
        campos_a_verificar = ['nombre', 'apellido', 'full_name', 'cargo', 'email', 'rol']
        
        for campo in campos_a_verificar:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'usuarios' AND column_name = %s
                )
            """, (campo,))
            
            existe = cursor.fetchone()[0]
            print(f"{campo}: {'SÍ' if existe else 'NO'}")
        
        # 3. Ver datos de ejemplo
        print("\nDATOS DE EJEMPLO:")
        print("-" * 20)
        
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        total = cursor.fetchone()[0]
        print(f"Total usuarios: {total}")
        
        if total > 0:
            cursor.execute("SELECT * FROM usuarios LIMIT 1")
            usuario = cursor.fetchone()
            
            # Obtener nombres de columnas
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'usuarios' 
                ORDER BY ordinal_position
            """)
            nombres_columnas = [row[0] for row in cursor.fetchall()]
            
            print("\nPrimer usuario:")
            for i, valor in enumerate(usuario):
                if i < len(nombres_columnas):
                    print(f"  {nombres_columnas[i]}: {valor}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"ERROR en consulta: {e}")

def main():
    """Función principal"""
    print("CONSULTANDO ESTRUCTURA DE BASE DE DATOS")
    print("=" * 60)
    
    consultar_estructura()

if __name__ == "__main__":
    main()
