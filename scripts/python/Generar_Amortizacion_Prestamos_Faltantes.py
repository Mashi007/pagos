"""
Script para generar tablas de amortización para préstamos aprobados
que no tienen cuotas generadas pero tienen todos los datos necesarios.

Uso:
    python scripts/python/Generar_Amortizacion_Prestamos_Faltantes.py
"""

import os
import sys
from datetime import date
from decimal import Decimal

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
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
except Exception:
    pass


def identificar_prestamos_sin_amortizacion(db):
    """Identifica préstamos aprobados sin tabla de amortización"""
    query = text("""
        SELECT p.id
        FROM prestamos p
        WHERE p.estado = 'APROBADO'
          AND p.fecha_base_calculo IS NOT NULL
          AND p.numero_cuotas > 0
          AND p.total_financiamiento > 0
          AND p.modalidad_pago IN ('MENSUAL', 'QUINCENAL', 'SEMANAL')
          AND NOT EXISTS (SELECT 1 FROM cuotas WHERE prestamo_id = p.id)
        ORDER BY p.id
    """)
    
    result = db.execute(query)
    prestamo_ids = [row[0] for row in result]
    return prestamo_ids


def generar_amortizacion_prestamo(prestamo_id: int, db) -> tuple[bool, str]:
    """
    Genera tabla de amortización para un préstamo específico
    
    Returns:
        (exito: bool, mensaje: str)
    """
    try:
        # Obtener préstamo
        prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
        
        if not prestamo:
            return False, f"Préstamo {prestamo_id} no encontrado"
        
        if prestamo.estado != 'APROBADO':
            return False, f"Préstamo {prestamo_id} no está aprobado (estado: {prestamo.estado})"
        
        if not prestamo.fecha_base_calculo:
            return False, f"Préstamo {prestamo_id} no tiene fecha_base_calculo"
        
        if prestamo.numero_cuotas <= 0:
            return False, f"Préstamo {prestamo_id} tiene número de cuotas inválido: {prestamo.numero_cuotas}"
        
        if prestamo.total_financiamiento <= 0:
            return False, f"Préstamo {prestamo_id} tiene monto inválido: {prestamo.total_financiamiento}"
        
        if prestamo.modalidad_pago not in ['MENSUAL', 'QUINCENAL', 'SEMANAL']:
            return False, f"Préstamo {prestamo_id} tiene modalidad inválida: {prestamo.modalidad_pago}"
        
        # Verificar si ya tiene cuotas
        cuotas_existentes = db.query(Cuota).filter(Cuota.prestamo_id == prestamo_id).count()
        
        if cuotas_existentes > 0:
            return False, f"Préstamo {prestamo_id} ya tiene {cuotas_existentes} cuotas generadas"
        
        # Generar tabla de amortización
        fecha_base = prestamo.fecha_base_calculo
        cuotas_generadas = generar_tabla_amortizacion(prestamo, fecha_base, db)
        
        return True, f"Préstamo {prestamo_id}: {len(cuotas_generadas)} cuotas generadas correctamente"
        
    except Exception as e:
        return False, f"Error en préstamo {prestamo_id}: {str(e)}"


def main():
    """Función principal"""
    print("=" * 70)
    print("GENERAR AMORTIZACIÓN PARA PRÉSTAMOS FALTANTES")
    print("=" * 70)
    print()
    
    # Crear sesión
    try:
        db = SessionLocal()
        # Probar conexión
        db.execute(text("SELECT 1"))
        print("[OK] Conexion a base de datos establecida")
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
        print("\n[INFO] Identificando prestamos aprobados sin tabla de amortizacion...")
        prestamo_ids = identificar_prestamos_sin_amortizacion(db)
        
        if not prestamo_ids:
            print("\n[OK] No hay prestamos aprobados sin tabla de amortizacion")
            return
        
        print(f"\n[INFO] Encontrados {len(prestamo_ids)} prestamos sin tabla de amortizacion")
        print(f"   IDs: {', '.join(map(str, prestamo_ids))}")
        
        # Confirmar antes de generar
        respuesta = input(f"\n¿Generar amortizacion para estos {len(prestamo_ids)} prestamos? (s/n): ")
        if respuesta.lower() != 's':
            print("\n[CANCELADO] Operacion cancelada")
            return
        
        # Generar amortización para cada préstamo
        print("\n[INFO] Generando tablas de amortizacion...\n")
        
        exitosos = 0
        fallidos = 0
        
        for prestamo_id in prestamo_ids:
            exito, mensaje = generar_amortizacion_prestamo(prestamo_id, db)
            
            if exito:
                print(f"[OK] {mensaje}")
                exitosos += 1
            else:
                print(f"[ERROR] {mensaje}")
                fallidos += 1
        
        # Resumen final
        print("\n" + "=" * 70)
        print("RESUMEN DE GENERACION")
        print("=" * 70)
        print(f"[OK] Exitosos: {exitosos}")
        print(f"[ERROR] Fallidos: {fallidos}")
        print(f"[INFO] Total procesados: {len(prestamo_ids)}")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n[ERROR] Error general: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        print("\n[OK] Sesion cerrada")


if __name__ == "__main__":
    main()

