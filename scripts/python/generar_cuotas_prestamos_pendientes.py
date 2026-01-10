"""
Script para generar cuotas para préstamos aprobados que no tienen cuotas generadas
"""

import logging
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.amortizacion import Cuota
from app.models.prestamo import Prestamo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def identificar_prestamos_sin_cuotas(db):
    """Identifica préstamos aprobados sin cuotas generadas"""
    query = text("""
        SELECT p.id, p.cedula, p.total_financiamiento, p.fecha_aprobacion, 
               p.numero_cuotas, p.tasa_interes, p.monto_cuota, p.modalidad_pago,
               p.cuota_periodo, p.fecha_base_calculo
        FROM prestamos p
        WHERE p.estado = 'APROBADO'
          AND NOT EXISTS (
            SELECT 1 FROM cuotas c WHERE c.prestamo_id = p.id
          )
        ORDER BY p.fecha_aprobacion DESC
    """)
    
    result = db.execute(query)
    return result.fetchall()


def validar_datos_prestamo(prestamo_data) -> tuple[bool, str]:
    """Valida que el préstamo tenga todos los datos necesarios para generar cuotas"""
    prestamo_id = prestamo_data[0]
    total_financiamiento = prestamo_data[2]
    fecha_aprobacion = prestamo_data[3]
    numero_cuotas = prestamo_data[4]
    tasa_interes = prestamo_data[5]
    monto_cuota = prestamo_data[6]
    modalidad_pago = prestamo_data[7] if len(prestamo_data) > 7 else None
    cuota_periodo = prestamo_data[8] if len(prestamo_data) > 8 else None
    
    errores = []
    
    if not total_financiamiento or total_financiamiento <= 0:
        errores.append("total_financiamiento inválido o faltante")
    
    if not fecha_aprobacion:
        errores.append("fecha_aprobacion faltante")
    
    if not numero_cuotas or numero_cuotas <= 0:
        errores.append("numero_cuotas inválido o faltante")
    
    if tasa_interes is None:
        errores.append("tasa_interes faltante")
    
    if not modalidad_pago:
        errores.append("modalidad_pago faltante")
    elif modalidad_pago not in ['MENSUAL', 'QUINCENAL', 'SEMANAL']:
        errores.append(f"modalidad_pago inválida: {modalidad_pago}")
    
    if not cuota_periodo or cuota_periodo <= 0:
        errores.append("cuota_periodo inválido o faltante")
    
    if errores:
        return False, f"Préstamo {prestamo_id}: {', '.join(errores)}"
    
    return True, "OK"


def generar_cuotas_para_prestamo(db, prestamo_id: int, dry_run: bool = True):
    """
    Genera cuotas para un préstamo usando el servicio existente
    """
    try:
        # Importar servicio de amortización correcto
        from app.services.prestamo_amortizacion_service import generar_tabla_amortizacion
        
        prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
        if not prestamo:
            logger.error(f"❌ Préstamo {prestamo_id} no encontrado")
            return False
        
        # Validar que tenga fecha_base_calculo o usar fecha_aprobacion
        fecha_base = None
        if hasattr(prestamo, 'fecha_base_calculo') and prestamo.fecha_base_calculo:
            fecha_base = prestamo.fecha_base_calculo
            if isinstance(fecha_base, datetime):
                fecha_base = fecha_base.date()
        elif prestamo.fecha_aprobacion:
            fecha_base = prestamo.fecha_aprobacion.date() if isinstance(prestamo.fecha_aprobacion, datetime) else prestamo.fecha_aprobacion
        else:
            fecha_base = date.today()
            logger.warning(f"⚠️ Préstamo {prestamo_id}: Sin fecha_aprobacion, usando fecha actual: {fecha_base}")
        
        if dry_run:
            logger.info(f"[DRY RUN] Generaría {prestamo.numero_cuotas} cuotas para préstamo {prestamo_id} (Cédula: {prestamo.cedula}, Fecha base: {fecha_base})")
            return True
        
        # Generar tabla de amortización usando el servicio correcto
        cuotas_generadas = generar_tabla_amortizacion(
            prestamo=prestamo,
            fecha_base=fecha_base,
            db=db
        )
        
        logger.info(f"✅ Generadas {len(cuotas_generadas)} cuotas para préstamo {prestamo_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error generando cuotas para préstamo {prestamo_id}: {e}", exc_info=True)
        return False


