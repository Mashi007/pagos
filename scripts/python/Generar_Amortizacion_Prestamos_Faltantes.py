"""
Script para generar tablas de amortización para préstamos aprobados
que no tienen cuotas generadas pero tienen todos los datos necesarios.

Uso:
    python scripts/python/Generar_Amortizacion_Prestamos_Faltantes.py

Características:
    - Identifica automáticamente préstamos aprobados sin cuotas
    - Valida que tengan todos los datos necesarios
    - Genera cuotas usando la función oficial del sistema
    - Muestra progreso en tiempo real
    - Maneja errores sin detener el proceso
    - Genera reporte final con estadísticas
"""

import os
import sys
import argparse
from datetime import date, datetime, timedelta
from decimal import Decimal
import time
from dateutil.relativedelta import relativedelta

# Manejar encoding para Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Agregar el directorio del backend al path (donde está la estructura app/)
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend"))
sys.path.insert(0, backend_dir)

from sqlalchemy import text
from sqlalchemy.orm import Session

# Importar desde app
from app.db.session import SessionLocal

logger = None
try:
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
except Exception:
    pass


def identificar_prestamos_sin_amortizacion(db):
    """
    Identifica préstamos aprobados sin tabla de amortización
    que tienen todos los datos necesarios
    """
    query = text("""
        SELECT 
            p.id,
            p.cedula,
            p.numero_cuotas,
            p.total_financiamiento,
            p.cuota_periodo,
            p.fecha_base_calculo
        FROM prestamos p
        WHERE p.estado = 'APROBADO'
          AND p.fecha_base_calculo IS NOT NULL
          AND p.numero_cuotas IS NOT NULL
          AND p.numero_cuotas > 0
          AND p.total_financiamiento IS NOT NULL
          AND p.total_financiamiento > 0
          AND p.cuota_periodo IS NOT NULL
          AND p.cuota_periodo > 0
          AND p.modalidad_pago IN ('MENSUAL', 'QUINCENAL', 'SEMANAL')
          AND NOT EXISTS (SELECT 1 FROM cuotas WHERE prestamo_id = p.id)
        ORDER BY p.id
    """)

    result = db.execute(query)
    prestamos_info = [
        {
            'id': row[0],
            'cedula': row[1],
            'numero_cuotas': row[2],
            'total_financiamiento': row[3],
            'cuota_periodo': row[4],
            'fecha_base_calculo': row[5]
        }
        for row in result
    ]
    return prestamos_info


def _calcular_intervalo_dias(modalidad_pago: str) -> int:
    """Calcula días entre cuotas según modalidad"""
    intervalos = {
        "MENSUAL": 30,
        "QUINCENAL": 15,
        "SEMANAL": 7,
    }
    return intervalos.get(modalidad_pago, 30)


