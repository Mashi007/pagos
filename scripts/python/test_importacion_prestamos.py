"""
Test de importación con mejor manejo de errores
"""
import sys
import io
from pathlib import Path
import csv
from decimal import Decimal
from datetime import datetime
from typing import Optional

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

csv_path = Path(r"C:\Users\PORTATIL\Desktop\Sync\pRESTAMO-2026.csv")

def convertir_fecha_mdy(fecha_str: Optional[str]) -> Optional[datetime]:
    if not fecha_str or not str(fecha_str).strip():
        return None
    fecha_str = str(fecha_str).strip()
    if '-' in fecha_str and len(fecha_str.split('-')[0]) == 4:
        try:
            return datetime.strptime(fecha_str, '%Y-%m-%d')
        except ValueError:
            pass
    try:
        if '-' in fecha_str and len(fecha_str.split('-')[0]) == 2:
            return datetime.strptime(fecha_str, '%m-%d-%Y')
    except ValueError:
        pass
    return None

def convertir_monto(monto_str: Optional[str]) -> Optional[Decimal]:
    if not monto_str or str(monto_str).strip() == '':
        return None
    try:
        monto_limpio = str(monto_str).replace('$', '').replace(',', '').replace(' ', '').strip()
        return Decimal(monto_limpio)
    except:
        return None

def convertir_entero(valor_str: Optional[str]) -> Optional[int]:
    if not valor_str or str(valor_str).strip() == '':
        return None
    try:
        return int(float(str(valor_str).replace(',', '').strip()))
    except:
        return None

print("=" * 100)
print("TEST DE IMPORTACION - SOLO PRIMERAS 5 FILAS")
print("=" * 100)

# Leer CSV
encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
csv_content = None

for encoding in encodings:
    try:
        with open(csv_path, 'r', encoding=encoding) as f:
            csv_content = f.read()
        print(f"CSV leído con encoding: {encoding}")
        break
    except UnicodeDecodeError:
        continue

primera_linea = csv_content.split('\n')[0]
delimitador = ',' if ',' in primera_linea else ';'

reader = csv.DictReader(csv_content.splitlines(), delimiter=delimitador)
columnas = reader.fieldnames
print(f"Columnas: {columnas}")

# Cargar mapa de clientes
mapa_clientes = {}
try:
    resultado = db.execute(text("SELECT id, cedula FROM clientes"))
    for row in resultado:
        mapa_clientes[row.cedula] = row.id
    print(f"Clientes cargados: {len(mapa_clientes):,}")
except Exception as e:
    print(f"Error al cargar clientes: {e}")

# Procesar solo primeras 5 filas
print(f"\nProcesando primeras 5 filas...\n")

