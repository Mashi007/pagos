"""
Script para revisar y procesar préstamos que fallaron en la generación de cuotas.

Uso:
    python scripts/python/Revisar_Prestamos_Fallidos.py
    python scripts/python/Revisar_Prestamos_Fallidos.py --intentar-generar
"""

import os
import sys
import argparse
from datetime import date, datetime, timedelta
from decimal import Decimal
from dateutil.relativedelta import relativedelta

# Manejar encoding para Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Agregar el directorio del backend al path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend"))
sys.path.insert(0, backend_dir)

from sqlalchemy import text
from app.db.session import SessionLocal

# IDs de préstamos que fallaron según el resumen
# Nota: 4468, 4475, 4476 ya tienen cuotas, solo 4519 y 4522 necesitan generación
PRESTAMOS_FALLIDOS = [4519, 4522]


def revisar_prestamo(db, prestamo_id: int):
    """Revisa un préstamo en detalle y muestra información completa"""
    print(f"\n{'='*80}")
    print(f"REVISANDO PRÉSTAMO ID: {prestamo_id}")
    print(f"{'='*80}")
    
    # Obtener información del préstamo
    query = text("""
        SELECT 
            id, cedula, estado, fecha_base_calculo, numero_cuotas,
            total_financiamiento, cuota_periodo, tasa_interes, modalidad_pago
        FROM prestamos
        WHERE id = :prestamo_id
    """)
    
    result = db.execute(query, {"prestamo_id": prestamo_id})
    row = result.fetchone()
    
    if not row:
        print(f"❌ Préstamo {prestamo_id} no encontrado")
        return None
    
    prestamo = {
        'id': row[0],
        'cedula': row[1],
        'estado': row[2],
        'fecha_base_calculo': row[3],
        'numero_cuotas': row[4],
        'total_financiamiento': row[5],
        'cuota_periodo': row[6],
        'tasa_interes': row[7],
        'modalidad_pago': row[8]
    }
    
    # Mostrar información
    print(f"\n📋 Información del Préstamo:")
    print(f"   ID: {prestamo['id']}")
    print(f"   Cédula: {prestamo['cedula']}")
    print(f"   Estado: {prestamo['estado']}")
    print(f"   Fecha Base Cálculo: {prestamo['fecha_base_calculo']} (tipo: {type(prestamo['fecha_base_calculo'])})")
    print(f"   Número de Cuotas: {prestamo['numero_cuotas']} (tipo: {type(prestamo['numero_cuotas'])})")
    print(f"   Total Financiamiento: {prestamo['total_financiamiento']} (tipo: {type(prestamo['total_financiamiento'])})")
    print(f"   Cuota Período: {prestamo['cuota_periodo']} (tipo: {type(prestamo['cuota_periodo'])})")
    print(f"   Tasa Interés: {prestamo['tasa_interes']} (tipo: {type(prestamo['tasa_interes'])})")
    print(f"   Modalidad Pago: {prestamo['modalidad_pago']}")
    
    # Validaciones
    print(f"\n🔍 Validaciones:")
    errores = []
    
    if prestamo['fecha_base_calculo'] is None:
        errores.append("❌ fecha_base_calculo es NULL")
    else:
        print(f"   ✓ fecha_base_calculo: {prestamo['fecha_base_calculo']}")
    
    if prestamo['numero_cuotas'] is None or prestamo['numero_cuotas'] <= 0:
        errores.append(f"❌ numero_cuotas inválido: {prestamo['numero_cuotas']}")
    else:
        print(f"   ✓ numero_cuotas: {prestamo['numero_cuotas']}")
    
    if prestamo['total_financiamiento'] is None or prestamo['total_financiamiento'] <= 0:
        errores.append(f"❌ total_financiamiento inválido: {prestamo['total_financiamiento']}")
    else:
        print(f"   ✓ total_financiamiento: {prestamo['total_financiamiento']}")
    
    if prestamo['cuota_periodo'] is None or prestamo['cuota_periodo'] <= 0:
        errores.append(f"❌ cuota_periodo inválido: {prestamo['cuota_periodo']}")
    else:
        print(f"   ✓ cuota_periodo: {prestamo['cuota_periodo']}")
    
    if prestamo['modalidad_pago'] not in ['MENSUAL', 'QUINCENAL', 'SEMANAL']:
        errores.append(f"❌ modalidad_pago inválida: {prestamo['modalidad_pago']}")
    else:
        print(f"   ✓ modalidad_pago: {prestamo['modalidad_pago']}")
    
    if errores:
        print(f"\n⚠️ ERRORES ENCONTRADOS:")
        for error in errores:
            print(f"   {error}")
        return prestamo
    
    # Verificar cuotas existentes
    query_cuotas = text("SELECT COUNT(*) FROM cuotas WHERE prestamo_id = :prestamo_id")
    result_cuotas = db.execute(query_cuotas, {"prestamo_id": prestamo_id})
    num_cuotas = result_cuotas.scalar()
    
    print(f"\n📊 Cuotas Existentes: {num_cuotas}")
    
    if num_cuotas > 0:
        query_detalle = text("""
            SELECT numero_cuota, fecha_vencimiento, monto_cuota, total_pagado, estado
            FROM cuotas
            WHERE prestamo_id = :prestamo_id
            ORDER BY numero_cuota
            LIMIT 5
        """)
        result_detalle = db.execute(query_detalle, {"prestamo_id": prestamo_id})
        print(f"   Primeras cuotas:")
        for row in result_detalle:
            print(f"      Cuota {row[0]}: {row[1]} - ${row[2]:.2f} - Pagado: ${row[3]:.2f} - {row[4]}")
    
    return prestamo


