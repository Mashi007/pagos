"""
Script de diagnóstico para verificar problemas con fechas en la importación de préstamos
"""
import sys
import io
from pathlib import Path
import csv
from datetime import datetime
from typing import Optional

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

csv_path = Path(r"C:\Users\PORTATIL\Desktop\Sync\pRESTAMO-2026.csv")

def convertir_fecha_mdy(fecha_str: Optional[str]) -> Optional[datetime]:
    """
    Convierte fecha de formato MM-DD-YYYY a datetime
    Ejemplo: '10-14-2024' -> datetime(2024, 10, 14)
    """
    if not fecha_str or not str(fecha_str).strip():
        return None
    
    fecha_str = str(fecha_str).strip()
    
    # Si ya está en formato YYYY-MM-DD, convertir directamente
    if '-' in fecha_str and len(fecha_str.split('-')[0]) == 4:
        try:
            return datetime.strptime(fecha_str, '%Y-%m-%d')
        except ValueError:
            pass
    
    # Intentar formato MM-DD-YYYY
    try:
        if '-' in fecha_str and len(fecha_str.split('-')[0]) == 2:
            return datetime.strptime(fecha_str, '%m-%d-%Y')
    except ValueError:
        pass
    
    # Intentar formato texto largo en español: 'viernes, octubre 18, 2024'
    try:
        if ',' in fecha_str:
            # Extraer la parte después de la coma: 'octubre 18, 2024'
            parte_fecha = fecha_str.split(', ', 1)[1] if ', ' in fecha_str else fecha_str.split(',')[1]
            parte_fecha = parte_fecha.strip()
            
            # Mapeo de meses en español a números
            meses_espanol = {
                'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
                'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
                'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
            }
            
            # Buscar el mes en español
            for mes_nombre, mes_num in meses_espanol.items():
                if mes_nombre in parte_fecha.lower():
                    # Reemplazar mes en español por número
                    parte_fecha = parte_fecha.lower().replace(mes_nombre, str(mes_num))
                    # Formato esperado: '10 18, 2024'
                    try:
                        return datetime.strptime(parte_fecha, '%m %d, %Y')
                    except ValueError:
                        # Intentar sin coma: '10 18 2024'
                        parte_fecha = parte_fecha.replace(',', '')
                        return datetime.strptime(parte_fecha, '%m %d %Y')
    except (ValueError, IndexError):
        pass
    
    return None

print("=" * 100)
print("DIAGNOSTICO DE FECHAS EN CSV DE PRESTAMOS")
print("=" * 100)

if not csv_path.exists():
    print(f"\nERROR: No se encontró el archivo: {csv_path}")
    sys.exit(1)

print(f"\nArchivo CSV: {csv_path}")

# Leer CSV
try:
    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
    csv_content = None
    encoding_usado = None
    
    for encoding in encodings:
        try:
            with open(csv_path, 'r', encoding=encoding) as f:
                csv_content = f.read()
            encoding_usado = encoding
            print(f"CSV leído con encoding: {encoding}")
            break
        except UnicodeDecodeError:
            continue
    
    if csv_content is None:
        raise Exception("No se pudo leer el CSV con ningún encoding")
    
    # Detectar delimitador
    primera_linea = csv_content.split('\n')[0]
    delimitador = ',' if ',' in primera_linea else ';'
    print(f"Delimitador detectado: '{delimitador}'")
    
    # Leer CSV
    reader = csv.DictReader(csv_content.splitlines(), delimiter=delimitador)
    
    # Obtener nombres de columnas
    columnas = reader.fieldnames
    print(f"\nColumnas encontradas ({len(columnas)}):")
    for i, col in enumerate(columnas, 1):
        print(f"  {i}. '{col}'")
    
    # Buscar columnas de fecha
    col_fecha_req = None
    col_fecha_apr = None
    
    for col in columnas:
        col_lower = col.lower().strip()
        if 'fecha_requerimiento' in col_lower or 'fecha requerimiento' in col_lower:
            col_fecha_req = col
        if 'fecha_aprobacion' in col_lower or 'fecha aprobacion' in col_lower:
            col_fecha_apr = col
    
    print(f"\nColumna fecha_requerimiento encontrada: '{col_fecha_req}'")
    print(f"Columna fecha_aprobacion encontrada: '{col_fecha_apr}'")
    
    # Analizar primeras 20 filas
    print(f"\n{'='*100}")
    print("ANALISIS DE PRIMERAS 20 FILAS")
    print(f"{'='*100}\n")
    
    filas_analizadas = 0
    errores_fecha_req = []
    errores_fecha_apr = []
    
    for idx, row in enumerate(reader, start=1):
        if idx > 20:
            break
        
        filas_analizadas += 1
        
        # Limpiar nombres de columnas (eliminar espacios)
        row_limpio = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items()}
        
        # Obtener valores de fecha
        fecha_req_raw = row_limpio.get(col_fecha_req, '') if col_fecha_req else ''
        fecha_apr_raw = row_limpio.get(col_fecha_apr, '') if col_fecha_apr else ''
        
        # Intentar convertir
        fecha_req_conv = convertir_fecha_mdy(fecha_req_raw)
        fecha_apr_conv = convertir_fecha_mdy(fecha_apr_raw)
        
        # Mostrar resultado
        print(f"Fila {idx}:")
        print(f"  fecha_requerimiento RAW: '{fecha_req_raw}' (tipo: {type(fecha_req_raw).__name__})")
        print(f"  fecha_requerimiento CONVERTIDA: {fecha_req_conv}")
        
        if fecha_req_raw and not fecha_req_conv:
            errores_fecha_req.append({
                'fila': idx,
                'valor': fecha_req_raw,
                'tipo': type(fecha_req_raw).__name__
            })
            print(f"  ⚠️ ERROR: No se pudo convertir fecha_requerimiento")
        
        if col_fecha_apr:
            print(f"  fecha_aprobacion RAW: '{fecha_apr_raw}' (tipo: {type(fecha_apr_raw).__name__})")
            print(f"  fecha_aprobacion CONVERTIDA: {fecha_apr_conv}")
            
            if fecha_apr_raw and not fecha_apr_conv:
                errores_fecha_apr.append({
                    'fila': idx,
                    'valor': fecha_apr_raw,
                    'tipo': type(fecha_apr_raw).__name__
                })
                print(f"  ⚠️ ERROR: No se pudo convertir fecha_aprobacion")
        
        print()
    
    # Resumen
    print(f"{'='*100}")
    print("RESUMEN")
    print(f"{'='*100}")
    print(f"Filas analizadas: {filas_analizadas}")
    print(f"Errores en fecha_requerimiento: {len(errores_fecha_req)}")
    print(f"Errores en fecha_aprobacion: {len(errores_fecha_apr)}")
    
    if errores_fecha_req:
        print(f"\nErrores fecha_requerimiento:")
        for err in errores_fecha_req[:10]:
            print(f"  Fila {err['fila']}: '{err['valor']}' (tipo: {err['tipo']})")
            # Mostrar representación hexadecimal para detectar caracteres ocultos
            print(f"    Hex: {err['valor'].encode('utf-8').hex()}")
    
    if errores_fecha_apr:
        print(f"\nErrores fecha_aprobacion:")
        for err in errores_fecha_apr[:10]:
            print(f"  Fila {err['fila']}: '{err['valor']}' (tipo: {err['tipo']})")
            print(f"    Hex: {err['valor'].encode('utf-8').hex()}")
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