def generar_amortizacion_prestamo(prestamo_info: dict, db) -> tuple[bool, int, str]:
    """
    Genera tabla de amortización para un préstamo específico usando SQL directo
    para evitar problemas con el modelo ORM desincronizado

    Returns:
        (exito: bool, num_cuotas: int, mensaje: str)
    """
    try:
        prestamo_id = prestamo_info['id']
        
        # Verificar si ya tiene cuotas
        query_verificar = text("SELECT COUNT(*) FROM cuotas WHERE prestamo_id = :prestamo_id")
        result = db.execute(query_verificar, {"prestamo_id": prestamo_id})
        cuotas_existentes = result.scalar()
        
        if cuotas_existentes > 0:
            return False, 0, f"Préstamo {prestamo_id} ya tiene {cuotas_existentes} cuotas generadas"

        # Eliminar cuotas existentes si las hay (por seguridad)
        db.execute(text("DELETE FROM cuotas WHERE prestamo_id = :prestamo_id"), 
                   {"prestamo_id": prestamo_id})

        # Preparar datos
        fecha_base = prestamo_info['fecha_base_calculo']
        if isinstance(fecha_base, str):
            fecha_base = datetime.fromisoformat(fecha_base).date()
        elif isinstance(fecha_base, datetime):
            fecha_base = fecha_base.date()

        numero_cuotas = prestamo_info['numero_cuotas']
        total_financiamiento = prestamo_info['total_financiamiento']
        cuota_periodo = prestamo_info['cuota_periodo']
        modalidad_pago = prestamo_info['modalidad_pago']
        tasa_interes = prestamo_info['tasa_interes']

        # Validaciones
        if total_financiamiento <= Decimal("0.00"):
            return False, 0, f"Monto inválido: {total_financiamiento}"
        if numero_cuotas <= 0:
            return False, 0, f"Número de cuotas inválido: {numero_cuotas}"

        # Calcular intervalo entre cuotas
        intervalo_dias = _calcular_intervalo_dias(modalidad_pago)

        # Tasa de interés mensual
        if tasa_interes == Decimal("0.00"):
            tasa_mensual = Decimal("0.00")
        else:
            tasa_mensual = tasa_interes / Decimal(100) / Decimal(12)

        # Generar cuotas
        saldo_capital = total_financiamiento
        cuotas_insertadas = []

        for numero_cuota in range(1, numero_cuotas + 1):
            # Calcular fecha de vencimiento
            if modalidad_pago == "MENSUAL":
                fecha_vencimiento = fecha_base + relativedelta(months=numero_cuota)
            else:
                fecha_vencimiento = fecha_base + timedelta(days=intervalo_dias * numero_cuota)

            # Método Francés (cuota fija)
            monto_cuota = cuota_periodo

            # Calcular interés y capital
            if tasa_mensual == Decimal("0.00"):
                monto_interes = Decimal("0.00")
                monto_capital = monto_cuota
            else:
                monto_interes = saldo_capital * tasa_mensual
                monto_capital = monto_cuota - monto_interes

            # Actualizar saldo
            saldo_capital_inicial = saldo_capital
            saldo_capital = saldo_capital - monto_capital
            saldo_capital_final = saldo_capital

            # Insertar cuota usando SQL directo
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
            
            db.execute(insert_query, {
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
            })
            cuotas_insertadas.append(numero_cuota)

        # Commit de todas las cuotas
        db.commit()
        num_cuotas = len(cuotas_insertadas)

        return True, num_cuotas, f"✓ {num_cuotas} cuotas generadas"

    except Exception as e:
        db.rollback()
        return False, 0, f"Error: {str(e)}"


