"""
Script para generar cuotas para préstamos aprobados que no tienen cuotas generadas
"""

import logging
import os
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
import urllib.parse

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, defer

from app.core.config import settings
from app.models.amortizacion import Cuota
from app.models.prestamo import Prestamo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def identificar_prestamos_sin_cuotas(db):
    """Identifica préstamos aprobados sin cuotas generadas"""
    query = text("""
        SELECT p.id, p.cedula, p.total_financiamiento, p.fecha_aprobacion, 
               p.numero_cuotas, p.tasa_interes, p.cuota_periodo, p.modalidad_pago,
               p.fecha_base_calculo
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
    cuota_periodo = prestamo_data[6]  # cuota_periodo está en posición 6
    modalidad_pago = prestamo_data[7] if len(prestamo_data) > 7 else None
    fecha_base_calculo = prestamo_data[8] if len(prestamo_data) > 8 else None
    
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
        
        # Hacer rollback si hay una transacción fallida anterior
        try:
            db.rollback()
        except:
            pass
        
        # Usar consulta SQL directa para evitar problemas con columnas faltantes en el modelo
        query_prestamo = text("""
            SELECT id, cedula, total_financiamiento, fecha_aprobacion, 
                   numero_cuotas, tasa_interes, cuota_periodo, modalidad_pago,
                   fecha_base_calculo
            FROM prestamos
            WHERE id = :prestamo_id
        """)
        
        result_prestamo = db.execute(query_prestamo, {'prestamo_id': prestamo_id})
        prestamo_row = result_prestamo.fetchone()
        
        if not prestamo_row:
            logger.error(f"❌ Préstamo {prestamo_id} no encontrado")
            return False
        
        # Ahora obtener el objeto Prestamo usando solo las columnas que existen
        # Durante la migración, excluir columnas que aún no existen en la BD
        # El modelo se mantiene completo para cuando la migración esté completa
        prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).options(
            defer(Prestamo.valor_activo),  # Columna de migración pendiente
            defer(Prestamo.ml_impago_nivel_riesgo_calculado),  # Columna de migración pendiente
            defer(Prestamo.ml_impago_probabilidad_calculada),  # Columna de migración pendiente
            defer(Prestamo.ml_impago_calculado_en),  # Columna de migración pendiente
            defer(Prestamo.ml_impago_modelo_id)  # Columna de migración pendiente
        ).first()
        
        if not prestamo:
            logger.error(f"❌ No se pudo cargar objeto Prestamo {prestamo_id}")
            return False
        
        # Cargar explícitamente los atributos necesarios desde los datos del query SQL
        # para evitar que SQLAlchemy intente cargar columnas faltantes
        prestamo.total_financiamiento = Decimal(str(prestamo_row[2]))
        prestamo.numero_cuotas = prestamo_row[4]
        prestamo.tasa_interes = Decimal(str(prestamo_row[5])) if prestamo_row[5] is not None else Decimal('0')
        prestamo.cuota_periodo = Decimal(str(prestamo_row[6]))
        prestamo.modalidad_pago = prestamo_row[7]
        
        # Validar que tenga fecha_base_calculo o usar fecha_aprobacion
        fecha_base = None
        fecha_base_calculo = prestamo_row[8]  # fecha_base_calculo está en posición 8
        fecha_aprobacion = prestamo_row[3]  # fecha_aprobacion está en posición 3
        
        if fecha_base_calculo:
            fecha_base = fecha_base_calculo
            if isinstance(fecha_base, datetime):
                fecha_base = fecha_base.date()
        elif fecha_aprobacion:
            fecha_base = fecha_aprobacion.date() if isinstance(fecha_aprobacion, datetime) else fecha_aprobacion
        else:
            fecha_base = date.today()
            logger.warning(f"⚠️ Préstamo {prestamo_id}: Sin fecha_aprobacion, usando fecha actual: {fecha_base}")
        
        if dry_run:
            numero_cuotas = prestamo_row[4]  # numero_cuotas está en posición 4
            cedula = prestamo_row[1]  # cedula está en posición 1
            logger.info(f"[DRY RUN] Generaría {numero_cuotas} cuotas para préstamo {prestamo_id} (Cédula: {cedula}, Fecha base: {fecha_base})")
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
        # Hacer rollback para limpiar la transacción fallida
        try:
            db.rollback()
        except:
            pass
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
        # Verificar si hay una variable de entorno que confirme automáticamente
        auto_confirm = os.getenv("AUTO_CONFIRM_GENERAR_CUOTAS", "").upper() == "SI"
        
        if not auto_confirm:
            try:
                respuesta = input("ADVERTENCIA: Estas seguro de que quieres generar cuotas REALES? (escribe 'SI' para continuar): ")
                if respuesta != 'SI':
                    logger.info("Operacion cancelada por el usuario")
                    return
            except (UnicodeEncodeError, UnicodeDecodeError, EOFError):
                # Si hay problemas de encoding o no hay entrada disponible, usar confirmación automática
                logger.warning("No se pudo solicitar confirmacion interactiva. Continuando automaticamente...")
        else:
            logger.info("Confirmacion automatica activada via variable de entorno AUTO_CONFIRM_GENERAR_CUOTAS=SI")
    
    # Conectar a la base de datos con manejo robusto de encoding
    database_url = None
    
    # Primero intentar desde variables de entorno (raw)
    try:
        raw_url = os.getenv("DATABASE_URL")
        if raw_url:
            if isinstance(raw_url, bytes):
                try:
                    database_url = raw_url.decode('utf-8')
                except UnicodeDecodeError:
                    database_url = raw_url.decode('latin1', errors='replace')
            else:
                database_url = raw_url
    except:
        pass
    
    # Si no está disponible, intentar desde settings
    if not database_url:
        try:
            database_url = getattr(settings, 'DATABASE_URL', None)
            if isinstance(database_url, bytes):
                try:
                    database_url = database_url.decode('utf-8')
                except UnicodeDecodeError:
                    database_url = database_url.decode('latin1', errors='replace')
        except:
            pass
    
    if not database_url:
        logger.error("❌ No se encontró DATABASE_URL")
        return
    
    # Parsear y reconstruir la URL de forma segura
    try:
        parsed = urllib.parse.urlparse(str(database_url))
        
        # Re-codificar componentes de manera segura
        if parsed.password:
            password = urllib.parse.quote(str(parsed.password), safe='')
        else:
            password = ''
        
        if parsed.username:
            username = urllib.parse.quote(str(parsed.username), safe='')
        else:
            username = ''
        
        # Reconstruir URL
        netloc = f"{username}:{password}@{parsed.hostname}" if username or password else parsed.hostname
        if parsed.port:
            netloc += f":{parsed.port}"
        
        database_url = urllib.parse.urlunparse((
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
    except Exception as e:
        logger.warning(f"⚠️ Error parseando DATABASE_URL: {e}, usando URL original")
    
    # Configurar connect_args para PostgreSQL
    connect_args = {}
    if database_url.startswith("postgresql"):
        connect_args = {
            "client_encoding": "UTF8",
            "connect_timeout": 10
        }
    
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False,
        connect_args=connect_args,
        pool_reset_on_return="commit",
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
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
        
        # Control de tiempo para reportes cada 10 minutos
        tiempo_inicio = time.time()
        ultimo_reporte_tiempo = tiempo_inicio
        intervalo_reporte_tiempo = 600  # 10 minutos en segundos
        
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
            
            # Verificar si es momento de reporte basado en tiempo (cada 10 minutos)
            tiempo_actual = time.time()
            tiempo_desde_ultimo_reporte = tiempo_actual - ultimo_reporte_tiempo
            
            # Informe periódico cada intervalo_reporte préstamos, cada 10 minutos, o al final
            debe_reportar = False
            motivo_reporte = ""
            
            if total_procesados % intervalo_reporte == 0:
                debe_reportar = True
                motivo_reporte = f"cada {intervalo_reporte} préstamos"
            elif tiempo_desde_ultimo_reporte >= intervalo_reporte_tiempo:
                debe_reportar = True
                motivo_reporte = "cada 10 minutos"
                ultimo_reporte_tiempo = tiempo_actual
            elif total_procesados == len(prestamos):
                debe_reportar = True
                motivo_reporte = "finalización"
            
            if debe_reportar:
                porcentaje = (total_procesados / len(prestamos)) * 100
                tiempo_total_transcurrido = tiempo_actual - tiempo_inicio
                minutos_transcurridos = int(tiempo_total_transcurrido // 60)
                segundos_transcurridos = int(tiempo_total_transcurrido % 60)
                
                # Calcular velocidad y tiempo estimado restante
                if total_procesados > 0:
                    velocidad = total_procesados / tiempo_total_transcurrido  # préstamos por segundo
                    prestamos_restantes = len(prestamos) - total_procesados
                    if velocidad > 0:
                        segundos_restantes = prestamos_restantes / velocidad
                        minutos_restantes = int(segundos_restantes // 60)
                        segundos_restantes_int = int(segundos_restantes % 60)
                        tiempo_estimado = f"{minutos_restantes}m {segundos_restantes_int}s"
                    else:
                        tiempo_estimado = "calculando..."
                else:
                    tiempo_estimado = "calculando..."
                
                logger.info("\n" + "=" * 80)
                logger.info(f"📊 INFORME DE AVANCE - {total_procesados}/{len(prestamos)} préstamos procesados ({porcentaje:.1f}%)")
                logger.info(f"⏰ Reporte: {motivo_reporte}")
                logger.info("=" * 80)
                logger.info(f"✅ Generaciones exitosas: {generaciones_exitosas}")
                logger.info(f"❌ Generaciones fallidas: {generaciones_fallidas}")
                logger.info(f"⚠️ Préstamos inválidos: {prestamos_invalidos}")
                logger.info(f"📈 Progreso: {total_procesados}/{len(prestamos)} ({porcentaje:.1f}%)")
                logger.info(f"⏱️ Tiempo transcurrido: {minutos_transcurridos}m {segundos_transcurridos}s")
                if total_procesados < len(prestamos):
                    logger.info(f"⏳ Pendientes: {len(prestamos) - total_procesados}")
                    logger.info(f"🔮 Tiempo estimado restante: {tiempo_estimado}")
                logger.info("=" * 80 + "\n")
        
        # Resumen final
        tiempo_total_final = time.time() - tiempo_inicio
        minutos_finales = int(tiempo_total_final // 60)
        segundos_finales = int(tiempo_total_final % 60)
        horas_finales = minutos_finales // 60
        minutos_finales_resto = minutos_finales % 60
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 RESUMEN FINAL - PROCESO COMPLETADO")
        logger.info("=" * 80)
        logger.info(f"Total préstamos encontrados: {total_prestamos}")
        logger.info(f"Préstamos válidos: {prestamos_validos}")
        logger.info(f"Préstamos inválidos: {prestamos_invalidos}")
        logger.info(f"✅ Generaciones exitosas: {generaciones_exitosas}")
        logger.info(f"❌ Generaciones fallidas: {generaciones_fallidas}")
        logger.info(f"⏱️ Tiempo total: {horas_finales}h {minutos_finales_resto}m {segundos_finales}s")
        if generaciones_exitosas > 0:
            velocidad_promedio = generaciones_exitosas / tiempo_total_final
            logger.info(f"⚡ Velocidad promedio: {velocidad_promedio:.2f} préstamos/segundo")
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
