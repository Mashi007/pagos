"""
Genera un script SQL con INSERT statements para importar el CSV
Solución alternativa que evita problemas de encoding en DATABASE_URL
"""

import pandas as pd
import sys

# Ruta del CSV
CSV_PATH = r"C:\Users\PORTATIL\Desktop\Sync\BD-Clientes(csv).csv"
SQL_OUTPUT = r"scripts\sql\importar_datos_csv.sql"

def generar_sql():
    """Genera script SQL con INSERT statements"""
    try:
        # Leer CSV
        print(f"[INFO] Leyendo CSV: {CSV_PATH}")
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(
                    CSV_PATH,
                    encoding=encoding,
                    dtype=str,
                    na_values=['', 'NULL', 'null', 'None'],
                    keep_default_na=False
                )
                print(f"[OK] CSV leído con encoding: {encoding}")
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            raise Exception("No se pudo leer el CSV")
        
        print(f"[INFO] Total filas: {len(df)}")
        
        # Limpiar nombres de columnas
        df.columns = df.columns.str.strip()
        
        # Seleccionar columnas necesarias
        columnas_necesarias = [
            'CLIENTE',
            'CEDULA IDENTIDAD',
            'MONTO CANCELADO CUOTA',
            'TOTAL FINANCIAMIENTO',
            'MODALIDAD FINANCIAMIENTO'
        ]
        
        df = df[columnas_necesarias].copy()
        
        # Limpiar y convertir datos
        print("[INFO] Procesando datos...")
        df['MONTO CANCELADO CUOTA'] = pd.to_numeric(df['MONTO CANCELADO CUOTA'], errors='coerce')
        df['TOTAL FINANCIAMIENTO'] = pd.to_numeric(df['TOTAL FINANCIAMIENTO'], errors='coerce')
        df = df.dropna(subset=['CLIENTE', 'CEDULA IDENTIDAD'])
        
        print(f"[INFO] Filas válidas: {len(df)}")
        
        # Generar SQL
        print(f"[INFO] Generando script SQL: {SQL_OUTPUT}")
        with open(SQL_OUTPUT, 'w', encoding='utf-8') as f:
            f.write("-- ============================================\n")
            f.write("-- SCRIPT SQL PARA IMPORTAR CSV\n")
            f.write("-- ============================================\n\n")
            f.write("TRUNCATE TABLE bd_clientes_csv;\n\n")
            f.write("BEGIN;\n\n")
            
            # Generar INSERT statements en lotes de 1000
            batch_size = 1000
            total_batches = (len(df) + batch_size - 1) // batch_size
            
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(df))
                batch_df = df.iloc[start_idx:end_idx]
                
                f.write(f"-- Lote {batch_num + 1} de {total_batches} (filas {start_idx + 1} a {end_idx})\n")
                f.write("INSERT INTO bd_clientes_csv (\n")
                f.write('    "CLIENTE", "CEDULA IDENTIDAD", "MOVIL", "ESTADO DEL CASO",\n')
                f.write('    "MODELO VEHICULO", "ANALISTA", "CONCESIONARIO2", "No",\n')
                f.write('    "MONTO CANCELADO CUOTA", "TOTAL FINANCIAMIENTO", "FECHA ENTREGA",\n')
                f.write('    ".", "MODALIDAD FINANCIAMIENTO"\n')
                f.write(") VALUES\n")
                
                values = []
                for _, row in batch_df.iterrows():
                    cliente = str(row['CLIENTE'])[:200].replace("'", "''") if pd.notna(row['CLIENTE']) else 'NULL'
                    cedula = str(row['CEDULA IDENTIDAD'])[:20].replace("'", "''") if pd.notna(row['CEDULA IDENTIDAD']) else 'NULL'
                    monto_cuota = str(row['MONTO CANCELADO CUOTA']) if pd.notna(row['MONTO CANCELADO CUOTA']) else 'NULL'
                    total = str(row['TOTAL FINANCIAMIENTO']) if pd.notna(row['TOTAL FINANCIAMIENTO']) else 'NULL'
                    modalidad = str(row['MODALIDAD FINANCIAMIENTO'])[:50].replace("'", "''") if pd.notna(row['MODALIDAD FINANCIAMIENTO']) else 'NULL'
                    
                    values.append(
                        f"    ('{cliente}', '{cedula}', NULL, NULL, NULL, NULL, NULL, NULL, "
                        f"{monto_cuota}, {total}, NULL, NULL, '{modalidad}')"
                    )
                
                f.write(",\n".join(values))
                f.write(";\n\n")
            
            f.write("COMMIT;\n\n")
            f.write(f"-- Total: {len(df)} registros importados\n")
        
        print(f"[OK] Script SQL generado: {SQL_OUTPUT}")
        print(f"[OK] Total registros: {len(df)}")
        print(f"\n[INFO] Ejecuta el script en DBeaver:")
        print(f"    {SQL_OUTPUT}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("GENERAR SCRIPT SQL PARA IMPORTACIÓN")
    print("=" * 60)
    
    if generar_sql():
        print("\n[OK] Proceso completado")
        sys.exit(0)
    else:
        print("\n[ERROR] El proceso falló")
        sys.exit(1)

