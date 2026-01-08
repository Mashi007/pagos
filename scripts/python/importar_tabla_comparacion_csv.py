"""Importar tabla de comparación desde CSV usando Python"""
import sys
import io
from pathlib import Path
import csv
from decimal import Decimal

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("=" * 80)
print("IMPORTAR TABLA DE COMPARACION DESDE CSV")
print("=" * 80)

# Ruta del CSV
csv_path = Path(r"C:\Users\PORTATIL\Desktop\Sync\Tabla referencia.csv")

if not csv_path.exists():
    print(f"\n❌ No se encontró el archivo: {csv_path}")
    print("   Verifica la ruta del archivo CSV")
    db.close()
    sys.exit(1)

print(f"\n📁 Archivo CSV: {csv_path}")
print(f"   Tamaño: {csv_path.stat().st_size / 1024:.2f} KB")

# Leer CSV
print(f"\n📖 Leyendo CSV...")
tabla_externa = []

try:
    with open(csv_path, 'r', encoding='utf-8') as f:
        # Detectar delimitador
        primera_linea = f.readline()
        f.seek(0)
        
        delimitador = ',' if ',' in primera_linea else ';'
        reader = csv.DictReader(f, delimiter=delimitador)
        
        for row in reader:
            row_limpio = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items()}
            tabla_externa.append(row_limpio)
    
    print(f"✅ Filas leídas: {len(tabla_externa):,}")
    
    if len(tabla_externa) > 0:
        columnas = list(tabla_externa[0].keys())
        print(f"✅ Columnas encontradas ({len(columnas)}): {', '.join(columnas)}")
        
        # Verificar columnas requeridas (case-insensitive)
        columnas_lower = {k.lower(): k for k in columnas}  # Mapeo lowercase -> original
        columnas_requeridas = ['cedula', 'total_financiamiento', 'abonos']
        columnas_faltantes = []
        for col_req in columnas_requeridas:
            if col_req not in columnas_lower:
                columnas_faltantes.append(col_req)
        
        if columnas_faltantes:
            print(f"⚠️ Columnas faltantes: {', '.join(columnas_faltantes)}")
        else:
            print(f"✅ Todas las columnas requeridas están presentes")
            
except Exception as e:
    print(f"❌ Error al leer CSV: {e}")
    import traceback
    traceback.print_exc()
    db.close()
    sys.exit(1)

# Funciones auxiliares
def convertir_monto(monto_str):
    if not monto_str or str(monto_str).strip() == '':
        return None
    try:
        monto_limpio = str(monto_str).replace('$', '').replace(',', '').replace(' ', '').strip()
        return Decimal(monto_limpio)
    except:
        return None

def convertir_entero(valor_str):
    if not valor_str or str(valor_str).strip() == '':
        return None
    try:
        return int(float(str(valor_str).replace(',', '').strip()))
    except:
        return None

# Limpiar tabla
print(f"\n🧹 Limpiando tabla...")
try:
    db.execute(text("TRUNCATE TABLE tabla_comparacion_externa"))
    db.commit()
    print(f"✅ Tabla limpiada")
except Exception as e:
    print(f"⚠️ Error al limpiar tabla: {e}")
    db.rollback()

# Insertar datos en lotes
print(f"\n📥 Insertando datos en lotes de 100...")

batch_size = 100
total_insertadas = 0
total_errores = 0
errores_detalle = []

