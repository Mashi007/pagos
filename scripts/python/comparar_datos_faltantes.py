"""Comparar datos pegados con la base de datos para identificar filas faltantes"""
import sys
import io
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from app.db.session import SessionLocal
from sqlalchemy import text

def convertir_monto(valor):
    """Convertir valor a Decimal, limpiando formato"""
    if not valor or valor == '' or valor == 'NULL':
        return None
    try:
        # Remover $, comas, espacios
        valor_limpio = str(valor).replace('$', '').replace(',', '').replace(' ', '').strip()
        if not valor_limpio or valor_limpio == '':
            return None
        from decimal import Decimal
        return Decimal(valor_limpio)
    except:
        return None

def convertir_entero(valor):
    """Convertir a entero"""
    if not valor or valor == '' or valor == 'NULL':
        return None
    try:
        return int(str(valor).strip())
    except:
        return None

def procesar_datos_pegados():
    """Procesar datos pegados desde stdin o archivo"""
    print("=" * 80)
    print("COMPARACIÓN DE DATOS PARA IDENTIFICAR FILAS FALTANTES")
    print("=" * 80)
    print("")
    print("Pega los datos aquí (formato CSV o tabulado).")
    print("Presiona Ctrl+Z (Windows) o Ctrl+D (Linux) seguido de Enter para terminar.")
    print("O escribe 'FIN' en una línea nueva para terminar.")
    print("")
    print("-" * 80)
    
    lineas = []
    try:
        while True:
            linea = input()
            if linea.strip().upper() == 'FIN':
                break
            lineas.append(linea)
    except EOFError:
        pass
    
    if not lineas:
        print("❌ No se recibieron datos")
        return
    
    print(f"\n✅ Se recibieron {len(lineas)} líneas de datos")
    print("")
    
    # Procesar datos
    datos_procesados = []
    for i, linea in enumerate(lineas, 1):
        # Intentar separar por tab o coma
        if '\t' in linea:
            campos = linea.split('\t')
        else:
            campos = linea.split(',')
        
        # Limpiar campos
        campos = [c.strip() for c in campos]
        
        if len(campos) < 2:
            continue
        
        # Asumir formato: cedula, nombres, estado, fecha_base_calculo, cuota_periodo, total_financiamiento, abonos, numero_cuotas, modalidad_pago
        dato = {
            'cedula': campos[0] if len(campos) > 0 else None,
            'nombres': campos[1] if len(campos) > 1 else None,
            'estado': campos[2] if len(campos) > 2 else None,
            'fecha_base_calculo': campos[3] if len(campos) > 3 else None,
            'cuota_periodo': convertir_monto(campos[4]) if len(campos) > 4 else None,
            'total_financiamiento': convertir_monto(campos[5]) if len(campos) > 5 else None,
            'abonos': convertir_monto(campos[6]) if len(campos) > 6 else None,
            'numero_cuotas': convertir_entero(campos[7]) if len(campos) > 7 else None,
            'modalidad_pago': campos[8] if len(campos) > 8 else None,
        }
        
        if dato['cedula']:
            datos_procesados.append(dato)
    
    print(f"✅ Se procesaron {len(datos_procesados)} registros válidos")
    print("")
    
    # Comparar con base de datos
    db = SessionLocal()
    try:
        print("=" * 80)
        print("COMPARANDO CON BASE DE DATOS...")
        print("=" * 80)
        print("")
        
        faltantes = []
        encontrados = []
        
        for dato in datos_procesados:
            cedula = dato['cedula']
            
            # Buscar en base de datos por cedula y otros campos clave
            query = text("""
                SELECT COUNT(*) 
                FROM tabla_comparacion_externa 
                WHERE cedula = :cedula
            """)
            
            resultado = db.execute(query, {'cedula': cedula})
            count = resultado.fetchone()[0]
            
            if count == 0:
                faltantes.append(dato)
            else:
                encontrados.append(cedula)
        
        # Mostrar resultados
        print(f"Total registros procesados: {len(datos_procesados)}")
        print(f"Registros encontrados en BD: {len(encontrados)}")
        print(f"Registros FALTANTES: {len(faltantes)}")
        print("")
        
        if faltantes:
            print("=" * 80)
            print("REGISTROS FALTANTES:")
            print("=" * 80)
            print("")
            
            for i, dato in enumerate(faltantes, 1):
                print(f"{i}. Cédula: {dato['cedula']}")
                print(f"   Nombres: {dato['nombres']}")
                print(f"   Total Financiamiento: {dato['total_financiamiento']}")
                print(f"   Abonos: {dato['abonos']}")
                print("")
            
            print("=" * 80)
            print(f"TOTAL FALTANTES: {len(faltantes)}")
            print("=" * 80)
        else:
            print("✅ Todos los registros están en la base de datos")
        
        print("")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    procesar_datos_pegados()