def intentar_generar_cuotas(db, prestamo_info: dict):
    """Intenta generar cuotas para un préstamo con manejo detallado de errores"""
    prestamo_id = prestamo_info['id']
    
    print(f"\n{'='*80}")
    print(f"INTENTANDO GENERAR CUOTAS PARA PRÉSTAMO {prestamo_id}")
    print(f"{'='*80}")
    
    try:
        # Convertir a tipos correctos
        fecha_base = prestamo_info['fecha_base_calculo']
        # Manejar timestamps en milisegundos (problema común en la BD)
        if isinstance(fecha_base, (int, float)) and fecha_base > 1000000000000:
            # Es un timestamp en milisegundos
            fecha_base = datetime.fromtimestamp(fecha_base / 1000).date()
        elif isinstance(fecha_base, str):
            # Intentar parsear como ISO o timestamp
            try:
                fecha_base = datetime.fromisoformat(fecha_base).date()
            except ValueError:
                # Intentar como timestamp en milisegundos
                try:
                    timestamp_ms = int(fecha_base)
                    if timestamp_ms > 1000000000000:
                        fecha_base = datetime.fromtimestamp(timestamp_ms / 1000).date()
                except (ValueError, TypeError):
                    raise ValueError(f"No se pudo convertir fecha_base_calculo: {fecha_base}")
        elif isinstance(fecha_base, datetime):
            fecha_base = fecha_base.date()
        
        numero_cuotas = int(prestamo_info['numero_cuotas'])
        total_financiamiento = Decimal(str(prestamo_info['total_financiamiento']))
        cuota_periodo = Decimal(str(prestamo_info['cuota_periodo']))
        modalidad_pago = str(prestamo_info['modalidad_pago'])
        tasa_interes = Decimal(str(prestamo_info['tasa_interes'] or 0))
        
        print(f"\n📝 Datos preparados:")
        print(f"   fecha_base: {fecha_base} (tipo: {type(fecha_base)})")
        print(f"   numero_cuotas: {numero_cuotas} (tipo: {type(numero_cuotas)})")
        print(f"   total_financiamiento: {total_financiamiento} (tipo: {type(total_financiamiento)})")
        print(f"   cuota_periodo: {cuota_periodo} (tipo: {type(cuota_periodo)})")
        print(f"   modalidad_pago: {modalidad_pago}")
        print(f"   tasa_interes: {tasa_interes}")
        
        # Calcular intervalo
        intervalos = {
            "MENSUAL": 30,
            "QUINCENAL": 15,
            "SEMANAL": 7,
        }
        intervalo_dias = intervalos.get(modalidad_pago, 30)
        
        # Tasa mensual
        if tasa_interes == Decimal("0.00"):
            tasa_mensual = Decimal("0.00")
        else:
            tasa_mensual = tasa_interes / Decimal(100) / Decimal(12)
        
        # Eliminar cuotas existentes si las hay
        db.execute(text("DELETE FROM cuotas WHERE prestamo_id = :prestamo_id"), 
                   {"prestamo_id": prestamo_id})
        print(f"\n🗑️  Cuotas existentes eliminadas (si las había)")
        
        # Generar cuotas
        saldo_capital = total_financiamiento
        cuotas_insertadas = 0
        
        print(f"\n🔄 Generando {numero_cuotas} cuotas...")
        
        for numero_cuota in range(1, numero_cuotas + 1):
            # Calcular fecha
            if modalidad_pago == "MENSUAL":
                fecha_vencimiento = fecha_base + relativedelta(months=numero_cuota)
            else:
                fecha_vencimiento = fecha_base + timedelta(days=intervalo_dias * numero_cuota)
            
            # Calcular montos
            monto_cuota = cuota_periodo
            if tasa_mensual == Decimal("0.00"):
                monto_interes = Decimal("0.00")
                monto_capital = monto_cuota
            else:
                monto_interes = saldo_capital * tasa_mensual
                monto_capital = monto_cuota - monto_interes
            
            saldo_capital_inicial = saldo_capital
            saldo_capital = saldo_capital - monto_capital
            saldo_capital_final = saldo_capital
            
            # Preparar parámetros
            params = {
                "prestamo_id": prestamo_id,
                "numero_cuota": numero_cuota,
                "fecha_vencimiento": fecha_vencimiento,
                "monto_cuota": float(monto_cuota),
                "monto_capital": float(monto_capital),
                "monto_interes": float(monto_interes),
                "saldo_capital_inicial": float(saldo_capital_inicial),
                "saldo_capital_final": float(saldo_capital_final),
                "capital_pagado": 0.00,
                "interes_pagado": 0.00,
                "mora_pagada": 0.00,
                "total_pagado": 0.00,
                "capital_pendiente": float(monto_capital),
                "interes_pendiente": float(monto_interes),
                "estado": "PENDIENTE"
            }
            
            # Mostrar primeros 3 y últimos 3
            if numero_cuota <= 3 or numero_cuota > numero_cuotas - 3:
                print(f"   Cuota {numero_cuota}: {fecha_vencimiento} - ${monto_cuota:.2f} (Capital: ${monto_capital:.2f}, Interés: ${monto_interes:.2f})")
            
            # Insertar
            insert_query = text("""
                INSERT INTO cuotas (
                    prestamo_id, numero_cuota, fecha_vencimiento,
                    monto_cuota, monto_capital, monto_interes,
                    saldo_capital_inicial, saldo_capital_final,
                    capital_pagado, interes_pagado, mora_pagada,
                    total_pagado, capital_pendiente, interes_pendiente,
                    estado
                ) VALUES (
                    :prestamo_id, :numero_cuota, :fecha_vencimiento,
                    :monto_cuota, :monto_capital, :monto_interes,
                    :saldo_capital_inicial, :saldo_capital_final,
                    :capital_pagado, :interes_pagado, :mora_pagada,
                    :total_pagado, :capital_pendiente, :interes_pendiente,
                    :estado
                )
            """)
            
            try:
                db.execute(insert_query, params)
                cuotas_insertadas += 1
            except Exception as e:
                print(f"\n❌ ERROR al insertar cuota {numero_cuota}:")
                print(f"   Tipo de error: {type(e).__name__}")
                print(f"   Mensaje: {str(e)}")
                print(f"   Parámetros: {params}")
                raise
        
        # Commit
        db.commit()
        print(f"\n✅ {cuotas_insertadas} cuotas generadas exitosamente")
        return True, cuotas_insertadas
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR al generar cuotas:")
        print(f"   Tipo: {type(e).__name__}")
        print(f"   Mensaje: {str(e)}")
        import traceback
        print(f"\n📋 Traceback completo:")
        traceback.print_exc()
        return False, 0


