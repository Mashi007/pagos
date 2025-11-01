"""
Script para generar tablas de amortización (cuotas) masivamente
para todos los préstamos aprobados que no tengan cuotas

Uso:
    python scripts/python/Generar_Cuotas_Masivas.py
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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import urllib.parse

# Importar desde app
from app.db.session import SessionLocal
from app.models.prestamo import Prestamo
from app.services.prestamo_amortizacion_service import generar_tabla_amortizacion

# Función helper para crear sesión segura con manejo de encoding
def create_safe_session():
    """Crea una sesión de base de datos con manejo robusto de encoding"""
    try:
        from app.core.config import settings
        database_url = os.getenv("DATABASE_URL", getattr(settings, 'DATABASE_URL', None))
    except:
        database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        # Usar SessionLocal como fallback
        return SessionLocal()
    
    # Intentar decodificar DATABASE_URL si es bytes
    if isinstance(database_url, bytes):
        try:
            database_url = database_url.decode('utf-8')
        except UnicodeDecodeError:
            database_url = database_url.decode('latin1')
    
    # Parsear y codificar correctamente
    try:
        parsed = urllib.parse.urlparse(database_url)
        if parsed.password:
            # Re-codificar componentes de manera segura
            password = urllib.parse.quote(parsed.password, safe='')
            username = urllib.parse.quote(parsed.username or '', safe='')
            database_url = f"{parsed.scheme}://{username}:{password}@{parsed.hostname}"
            if parsed.port:
                database_url += f":{parsed.port}"
            database_url += parsed.path
    except Exception:
        pass  # Si falla, usar la URL original
    
    connect_args = {}
    if database_url.startswith("postgresql"):
        connect_args = {"client_encoding": "UTF8"}
    
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False,
        connect_args=connect_args,
        pool_reset_on_return="commit",
    )
    
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()

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


def verificar_prestamo(prestamo: Prestamo) -> tuple[bool, str]:
    """
    Verifica que el préstamo tenga todos los datos necesarios para generar cuotas
    
    Returns:
        (es_valido, mensaje_error)
    """
    if prestamo.estado != "APROBADO":
        return False, f"Préstamo no está aprobado (estado: {prestamo.estado})"
    
    if prestamo.total_financiamiento <= Decimal("0.00"):
        return False, f"Monto inválido: {prestamo.total_financiamiento}"
    
    if prestamo.numero_cuotas <= 0:
        return False, f"Número de cuotas inválido: {prestamo.numero_cuotas}"
    
    if not prestamo.fecha_base_calculo:
        return False, "fecha_base_calculo no está configurada"
    
    if prestamo.cuota_periodo <= Decimal("0.00"):
        return False, f"Cuota período inválida: {prestamo.cuota_periodo}"
    
    # Convertir fecha_base_calculo a date si es necesario
    if isinstance(prestamo.fecha_base_calculo, str):
        try:
            prestamo.fecha_base_calculo = datetime.fromisoformat(prestamo.fecha_base_calculo).date()
        except Exception:
            return False, f"fecha_base_calculo inválida: {prestamo.fecha_base_calculo}"
    
    return True, "OK"


def generar_cuotas_prestamo(prestamo: Prestamo, db: Session) -> tuple[bool, int, str]:
    """
    Genera cuotas para un préstamo
    
    Returns:
        (exito, num_cuotas_generadas, mensaje)
    """
    try:
        # Verificar préstamo
        es_valido, mensaje = verificar_prestamo(prestamo)
        if not es_valido:
            return False, 0, mensaje
        
        # Convertir fecha_base_calculo a date
        fecha_base = prestamo.fecha_base_calculo
        if isinstance(fecha_base, str):
            fecha_base = datetime.fromisoformat(fecha_base).date()
        elif isinstance(fecha_base, datetime):
            fecha_base = fecha_base.date()
        
        # Generar tabla de amortización
        cuotas = generar_tabla_amortizacion(prestamo, fecha_base, db)
        
        num_cuotas = len(cuotas)
        return True, num_cuotas, f"✓ Generadas {num_cuotas} cuotas"
    
    except Exception as e:
        return False, 0, f"Error: {str(e)}"


def main():
    """Función principal"""
    try:
        db: Session = create_safe_session()
    except Exception:
        # Fallback a SessionLocal si create_safe_session falla
        db: Session = SessionLocal()
    
    try:
        log_info("=" * 60)
        log_info("GENERACIÓN MASIVA DE CUOTAS PARA PRÉSTAMOS")
        log_info("=" * 60)
        
        # 1. Buscar préstamos aprobados sin cuotas o con cuotas incompletas
        prestamos = (
            db.query(Prestamo)
            .filter(Prestamo.estado == "APROBADO")
            .order_by(Prestamo.id)
            .all()
        )
        
        log_info(f"Total préstamos aprobados encontrados: {len(prestamos)}")
        
        # 2. Verificar cuáles necesitan cuotas
        from app.models.amortizacion import Cuota
        
        prestamos_pendientes = []
        for prestamo in prestamos:
            num_cuotas_existentes = (
                db.query(Cuota)
                .filter(Cuota.prestamo_id == prestamo.id)
                .count()
            )
            
            # Si no tiene cuotas o tiene menos cuotas de las que debería
            if num_cuotas_existentes == 0 or num_cuotas_existentes != prestamo.numero_cuotas:
                prestamos_pendientes.append((prestamo, num_cuotas_existentes))
        
        log_info(f"Préstamos que necesitan cuotas: {len(prestamos_pendientes)}")
        
        if len(prestamos_pendientes) == 0:
            log_info("✓ Todos los préstamos ya tienen sus cuotas generadas")
            return
        
        # 3. Generar cuotas para cada préstamo
        exitosos = 0
        fallidos = 0
        
        for prestamo, cuotas_existentes in prestamos_pendientes:
            log_info(f"\n--- Procesando préstamo ID {prestamo.id} ---")
            log_info(f"  Cliente: {prestamo.nombres} ({prestamo.cedula})")
            log_info(f"  Monto: ${prestamo.total_financiamiento}")
            log_info(f"  Cuotas esperadas: {prestamo.numero_cuotas}")
            log_info(f"  Cuotas existentes: {cuotas_existentes}")
            log_info(f"  Fecha base: {prestamo.fecha_base_calculo}")
            
            # Verificar antes de generar
            es_valido, mensaje = verificar_prestamo(prestamo)
            if not es_valido:
                log_error(f"  ✗ {mensaje}")
                fallidos += 1
                continue
            
            # Generar cuotas
            exito, num_cuotas, mensaje = generar_cuotas_prestamo(prestamo, db)
            
            if exito:
                log_info(f"  {mensaje}")
                exitosos += 1
            else:
                log_error(f"  ✗ {mensaje}")
                fallidos += 1
        
        # 4. Resumen final
        log_info("\n" + "=" * 60)
        log_info("RESUMEN FINAL")
        log_info("=" * 60)
        log_info(f"Préstamos procesados: {len(prestamos_pendientes)}")
        log_info(f"✓ Exitosos: {exitosos}")
        log_info(f"✗ Fallidos: {fallidos}")
        log_info("=" * 60)
        
    except Exception as e:
        log_error("Error fatal en el proceso", e)
        db.rollback()
        raise
    
    finally:
        db.close()


if __name__ == "__main__":
    main()

