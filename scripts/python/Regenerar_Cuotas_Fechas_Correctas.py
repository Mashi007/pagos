"""
Script para regenerar todas las cuotas con fechas corregidas
Usa la lógica corregida con relativedelta para mantener el mismo día del mes en pagos MENSUAL

Uso:
    python scripts/python/Regenerar_Cuotas_Fechas_Correctas.py
"""

import os
import sys
from datetime import date, datetime
from decimal import Decimal

# Manejar encoding para Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Agregar el directorio backend al path (donde está la estructura app/)
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend"))
sys.path.insert(0, backend_dir)

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


def log_info(message: str):
    """Log helper"""
    print(f"[INFO] {message}")
    if logger:
        logger.info(message)


def log_error(message: str, exc: Exception = None):
    """Error log helper"""
    print(f"[ERROR] {message}")
    if exc:
        print(f"        Exception: {str(exc)}")
    if logger:
        logger.error(message, exc_info=exc)


def regenerar_cuotas_prestamo(prestamo: Prestamo, db: Session) -> tuple[bool, int, str]:
    """
    Regenera las cuotas de un préstamo usando la lógica corregida
    
    Returns:
        (exito, cantidad_cuotas, mensaje)
    """
    try:
        # Validar que tenga fecha_base_calculo
        if not prestamo.fecha_base_calculo:
            return False, 0, f"Préstamo {prestamo.id}: No tiene fecha_base_calculo"
        
        # Validar que esté aprobado
        if prestamo.estado != 'APROBADO':
            return False, 0, f"Préstamo {prestamo.id}: Estado '{prestamo.estado}' (no APROBADO)"
        
        # Validar datos necesarios
        if prestamo.total_financiamiento <= Decimal("0.00"):
            return False, 0, f"Préstamo {prestamo.id}: total_financiamiento <= 0"
        
        if prestamo.numero_cuotas <= 0:
            return False, 0, f"Préstamo {prestamo.id}: numero_cuotas <= 0"
        
        # Convertir fecha_base_calculo a date si es necesario
        fecha_base = prestamo.fecha_base_calculo
        if isinstance(fecha_base, str):
            fecha_base = datetime.fromisoformat(fecha_base).date()
        elif isinstance(fecha_base, datetime):
            fecha_base = fecha_base.date()
        
        # Eliminar cuotas existentes (la función generar_tabla_amortizacion ya lo hace)
        # pero lo hacemos explícito para contar cuántas había
        cuotas_anteriores = db.query(Cuota).filter(Cuota.prestamo_id == prestamo.id).count()
        
        # Generar nuevas cuotas con lógica corregida
        cuotas_nuevas = generar_tabla_amortizacion(prestamo, fecha_base, db)
        
        cantidad = len(cuotas_nuevas)
        
        log_info(
            f"Préstamo {prestamo.id}: Regeneradas {cantidad} cuotas "
            f"(tenía {cuotas_anteriores}). Fecha base: {fecha_base}"
        )
        
        return True, cantidad, f"OK: {cantidad} cuotas regeneradas"
        
    except Exception as e:
        log_error(f"Error regenerando cuotas del préstamo {prestamo.id}: {str(e)}", e)
        return False, 0, f"Error: {str(e)}"


def main():
    """Función principal"""
    print("=" * 80)
    print("REGENERACION DE CUOTAS CON FECHAS CORREGIDAS")
    print("Usa relativedelta para mantener el mismo dia del mes en pagos MENSUAL")
    print("=" * 80)
    print()
    
    db = SessionLocal()
    
    try:
        # Obtener todos los préstamos aprobados con fecha_base_calculo
        prestamos = (
            db.query(Prestamo)
            .filter(
                Prestamo.estado == 'APROBADO',
                Prestamo.fecha_base_calculo.isnot(None)
            )
            .order_by(Prestamo.id)
            .all()
        )
        
        total_prestamos = len(prestamos)
        print(f"Total de préstamos a procesar: {total_prestamos}")
        print()
        
        exitosos = 0
        fallidos = 0
        total_cuotas = 0
        errores = []
        
        for idx, prestamo in enumerate(prestamos, 1):
            print(f"[{idx}/{total_prestamos}] Procesando préstamo {prestamo.id}...", end=" ")
            
            exito, cantidad, mensaje = regenerar_cuotas_prestamo(prestamo, db)
            
            if exito:
                exitosos += 1
                total_cuotas += cantidad
                print(f"OK ({cantidad} cuotas)")
            else:
                fallidos += 1
                errores.append(f"Préstamo {prestamo.id}: {mensaje}")
                print(f"ERROR: {mensaje}")
            
            # Commit después de cada préstamo
            try:
                db.commit()
            except Exception as e:
                db.rollback()
                log_error(f"Error en commit para préstamo {prestamo.id}: {str(e)}", e)
                fallidos += 1
                errores.append(f"Préstamo {prestamo.id}: Error en commit - {str(e)}")
        
        # Resumen final
        print()
        print("=" * 80)
        print("RESUMEN FINAL")
        print("=" * 80)
        print(f"Préstamos procesados: {total_prestamos}")
        print(f"Exitosos: {exitosos}")
        print(f"Fallidos: {fallidos}")
        print(f"Total cuotas regeneradas: {total_cuotas}")
        print()
        
        if errores:
            print("ERRORES DETECTADOS:")
            for error in errores[:20]:  # Mostrar máximo 20 errores
                print(f"  - {error}")
            if len(errores) > 20:
                print(f"  ... y {len(errores) - 20} errores más")
            print()
        
        print("Proceso completado.")
        return 0 if fallidos == 0 else 1
        
    except Exception as e:
        log_error(f"Error crítico: {str(e)}", e)
        print(f"ERROR CRÍTICO: {str(e)}")
        return 1
    finally:
        db.close()


if __name__ == '__main__':
    sys.exit(main())