def main():
    parser = argparse.ArgumentParser(
        description='Revisar préstamos que fallaron en la generación de cuotas'
    )
    parser.add_argument(
        '--intentar-generar',
        action='store_true',
        help='Intentar generar cuotas para los préstamos fallidos'
    )
    parser.add_argument(
        '--ids',
        nargs='+',
        type=int,
        default=PRESTAMOS_FALLIDOS,
        help='IDs de préstamos a revisar (por defecto: los 4 conocidos)'
    )
    args = parser.parse_args()
    
    print("=" * 80)
    print("REVISAR PRÉSTAMOS FALLIDOS")
    print("=" * 80)
    
    try:
        db = SessionLocal()
        print("\n[OK] Conexión a base de datos establecida")
    except Exception as e:
        print(f"\n[ERROR] Error conectando a base de datos: {str(e)}")
        return
    
    try:
        prestamos_revisados = []
        
        for prestamo_id in args.ids:
            prestamo = revisar_prestamo(db, prestamo_id)
            if prestamo:
                prestamos_revisados.append(prestamo)
        
        # Resumen
        print(f"\n{'='*80}")
        print("RESUMEN")
        print(f"{'='*80}")
        print(f"Préstamos revisados: {len(prestamos_revisados)}")
        
        # Intentar generar si se solicita
        if args.intentar_generar:
            print(f"\n{'='*80}")
            print("INTENTANDO GENERAR CUOTAS")
            print(f"{'='*80}")
            
            exitosos = 0
            fallidos = 0
            
            for prestamo in prestamos_revisados:
                exito, num_cuotas = intentar_generar_cuotas(db, prestamo)
                if exito:
                    exitosos += 1
                else:
                    fallidos += 1
            
            print(f"\n{'='*80}")
            print("RESULTADO FINAL")
            print(f"{'='*80}")
            print(f"Exitosos: {exitosos}")
            print(f"Fallidos: {fallidos}")
        
    except Exception as e:
        print(f"\n[ERROR] Error general: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        print("\n[OK] Sesión cerrada")


if __name__ == "__main__":
    main()