for i in range(0, len(tabla_externa), batch_size):
    batch = tabla_externa[i:i+batch_size]
    
    for fila in batch:
        try:
            cedula = str(fila.get('cedula', '')).strip()
            if not cedula:
                continue
            
            nombres = str(fila.get('nombres', '')).strip() if fila.get('nombres') else None
            estado = str(fila.get('estado', '')).strip() if fila.get('estado') else None
            fecha_base_calculo = str(fila.get('fecha_base_calculo', '')).strip() if fila.get('fecha_base_calculo') else None
            
            cuota_periodo = convertir_monto(fila.get('cuota_periodo'))
            total_financiamiento = convertir_monto(fila.get('total_financiamiento'))
            abonos = convertir_monto(fila.get('Abonos'))  # Nota: CSV tiene "Abonos" con mayúscula
            
            numero_cuotas = convertir_entero(fila.get('numero_cuotas'))
            modalidad_pago = str(fila.get('modalidad_pago', '')).strip() if fila.get('modalidad_pago') else None
            
            db.execute(text("""
                INSERT INTO tabla_comparacion_externa 
                    (cedula, nombres, estado, fecha_base_calculo, 
                     cuota_periodo, total_financiamiento, abonos, 
                     numero_cuotas, modalidad_pago)
                VALUES (:cedula, :nombres, :estado, :fecha_base_calculo,
                        :cuota_periodo, :total_financiamiento, :abonos,
                        :numero_cuotas, :modalidad_pago)
                ON CONFLICT (cedula) DO UPDATE SET
                    nombres = EXCLUDED.nombres,
                    estado = EXCLUDED.estado,
                    fecha_base_calculo = EXCLUDED.fecha_base_calculo,
                    cuota_periodo = EXCLUDED.cuota_periodo,
                    total_financiamiento = EXCLUDED.total_financiamiento,
                    abonos = EXCLUDED.abonos,
                    numero_cuotas = EXCLUDED.numero_cuotas,
                    modalidad_pago = EXCLUDED.modalidad_pago
            """), {
                'cedula': cedula,
                'nombres': nombres,
                'estado': estado,
                'fecha_base_calculo': fecha_base_calculo,
                'cuota_periodo': cuota_periodo,
                'total_financiamiento': total_financiamiento,
                'abonos': abonos,
                'numero_cuotas': numero_cuotas,
                'modalidad_pago': modalidad_pago
            })
            total_insertadas += 1
            
        except Exception as e:
            total_errores += 1
            errores_detalle.append({
                'cedula': fila.get('cedula', 'N/A'),
                'error': str(e)
            })
            if total_errores <= 10:  # Mostrar solo primeros 10 errores
                print(f"⚠️ Error en fila {i}: {e}")
            continue
    
    # Commit cada batch
    try:
        db.commit()
        if (i + batch_size) % 500 == 0 or (i + batch_size) >= len(tabla_externa):
            print(f"   Procesadas: {min(i + batch_size, len(tabla_externa)):,}/{len(tabla_externa):,} filas")
    except Exception as e:
        print(f"❌ Error en commit del batch: {e}")
        db.rollback()

# Resumen final
print(f"\n" + "=" * 80)
print(f"RESUMEN DE IMPORTACIÓN")
print("=" * 80)
print(f"✅ Filas insertadas exitosamente: {total_insertadas:,}")
print(f"❌ Errores encontrados: {total_errores:,}")

if errores_detalle and len(errores_detalle) > 0:
    print(f"\n⚠️ Primeros errores encontrados:")
    for err in errores_detalle[:5]:
        print(f"   - Cédula {err['cedula']}: {err['error']}")

# Verificar datos importados
print(f"\n🔍 Verificando datos importados...")
try:
    resultado = db.execute(text("""
        SELECT 
            COUNT(*) AS total_filas,
            COUNT(DISTINCT cedula) AS cedulas_unicas,
            SUM(total_financiamiento) AS total_financiamiento_sum,
            SUM(abonos) AS total_abonos_sum
        FROM tabla_comparacion_externa
    """))
    
    row = resultado.fetchone()
    total_filas, cedulas_unicas, total_fin_sum, total_abonos_sum = row
    
    print(f"✅ Total filas en tabla: {total_filas:,}")
    print(f"✅ Cédulas únicas: {cedulas_unicas:,}")
    print(f"✅ Total financiamiento: ${total_fin_sum:,.2f}" if total_fin_sum else "✅ Total financiamiento: $0.00")
    print(f"✅ Total abonos: ${total_abonos_sum:,.2f}" if total_abonos_sum else "✅ Total abonos: $0.00")
    
except Exception as e:
    print(f"⚠️ Error al verificar: {e}")

print("\n" + "=" * 80)
print("✅ Importación completada")
print("=" * 80)

db.close()
