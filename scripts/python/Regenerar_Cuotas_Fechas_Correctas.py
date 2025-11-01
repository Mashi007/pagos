"""
Script para regenerar todas las cuotas con fechas corregidas
Usa la lógica corregida con relativedelta para mantener el mismo día del mes en pagos MENSUAL
"""

import os
import sys
from datetime import date
from decimal import Decimal

# Agregar el directorio backend al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models.prestamo import Prestamo
from app.models.amortizacion import Cuota
from app.services.prestamo_amortizacion_service import generar_tabla_amortizacion
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_safe_session():
    """Crea una sesión de base de datos con manejo robusto de encoding"""
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        raise ValueError("DATABASE_URL no está definida en las variables de entorno")
    
    # Manejar encoding en DATABASE_URL
    if isinstance(database_url, bytes):
        try:
            database_url = database_url.decode('utf-8')
        except UnicodeDecodeError:
            database_url = database_url.decode('latin1')
    
    # Asegurar que el encoding esté configurado en la URL
    if '?' in database_url:
        if 'client_encoding' not in database_url:
            database_url += '&client_encoding=UTF8'
    else:
        database_url += '?client_encoding=UTF8'
    
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"options": "-c client_encoding=UTF8"}
    )
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


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
        if isinstance(prestamo.fecha_base_calculo, str):
            from dateutil.parser import parse as date_parse
            fecha_base = date_parse(prestamo.fecha_base_calculo).date()
        else:
            fecha_base = prestamo.fecha_base_calculo
        
        # Eliminar cuotas existentes (la función generar_tabla_amortizacion ya lo hace)
        # pero lo hacemos explícito para contar cuántas había
        cuotas_anteriores = db.query(Cuota).filter(Cuota.prestamo_id == prestamo.id).count()
        
        # Generar nuevas cuotas con lógica corregida
        cuotas_nuevas = generar_tabla_amortizacion(prestamo, fecha_base, db)
        
        cantidad = len(cuotas_nuevas)
        
        logger.info(
            f"Préstamo {prestamo.id}: Regeneradas {cantidad} cuotas "
            f"(tenía {cuotas_anteriores}). Fecha base: {fecha_base}"
        )
        
        return True, cantidad, f"OK: {cantidad} cuotas regeneradas"
        
    except Exception as e:
        logger.error(f"Error regenerando cuotas del préstamo {prestamo.id}: {str(e)}", exc_info=True)
        return False, 0, f"Error: {str(e)}"


def main():
    """Función principal"""
    print("=" * 80)
    print("REGENERACION DE CUOTAS CON FECHAS CORREGIDAS")
    print("Usa relativedelta para mantener el mismo dia del mes en pagos MENSUAL")
    print("=" * 80)
    print()
    
    db = create_safe_session()
    
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
                logger.error(f"Error en commit para préstamo {prestamo.id}: {str(e)}")
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
        
    except Exception as e:
        logger.error(f"Error crítico: {str(e)}", exc_info=True)
        print(f"ERROR CRÍTICO: {str(e)}")
        return 1
    finally:
        db.close()
    
    return 0 if fallidos == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

