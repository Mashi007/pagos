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
from datetime import date, datetime
from decimal import Decimal
import time

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
from app.models.prestamo import Prestamo
from app.models.amortizacion import Cuota
from app.services.prestamo_amortizacion_service import generar_tabla_amortizacion

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


def generar_amortizacion_prestamo(prestamo_id: int, db) -> tuple[bool, int, str]:
    """
    Genera tabla de amortización para un préstamo específico

    Returns:
        (exito: bool, num_cuotas: int, mensaje: str)
    """
    try:
        # Obtener préstamo
        prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()

        if not prestamo:
            return False, 0, f"Préstamo {prestamo_id} no encontrado"

        if prestamo.estado != 'APROBADO':
            return False, 0, f"Préstamo {prestamo_id} no está aprobado (estado: {prestamo.estado})"

        if not prestamo.fecha_base_calculo:
            return False, 0, f"Préstamo {prestamo_id} no tiene fecha_base_calculo"

        if prestamo.numero_cuotas <= 0:
            return False, 0, f"Préstamo {prestamo_id} tiene número de cuotas inválido: {prestamo.numero_cuotas}"

        if prestamo.total_financiamiento <= 0:
            return False, 0, f"Préstamo {prestamo_id} tiene monto inválido: {prestamo.total_financiamiento}"

        if prestamo.modalidad_pago not in ['MENSUAL', 'QUINCENAL', 'SEMANAL']:
            return False, 0, f"Préstamo {prestamo_id} tiene modalidad inválida: {prestamo.modalidad_pago}"

        # Verificar si ya tiene cuotas
        cuotas_existentes = db.query(Cuota).filter(Cuota.prestamo_id == prestamo_id).count()

        if cuotas_existentes > 0:
            return False, 0, f"Préstamo {prestamo_id} ya tiene {cuotas_existentes} cuotas generadas"

        # Convertir fecha_base_calculo a date si es necesario
        fecha_base = prestamo.fecha_base_calculo
        if isinstance(fecha_base, str):
            fecha_base = datetime.fromisoformat(fecha_base).date()
        elif isinstance(fecha_base, datetime):
            fecha_base = fecha_base.date()

        # Generar tabla de amortización
        cuotas_generadas = generar_tabla_amortizacion(prestamo, fecha_base, db)
        num_cuotas = len(cuotas_generadas)

        return True, num_cuotas, f"✓ {num_cuotas} cuotas generadas"

    except Exception as e:
        return False, 0, f"Error: {str(e)}"


def main():
    """Función principal"""
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

        # Confirmar antes de generar
        print(f"\n[INFO] Total de préstamos a procesar: {len(prestamos_info)}")
        respuesta = input(f"\n¿Generar amortización para estos {len(prestamos_info)} préstamos? (s/n): ")
        if respuesta.lower() != 's':
            print("\n[CANCELADO] Operación cancelada")
            return

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

            exito, num_cuotas, mensaje = generar_amortizacion_prestamo(prestamo_id, db)

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