def main():
    """Función principal"""
    # Parsear argumentos de línea de comandos
    parser = argparse.ArgumentParser(
        description='Generar tablas de amortización para préstamos aprobados sin cuotas'
    )
    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        help='Ejecutar sin pedir confirmación'
    )
    args = parser.parse_args()
    
    print("=" * 80)
    print("GENERAR AMORTIZACIÓN PARA PRÉSTAMOS FALTANTES")
    print("=" * 80)
    print()

    # Crear sesión
    try:
        db = SessionLocal()
        # Probar conexión
        db.execute(text("SELECT 1"))
        print("[OK] Conexión a base de datos establecida")
    except UnicodeDecodeError as e:
        print(f"[ERROR] Error de encoding en DATABASE_URL: {str(e)}")
        print("[INFO] Sugerencia: Verifica que DATABASE_URL esté correctamente codificado")
        print("[INFO] Alternativa: Usa el script Generar_Amortizacion_Por_API.py que usa la API")
        return
    except Exception as e:
        print(f"[ERROR] Error conectando a base de datos: {str(e)}")
        print("[INFO] Sugerencia: Verifica que DATABASE_URL esté configurado correctamente")
        print("[INFO] Alternativa: Usa el script Generar_Amortizacion_Por_API.py que usa la API")
        return

    try:
        # Identificar préstamos sin amortización
        print("\n[INFO] Identificando préstamos aprobados sin tabla de amortización...")
        inicio_identificacion = time.time()
        prestamos_info = identificar_prestamos_sin_amortizacion(db)
        tiempo_identificacion = time.time() - inicio_identificacion

        if not prestamos_info:
            print("\n[OK] No hay préstamos aprobados sin tabla de amortización")
            return

        print(f"\n[OK] Encontrados {len(prestamos_info)} préstamos sin tabla de amortización")
        print(f"     Tiempo de identificación: {tiempo_identificacion:.2f} segundos")
        
        # Mostrar muestra de préstamos
        print("\n[INFO] Muestra de préstamos a procesar (primeros 5):")
        for i, info in enumerate(prestamos_info[:5], 1):
            print(f"     {i}. ID: {info['id']}, Cédula: {info['cedula']}, "
                  f"Cuotas: {info['numero_cuotas']}, Monto: ${info['total_financiamiento']}")
        if len(prestamos_info) > 5:
            print(f"     ... y {len(prestamos_info) - 5} préstamos más")

        # Confirmar antes de generar (a menos que se use --yes)
        print(f"\n[INFO] Total de préstamos a procesar: {len(prestamos_info)}")
        
        if not args.yes:
            try:
                respuesta = input(f"\n¿Generar amortización para estos {len(prestamos_info)} préstamos? (s/n): ")
                if respuesta.lower() != 's':
                    print("\n[CANCELADO] Operación cancelada")
                    return
            except (EOFError, KeyboardInterrupt):
                print("\n[ERROR] No se puede leer entrada interactiva. Usa --yes para ejecutar automáticamente.")
                print("         Ejemplo: python scripts/python/Generar_Amortizacion_Prestamos_Faltantes.py --yes")
                return
        else:
            print(f"\n[INFO] Modo automático activado (--yes). Iniciando generación...")

        # Generar amortización para cada préstamo
        print("\n" + "=" * 80)
        print("[INFO] Generando tablas de amortización...")
        print("=" * 80)
        print()

        inicio_proceso = time.time()
        exitosos = 0
        fallidos = 0
        total_cuotas_generadas = 0
        errores_detallados = []

        for idx, info in enumerate(prestamos_info, 1):
            prestamo_id = info['id']
            
            # Mostrar progreso cada 100 préstamos o en los primeros 10
            if idx <= 10 or idx % 100 == 0 or idx == len(prestamos_info):
                porcentaje = (idx / len(prestamos_info)) * 100
                print(f"[PROGRESO] {idx}/{len(prestamos_info)} ({porcentaje:.1f}%) - "
                      f"Procesando préstamo ID {prestamo_id}...")

            exito, num_cuotas, mensaje = generar_amortizacion_prestamo(info, db)

            if exito:
                exitosos += 1
                total_cuotas_generadas += num_cuotas
                if idx <= 10 or idx % 100 == 0:
                    print(f"  [OK] {mensaje}")
            else:
                fallidos += 1
                errores_detallados.append({
                    'prestamo_id': prestamo_id,
                    'cedula': info['cedula'],
                    'error': mensaje
                })
                if idx <= 10 or idx % 100 == 0:
                    print(f"  [ERROR] {mensaje}")

        tiempo_proceso = time.time() - inicio_proceso

        # Resumen final
        print("\n" + "=" * 80)
        print("RESUMEN DE GENERACIÓN")
        print("=" * 80)
        print(f"[OK] Préstamos exitosos: {exitosos}")
        print(f"[ERROR] Préstamos fallidos: {fallidos}")
        print(f"[INFO] Total procesados: {len(prestamos_info)}")
        print(f"[INFO] Total cuotas generadas: {total_cuotas_generadas:,}")
        print(f"[INFO] Tiempo total: {tiempo_proceso:.2f} segundos ({tiempo_proceso/60:.2f} minutos)")
        print(f"[INFO] Promedio por préstamo: {tiempo_proceso/len(prestamos_info):.3f} segundos")
        print("=" * 80)

        # Mostrar errores si los hay
        if errores_detallados:
            print(f"\n[ERROR] Detalles de préstamos fallidos ({len(errores_detallados)}):")
            for error in errores_detallados[:20]:  # Mostrar primeros 20
                print(f"  - ID {error['prestamo_id']} (Cédula: {error['cedula']}): {error['error']}")
            if len(errores_detallados) > 20:
                print(f"  ... y {len(errores_detallados) - 20} errores más")

        # Verificación final
        print("\n[INFO] Verificando resultados finales...")
        query_verificacion = text("""
            SELECT 
                COUNT(DISTINCT prestamo_id) AS prestamos_con_cuotas,
                COUNT(*) AS total_cuotas
            FROM cuotas
        """)
        resultado = db.execute(query_verificacion).fetchone()
        print(f"  [OK] Préstamos con cuotas en BD: {resultado[0]:,}")
        print(f"  [OK] Total cuotas en BD: {resultado[1]:,}")

    except KeyboardInterrupt:
        print("\n\n[INTERRUPCIÓN] Proceso cancelado por el usuario")
        print(f"[INFO] Procesados hasta el momento: {exitosos} exitosos, {fallidos} fallidos")
        db.rollback()
    except Exception as e:
        print(f"\n[ERROR] Error general: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()
        print("\n[OK] Sesión cerrada")


if __name__ == "__main__":
    main()

