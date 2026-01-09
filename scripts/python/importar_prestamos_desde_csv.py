"""
Script para importar préstamos desde CSV con conversión correcta de fechas
Solución alternativa cuando DBeaver no reconoce las transformaciones
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

print("=" * 100)
print("IMPORTAR PRESTAMOS DESDE CSV")
print("=" * 100)

# ============================================================================
# CONFIGURACIÓN: Ruta del CSV
# ============================================================================
csv_path = Path(r"C:\Users\PORTATIL\Desktop\Sync\pRESTAMO-2026.csv")

if not csv_path.exists():
    print(f"\n❌ No se encontró el archivo: {csv_path}")
    print("   Por favor, modifica la variable 'csv_path' en el script con la ruta correcta")
    db.close()
    sys.exit(1)

print(f"\n📁 Archivo CSV: {csv_path}")
print(f"   Tamaño: {csv_path.stat().st_size / 1024:.2f} KB")

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

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

def convertir_monto(monto_str: Optional[str]) -> Optional[Decimal]:
    """Convierte string a Decimal, limpiando formato"""
    if not monto_str or str(monto_str).strip() == '':
        return None
    try:
        monto_limpio = str(monto_str).replace('$', '').replace(',', '').replace(' ', '').strip()
        return Decimal(monto_limpio)
    except:
        return None

def convertir_entero(valor_str: Optional[str]) -> Optional[int]:
    """Convierte string a entero"""
    if not valor_str or str(valor_str).strip() == '':
        return None
    try:
        return int(float(str(valor_str).replace(',', '').strip()))
    except:
        return None

# ============================================================================
# LEER CSV
# ============================================================================
print(f"\n📖 Leyendo CSV...")
prestamos_data = []

try:
    # Intentar diferentes encodings
    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
    csv_content = None
    
    for encoding in encodings:
        try:
            with open(csv_path, 'r', encoding=encoding) as f:
                csv_content = f.read()
            print(f"✅ CSV leído con encoding: {encoding}")
            break
        except UnicodeDecodeError:
            continue
    
    if csv_content is None:
        raise Exception("No se pudo leer el CSV con ningún encoding")
    
    # Detectar delimitador
    primera_linea = csv_content.split('\n')[0]
    delimitador = ',' if ',' in primera_linea else ';'
    
    # Leer CSV
    reader = csv.DictReader(csv_content.splitlines(), delimiter=delimitador)
    
    for row in reader:
        row_limpio = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items()}
        prestamos_data.append(row_limpio)
    
    print(f"✅ Filas leídas: {len(prestamos_data):,}")
    
    if len(prestamos_data) > 0:
        columnas = list(prestamos_data[0].keys())
        print(f"✅ Columnas encontradas ({len(columnas)}): {', '.join(columnas[:10])}...")
        
except Exception as e:
    print(f"❌ Error al leer CSV: {e}")
    import traceback
    traceback.print_exc()
    db.close()
    sys.exit(1)

# ============================================================================
# CARGAR MAPA DE CLIENTES EN MEMORIA (OPTIMIZACIÓN)
# ============================================================================
print(f"\n🔍 Cargando mapa de clientes en memoria...")
mapa_clientes = {}
try:
    resultado = db.execute(text("SELECT id, cedula FROM clientes"))
    for row in resultado:
        # Normalizar cédula (mayúsculas, sin espacios) para búsqueda consistente
        cedula_normalizada = str(row.cedula).strip().upper()
        mapa_clientes[cedula_normalizada] = row.id
        # También guardar la cédula original por si acaso
        if str(row.cedula).strip() != cedula_normalizada:
            mapa_clientes[str(row.cedula).strip()] = row.id
    print(f"✅ {len(mapa_clientes):,} clientes cargados en memoria")
except Exception as e:
    print(f"⚠️ Error al cargar clientes: {e}")
    mapa_clientes = {}

# ============================================================================
# IMPORTAR DATOS
# ============================================================================
print(f"\n📥 Importando préstamos...")

batch_size = 100
total_insertados = 0
total_errores = 0
errores_detalle = []

for i in range(0, len(prestamos_data), batch_size):
    batch = prestamos_data[i:i+batch_size]
    
    for idx, fila in enumerate(batch, start=i+1):
        try:
            # Extraer datos básicos
            id_prestamo = convertir_entero(fila.get('id'))
            cedula_raw = str(fila.get('cedula', '')).strip()  # Cédula original del CSV
            cedula = cedula_raw.upper()  # Normalizar a mayúsculas para búsqueda
            nombres = str(fila.get('nombres', '')).strip() if fila.get('nombres') else None
            
            # Convertir fechas
            fecha_requerimiento_str = fila.get('fecha_requerimiento', '')
            fecha_requerimiento = convertir_fecha_mdy(fecha_requerimiento_str)
            
            fecha_aprobacion_str = fila.get('fecha_aprobacion', '')
            fecha_aprobacion = convertir_fecha_mdy(fecha_aprobacion_str)
            
            # Convertir valores numéricos
            total_financiamiento = convertir_monto(fila.get('total_financiamiento'))
            numero_cuotas = convertir_entero(fila.get('numero_cuotas'))
            cuota_periodo = convertir_monto(fila.get('cuota_periodo'))
            
            # Validar campos obligatorios
            if not cedula:
                errores_detalle.append({
                    'fila': idx,
                    'error': 'Cédula vacía',
                    'datos': fila
                })
                total_errores += 1
                continue
            
            if not fecha_requerimiento:
                errores_detalle.append({
                    'fila': idx,
                    'error': f'Fecha requerimiento inválida: {fecha_requerimiento_str}',
                    'datos': fila
                })
                total_errores += 1
                continue
            
            # Preparar valores para INSERT
            valores = {
                'cedula': cedula,
                'nombres': nombres or 'Sin nombre',
                'total_financiamiento': total_financiamiento or 0,
                'fecha_requerimiento': fecha_requerimiento.date(),
                'modalidad_pago': str(fila.get('modalidad_pago', 'QUINCENAL')).strip(),
                'numero_cuotas': numero_cuotas or 0,
                'cuota_periodo': cuota_periodo or 0,
                'producto': str(fila.get('producto', '')).strip() or 'Sin producto',
                'producto_financiero': str(fila.get('producto_financiero', '')).strip() or 'Sin producto financiero',
                'estado': str(fila.get('estado', 'APROBADO')).strip(),
                'concesionario': str(fila.get('concesionario', '')).strip() if fila.get('concesionario') else None,
                'analista': str(fila.get('analista', '')).strip() if fila.get('analista') else None,
            }
            
            # Agregar fecha_aprobacion si está disponible (TIMESTAMP en BD, mantener datetime)
            if fecha_aprobacion:
                valores['fecha_aprobacion'] = fecha_aprobacion  # Mantener como datetime para TIMESTAMP
            
            # Buscar cliente_id por cédula (usando mapa en memoria - más rápido)
            # Intentar primero con cédula normalizada, luego con original
            cliente_id = mapa_clientes.get(cedula) or mapa_clientes.get(cedula_raw)
            
            # Validar que el cliente existe (cliente_id es NOT NULL en BD)
            if not cliente_id:
                errores_detalle.append({
                    'fila': idx,
                    'error': f'Cliente no encontrado para cédula: {cedula_raw}',
                    'datos': fila
                })
                total_errores += 1
                if total_errores <= 10:  # Mostrar solo primeros 10 errores
                    print(f"  ⚠️ Fila {idx}: Cliente no encontrado para cédula '{cedula_raw}'")
                continue
            
            valores['cliente_id'] = cliente_id
            
            # Construir INSERT
            if id_prestamo:
                # Si hay ID, intentar insertar con ID específico
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
                # Sin ID, dejar que la secuencia lo genere
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
            
            # Ejecutar INSERT
            db.execute(text(sql), valores)
            total_insertados += 1
            
            # Commit cada batch y mostrar progreso
            if total_insertados % batch_size == 0:
                db.commit()
                print(f"  Procesadas {total_insertados:,} filas...")
        
        except Exception as e:
            errores_detalle.append({
                'fila': idx,
                'error': str(e),
                'datos': fila
            })
            total_errores += 1
            # No hacer rollback aquí, solo continuar
            if total_errores <= 5:  # Mostrar solo primeros 5 errores en tiempo real
                print(f"  ERROR fila {idx}: {str(e)[:100]}")
            continue
    
    # Commit después de cada batch completo
    try:
        db.commit()
    except Exception as e:
        print(f"  Error en commit del batch: {e}")
        db.rollback()

# Commit final
try:
    db.commit()
    print(f"\n✅ Commit final realizado")
except Exception as e:
    print(f"\n❌ Error en commit final: {e}")
    db.rollback()

# ============================================================================
# RESUMEN
# ============================================================================
print("\n" + "=" * 100)
print("RESUMEN DE IMPORTACIÓN")
print("=" * 100)
print(f"✅ Total insertados: {total_insertados:,}")
print(f"❌ Total errores: {total_errores:,}")

if errores_detalle:
    print(f"\n⚠️ Primeros 10 errores:")
    for error in errores_detalle[:10]:
        print(f"  Fila {error['fila']}: {error['error']}")

# Verificar importación
print(f"\n📊 Verificando importación...")
resultado = db.execute(text("SELECT COUNT(*) FROM prestamos"))
total_prestamos = resultado.scalar()
print(f"✅ Total préstamos en BD: {total_prestamos:,}")

db.close()
print("\n✅ Proceso completado")