def main(dry_run: bool = True, limit: int = None):
    """
    Genera cuotas para préstamos aprobados sin cuotas
    
    Args:
        dry_run: Si es True, solo muestra qué se haría sin hacer cambios
        limit: Límite de préstamos a procesar (None = todos)
    """
    logger.info("=" * 80)
    logger.info("🔧 GENERACIÓN DE CUOTAS PARA PRÉSTAMOS PENDIENTES")
    logger.info("=" * 80)
    logger.info(f"Modo: {'DRY RUN (sin cambios)' if dry_run else 'EJECUCIÓN REAL'}")
    if limit:
        logger.info(f"Límite: {limit} préstamos")
    logger.info("=" * 80)
    
    if not dry_run:
        respuesta = input("⚠️ ¿Estás seguro de que quieres generar cuotas REALES? (escribe 'SI' para continuar): ")
        if respuesta != 'SI':
            logger.info("❌ Operación cancelada por el usuario")
            return
    
    # Conectar a la base de datos
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Identificar préstamos sin cuotas
        logger.info("🔍 Identificando préstamos aprobados sin cuotas...")
        prestamos = identificar_prestamos_sin_cuotas(db)
        
        total_prestamos = len(prestamos)
        if limit:
            prestamos = prestamos[:limit]
            logger.info(f"📊 Total encontrados: {total_prestamos}, Procesando: {len(prestamos)}")
        else:
            logger.info(f"📊 Total encontrados: {total_prestamos}")
        
        if total_prestamos == 0:
            logger.info("✅ No se encontraron préstamos sin cuotas")
            return
        
        # Estadísticas
        prestamos_validos = 0
        prestamos_invalidos = 0
        generaciones_exitosas = 0
        generaciones_fallidas = 0
        total_procesados = 0
        
        # Intervalo para informes periódicos (cada 50 préstamos)
        intervalo_reporte = 50
        
        # Procesar cada préstamo
        for idx, prestamo_data in enumerate(prestamos, 1):
            total_procesados = idx
            prestamo_id = prestamo_data[0]
            cedula = prestamo_data[1]
            total_financiamiento = prestamo_data[2]
            
            # Validar datos
            es_valido, mensaje = validar_datos_prestamo(prestamo_data)
            
            if not es_valido:
                logger.warning(f"⚠️ {mensaje}")
                prestamos_invalidos += 1
                continue
            
            prestamos_validos += 1
            
            # Generar cuotas
            logger.info(f"📝 Procesando préstamo {prestamo_id} (Cédula: {cedula}, Monto: ${total_financiamiento:,.2f})...")
            
            if generar_cuotas_para_prestamo(db, prestamo_id, dry_run):
                generaciones_exitosas += 1
                if not dry_run:
                    db.commit()
            else:
                generaciones_fallidas += 1
                if not dry_run:
                    db.rollback()
            
            # Informe periódico cada intervalo_reporte préstamos o al final
            if total_procesados % intervalo_reporte == 0 or total_procesados == len(prestamos):
                porcentaje = (total_procesados / len(prestamos)) * 100
                tiempo_transcurrido = ""
                logger.info("\n" + "=" * 80)
                logger.info(f"📊 INFORME DE AVANCE - {total_procesados}/{len(prestamos)} préstamos procesados ({porcentaje:.1f}%)")
                logger.info("=" * 80)
                logger.info(f"✅ Generaciones exitosas: {generaciones_exitosas}")
                logger.info(f"❌ Generaciones fallidas: {generaciones_fallidas}")
                logger.info(f"⚠️ Préstamos inválidos: {prestamos_invalidos}")
                logger.info(f"📈 Progreso: {total_procesados}/{len(prestamos)} ({porcentaje:.1f}%)")
                if total_procesados < len(prestamos):
                    logger.info(f"⏳ Pendientes: {len(prestamos) - total_procesados}")
                logger.info("=" * 80 + "\n")
        
        # Resumen final
        logger.info("\n" + "=" * 80)
        logger.info("📊 RESUMEN FINAL")
        logger.info("=" * 80)
        logger.info(f"Total préstamos encontrados: {total_prestamos}")
        logger.info(f"Préstamos válidos: {prestamos_validos}")
        logger.info(f"Préstamos inválidos: {prestamos_invalidos}")
        logger.info(f"Generaciones exitosas: {generaciones_exitosas}")
        logger.info(f"Generaciones fallidas: {generaciones_fallidas}")
        logger.info("=" * 80)
        
        if dry_run:
            logger.info("\n💡 Para ejecutar los cambios reales, ejecuta:")
            logger.info("   python scripts/python/generar_cuotas_prestamos_pendientes.py --execute")
        
    except Exception as e:
        logger.error(f"❌ Error durante la generación: {e}", exc_info=True)
        if not dry_run:
            db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    dry_run = True
    if "--execute" in sys.argv:
        dry_run = False
    
    limit = None
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])
    
    main(dry_run=dry_run, limit=limit)