for idx, fila in enumerate(reader, start=1):
    if idx > 5:
        break
    
    print(f"{'='*80}")
    print(f"FILA {idx}")
    print(f"{'='*80}")
    print(f"Datos CSV: {fila}")
    
    try:
        # Limpiar nombres de columnas
        row_limpio = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in fila.items()}
        print(f"Columnas después de limpiar: {list(row_limpio.keys())}")
        
        # Extraer datos
        id_prestamo = convertir_entero(row_limpio.get('id'))
        cedula = str(row_limpio.get('cedula', '')).strip()
        nombres = str(row_limpio.get('nombres', '')).strip() if row_limpio.get('nombres') else None
        
        print(f"id_prestamo: {id_prestamo}")
        print(f"cedula: '{cedula}'")
        print(f"nombres: '{nombres}'")
        
        # Convertir fechas
        fecha_requerimiento_str = row_limpio.get('fecha_requerimiento', '')
        fecha_requerimiento = convertir_fecha_mdy(fecha_requerimiento_str)
        
        fecha_aprobacion_str = row_limpio.get('fecha_aprobacion', '')
        fecha_aprobacion = convertir_fecha_mdy(fecha_aprobacion_str)
        
        print(f"fecha_requerimiento: '{fecha_requerimiento_str}' -> {fecha_requerimiento}")
        print(f"fecha_aprobacion: '{fecha_aprobacion_str}' -> {fecha_aprobacion}")
        
        # Validaciones
        if not cedula:
            print("ERROR: Cédula vacía")
            continue
        
        if not fecha_requerimiento:
            print(f"ERROR: Fecha requerimiento inválida: '{fecha_requerimiento_str}'")
            continue
        
        # Preparar valores
        valores = {
            'cedula': cedula,
            'nombres': nombres or 'Sin nombre',
            'total_financiamiento': convertir_monto(row_limpio.get('total_financiamiento')) or 0,
            'fecha_requerimiento': fecha_requerimiento.date(),
            'modalidad_pago': str(row_limpio.get('modalidad_pago', 'QUINCENAL')).strip(),
            'numero_cuotas': convertir_entero(row_limpio.get('numero_cuotas')) or 0,
            'cuota_periodo': convertir_monto(row_limpio.get('cuota_periodo')) or 0,
            'producto': str(row_limpio.get('producto', '')).strip() or 'Sin producto',
            'producto_financiero': str(row_limpio.get('producto_financiero', '')).strip() or 'Sin producto financiero',
            'estado': str(row_limpio.get('estado', 'APROBADO')).strip(),
            'concesionario': str(row_limpio.get('concesionario', '')).strip() if row_limpio.get('concesionario') else None,
            'analista': str(row_limpio.get('analista', '')).strip() if row_limpio.get('analista') else None,
        }
        
        if fecha_aprobacion:
            valores['fecha_aprobacion'] = fecha_aprobacion
        
        cliente_id = mapa_clientes.get(cedula)
        valores['cliente_id'] = cliente_id
        
        print(f"\nValores preparados: {valores}")
        
        # Construir SQL
        if id_prestamo:
            sql = """
                INSERT INTO prestamos (
                    id, cliente_id, cedula, nombres, total_financiamiento,
                    fecha_requerimiento, modalidad_pago, numero_cuotas, cuota_periodo,
                    producto, producto_financiero, estado, fecha_aprobacion,
                    concesionario, analista
                ) VALUES (
                    :id, :cliente_id, :cedula, :nombres, :total_financiamiento,
                    :fecha_requerimiento, :modalidad_pago, :numero_cuotas, :cuota_periodo,
                    :producto, :producto_financiero, :estado, :fecha_aprobacion,
                    :concesionario, :analista
                )
                ON CONFLICT (id) DO UPDATE SET
                    cedula = EXCLUDED.cedula,
                    nombres = EXCLUDED.nombres,
                    total_financiamiento = EXCLUDED.total_financiamiento,
                    fecha_requerimiento = EXCLUDED.fecha_requerimiento,
                    modalidad_pago = EXCLUDED.modalidad_pago,
                    numero_cuotas = EXCLUDED.numero_cuotas,
                    cuota_periodo = EXCLUDED.cuota_periodo,
                    producto = EXCLUDED.producto,
                    producto_financiero = EXCLUDED.producto_financiero,
                    estado = EXCLUDED.estado,
                    fecha_aprobacion = EXCLUDED.fecha_aprobacion,
                    concesionario = EXCLUDED.concesionario,
                    analista = EXCLUDED.analista
            """
            valores['id'] = id_prestamo
        else:
            sql = """
                INSERT INTO prestamos (
                    cliente_id, cedula, nombres, total_financiamiento,
                    fecha_requerimiento, modalidad_pago, numero_cuotas, cuota_periodo,
                    producto, producto_financiero, estado, fecha_aprobacion,
                    concesionario, analista
                ) VALUES (
                    :cliente_id, :cedula, :nombres, :total_financiamiento,
                    :fecha_requerimiento, :modalidad_pago, :numero_cuotas, :cuota_periodo,
                    :producto, :producto_financiero, :estado, :fecha_aprobacion,
                    :concesionario, :analista
                )
            """
        
        print(f"\nEjecutando SQL...")
        print(f"SQL: {sql[:200]}...")
        
        # Ejecutar
        db.execute(text(sql), valores)
        db.commit()
        
        print(f"✅ FILA {idx} INSERTADA CORRECTAMENTE")
        
    except Exception as e:
        print(f"❌ ERROR en fila {idx}: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()

# Verificar
resultado = db.execute(text("SELECT COUNT(*) FROM prestamos"))
total = resultado.scalar()
print(f"\n{'='*80}")
print(f"Total préstamos en BD después del test: {total:,}")
print(f"{'='*80}")

db.close()
