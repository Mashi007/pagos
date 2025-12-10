"""
Script para importar CSV directamente a PostgreSQL usando COPY
Solución definitiva para importar todos los registros
"""

import os
import sys
import pandas as pd
from urllib.parse import quote_plus, urlparse, urlunparse, unquote
from sqlalchemy import create_engine, text

# Obtener DATABASE_URL del entorno o desde settings
DATABASE_URL_RAW = None

# Primero intentar desde variables de entorno
try:
    DATABASE_URL_RAW = os.getenv("DATABASE_URL")
except:
    pass

# Si no está disponible, intentar desde settings
if not DATABASE_URL_RAW:
    try:
        # Agregar el directorio backend al path para importar settings
        backend_path = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
        if os.path.exists(backend_path):
            sys.path.insert(0, backend_path)
        from app.core.config import settings
        DATABASE_URL_RAW = getattr(settings, 'DATABASE_URL', None)
    except Exception as e:
        print(f"[WARNING] No se pudo cargar DATABASE_URL desde settings: {e}")

# Manejar encoding de DATABASE_URL correctamente
if DATABASE_URL_RAW:
    try:
        # Si es bytes, decodificar primero
        if isinstance(DATABASE_URL_RAW, bytes):
            try:
                DATABASE_URL_RAW = DATABASE_URL_RAW.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    DATABASE_URL_RAW = DATABASE_URL_RAW.decode('latin1', errors='replace')
                except:
                    DATABASE_URL_RAW = DATABASE_URL_RAW.decode('utf-8', errors='replace')
        
        # Parsear y reconstruir la URL de forma segura
        parsed = urlparse(str(DATABASE_URL_RAW))
        
        # Re-codificar componentes de manera segura
        if parsed.password:
            password = quote_plus(str(parsed.password), safe='')
        else:
            password = ''
        
        if parsed.username:
            username = quote_plus(str(parsed.username), safe='')
        else:
            username = ''
        
        # Reconstruir URL
        netloc = f"{username}:{password}@{parsed.hostname}" if username or password else parsed.hostname
        if parsed.port:
            netloc += f":{parsed.port}"
        
        DATABASE_URL = urlunparse((
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
    except Exception as e:
        print(f"[WARNING] Error procesando DATABASE_URL: {e}")
        DATABASE_URL = str(DATABASE_URL_RAW)
else:
    print("ERROR: DATABASE_URL no configurado")
    print("   Configura DATABASE_URL como variable de entorno o en backend/.env")
    sys.exit(1)

# Ruta del CSV
CSV_PATH = r"C:\Users\PORTATIL\Desktop\Sync\BD-Clientes(csv).csv"

def limpiar_valor(valor):
    """Limpia valores problemáticos"""
    if pd.isna(valor):
        return None
    if isinstance(valor, str):
        # Remover caracteres problemáticos
        valor = valor.strip()
        if valor == '':
            return None
        # Si es un número con formato de texto, limpiarlo
        if valor.replace('.', '').replace('-', '').isdigit():
            try:
                return float(valor)
            except:
                return valor
    return valor

def importar_csv():
    """Importa CSV a PostgreSQL"""
    try:
        # Leer CSV (intentar diferentes encodings)
        print(f"[INFO] Leyendo CSV: {CSV_PATH}")
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
        df = None
        
        for encoding in encodings:
            try:
                print(f"[INFO] Intentando encoding: {encoding}")
                df = pd.read_csv(
                    CSV_PATH,
                    encoding=encoding,
                    dtype=str,  # Leer todo como string primero
                    na_values=['', 'NULL', 'null', 'None'],
                    keep_default_na=False
                )
                print(f"[OK] CSV leído correctamente con encoding: {encoding}")
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            raise Exception("No se pudo leer el CSV con ningún encoding. Intentados: " + ", ".join(encodings))
        
        print(f"[INFO] Total filas en CSV: {len(df)}")
        print(f"[INFO] Columnas: {list(df.columns)}")
        
        # Limpiar nombres de columnas (remover espacios extra)
        df.columns = df.columns.str.strip()
        
        # Seleccionar solo las columnas necesarias
        columnas_necesarias = [
            'CLIENTE',
            'CEDULA IDENTIDAD',
            'MONTO CANCELADO CUOTA',
            'TOTAL FINANCIAMIENTO',
            'MODALIDAD FINANCIAMIENTO'
        ]
        
        # Verificar que existan las columnas
        columnas_faltantes = [c for c in columnas_necesarias if c not in df.columns]
        if columnas_faltantes:
            print(f"[ERROR] Columnas faltantes: {columnas_faltantes}")
            print(f"[INFO] Columnas disponibles: {list(df.columns)}")
            return False
        
        # Filtrar solo las columnas necesarias
        df = df[columnas_necesarias].copy()
        
        # Limpiar datos
        print("[INFO] Limpiando datos...")
        for col in df.columns:
            df[col] = df[col].apply(limpiar_valor)
        
        # Convertir columnas numéricas
        print("[INFO] Convirtiendo tipos de datos...")
        df['MONTO CANCELADO CUOTA'] = pd.to_numeric(df['MONTO CANCELADO CUOTA'], errors='coerce')
        df['TOTAL FINANCIAMIENTO'] = pd.to_numeric(df['TOTAL FINANCIAMIENTO'], errors='coerce')
        
        # Remover filas con valores críticos nulos
        df = df.dropna(subset=['CLIENTE', 'CEDULA IDENTIDAD'])
        
        print(f"[INFO] Filas válidas después de limpieza: {len(df)}")
        
        # Conectar a PostgreSQL usando SQLAlchemy (más robusto con encoding)
        print("[INFO] Conectando a PostgreSQL...")
        connect_args = {"client_encoding": "UTF8"}
        engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
        conn = engine.raw_connection()
        cur = conn.cursor()
        
        # Truncar tabla
        print("[INFO] Limpiando tabla bd_clientes_csv...")
        cur.execute("TRUNCATE TABLE bd_clientes_csv;")
        
        # Preparar datos para inserción
        print("[INFO] Preparando datos para inserción...")
        valores = []
        for _, row in df.iterrows():
            valores.append((
                str(row['CLIENTE'])[:200] if pd.notna(row['CLIENTE']) else None,
                str(row['CEDULA IDENTIDAD'])[:20] if pd.notna(row['CEDULA IDENTIDAD']) else None,
                None,  # MOVIL
                None,  # ESTADO DEL CASO
                None,  # MODELO VEHICULO
                None,  # ANALISTA
                None,  # CONCESIONARIO2
                None,  # No
                float(row['MONTO CANCELADO CUOTA']) if pd.notna(row['MONTO CANCELADO CUOTA']) else None,
                float(row['TOTAL FINANCIAMIENTO']) if pd.notna(row['TOTAL FINANCIAMIENTO']) else None,
                None,  # FECHA ENTREGA
                None,  # .
                str(row['MODALIDAD FINANCIAMIENTO'])[:50] if pd.notna(row['MODALIDAD FINANCIAMIENTO']) else None
            ))
        
        # Insertar datos usando execute_values
        from psycopg2.extras import execute_values
        print(f"[INFO] Insertando {len(valores)} registros...")
        insert_query = """
            INSERT INTO bd_clientes_csv (
                "CLIENTE", "CEDULA IDENTIDAD", "MOVIL", "ESTADO DEL CASO",
                "MODELO VEHICULO", "ANALISTA", "CONCESIONARIO2", "No",
                "MONTO CANCELADO CUOTA", "TOTAL FINANCIAMIENTO", "FECHA ENTREGA",
                ".", "MODALIDAD FINANCIAMIENTO"
            ) VALUES %s
        """
        
        execute_values(cur, insert_query, valores, page_size=1000)
        
        # Commit
        conn.commit()
        
        # Verificar
        cur.execute("SELECT COUNT(*) FROM bd_clientes_csv;")
        total = cur.fetchone()[0]
        
        print(f"[OK] Importación completada: {total} registros importados")
        
        cur.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error durante la importación: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("IMPORTACIÓN CSV A POSTGRESQL - SOLUCIÓN DEFINITIVA")
    print("=" * 60)
    
    if importar_csv():
        print("\n[OK] Proceso completado exitosamente")
        sys.exit(0)
    else:
        print("\n[ERROR] El proceso falló")
        sys.exit(1)

