"""
Script para corregir masivamente el formato científico en numero_documento
⚠️ IMPORTANTE: Ejecutar con precaución. Hacer backup completo antes de ejecutar.
"""

import logging
import re
from decimal import Decimal
from typing import List, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _normalizar_numero_documento(numero_documento: str) -> Tuple[str, bool]:
    """
    Normaliza el número de documento, convirtiendo formato científico a string completo.
    
    Returns:
        Tuple[str, bool]: (número normalizado, si fue modificado)
    """
    if not numero_documento:
        return '', False
    
    numero_str = str(numero_documento).strip()
    
    if not numero_str:
        return '', False
    
    # Detectar formato científico (ej: 7.40087E+14, 1.23e+5)
    if 'e' in numero_str.lower() and ('+' in numero_str or '-' in numero_str):
        try:
            # Convertir de formato científico a float y luego a int (sin decimales)
            numero_float = float(numero_str)
            numero_int = int(numero_float)
            numero_normalizado = str(numero_int)
            return numero_normalizado, True
        except (ValueError, OverflowError):
            logger.warning(f"⚠️ No se pudo normalizar número científico: {numero_str}")
            return numero_str, False
    
    return numero_str, False


def identificar_pagos_con_formato_cientifico(db):
    """Identifica todos los pagos con formato científico en numero_documento"""
    query = text("""
        SELECT id, cedula, prestamo_id, numero_documento, monto_pagado, conciliado
        FROM pagos
        WHERE activo = true
          AND (
            numero_documento ~* '^[0-9]+\\.[0-9]+E\\+[0-9]+$'
            OR numero_documento ~* '^[0-9]+\\.[0-9]+e\\+[0-9]+$'
            OR numero_documento ~* '^[0-9]+\\.[0-9]+E-[0-9]+$'
            OR numero_documento ~* '^[0-9]+\\.[0-9]+e-[0-9]+$'
          )
        ORDER BY id
    """)
    
    result = db.execute(query)
    return result.fetchall()


def verificar_duplicados_antes_correccion(db, numero_original: str, numero_normalizado: str) -> int:
    """Verifica cuántos pagos ya tienen el número normalizado"""
    query = text("""
        SELECT COUNT(*) 
        FROM pagos 
        WHERE activo = true 
          AND numero_documento = :numero_normalizado
          AND numero_documento != :numero_original
    """)
    
    result = db.execute(query, {
        'numero_normalizado': numero_normalizado,
        'numero_original': numero_original
    })
    return result.scalar() or 0


def corregir_pago(db, pago_id: int, numero_original: str, numero_normalizado: str, dry_run: bool = True):
    """Corrige el numero_documento de un pago"""
    if dry_run:
        logger.info(f"[DRY RUN] Pago ID {pago_id}: '{numero_original}' → '{numero_normalizado}'")
        return True
    
    # Verificar duplicados antes de actualizar
    duplicados = verificar_duplicados_antes_correccion(db, numero_original, numero_normalizado)
    if duplicados > 0:
        logger.warning(
            f"⚠️ Pago ID {pago_id}: El número normalizado '{numero_normalizado}' "
            f"ya existe en {duplicados} otros pagos. Revisar manualmente."
        )
        return False
    
    # Actualizar el pago
    update_query = text("""
        UPDATE pagos 
        SET numero_documento = :numero_normalizado,
            fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE id = :pago_id
    """)
    
    db.execute(update_query, {
        'numero_normalizado': numero_normalizado,
        'pago_id': pago_id
    })
    
    logger.info(f"✅ Pago ID {pago_id} corregido: '{numero_original}' → '{numero_normalizado}'")
    return True


def main(dry_run: bool = True, batch_size: int = 100, limit: int = None):
    """
    Corrección masiva de formato científico en numero_documento
    
    Args:
        dry_run: Si es True, solo muestra qué se haría sin hacer cambios
        batch_size: Tamaño del lote para procesar
        limit: Límite de pagos a procesar (None = todos)
    """
    logger.info("=" * 80)
    logger.info("🔧 CORRECCIÓN MASIVA DE FORMATO CIENTÍFICO EN NUMERO_DOCUMENTO")
    logger.info("=" * 80)
    logger.info(f"Modo: {'DRY RUN (sin cambios)' if dry_run else 'EJECUCIÓN REAL'}")
    logger.info(f"Tamaño de lote: {batch_size}")
    if limit:
        logger.info(f"Límite: {limit} pagos")
    logger.info("=" * 80)
    
    if not dry_run:
        respuesta = input("⚠️ ¿Estás seguro de que quieres hacer cambios REALES en la base de datos? (escribe 'SI' para continuar): ")
        if respuesta != 'SI':
            logger.info("❌ Operación cancelada por el usuario")
            return
    
    # Conectar a la base de datos
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Identificar pagos con formato científico
        logger.info("🔍 Identificando pagos con formato científico...")
        pagos = identificar_pagos_con_formato_cientifico(db)
        
        total_pagos = len(pagos)
        if limit:
            pagos = pagos[:limit]
            logger.info(f"📊 Total encontrados: {total_pagos}, Procesando: {len(pagos)}")
        else:
            logger.info(f"📊 Total encontrados: {total_pagos}")
        
        if total_pagos == 0:
            logger.info("✅ No se encontraron pagos con formato científico")
            return
        
        # Estadísticas
        correcciones_exitosas = 0
        correcciones_fallidas = 0
        duplicados_detectados = 0
        monto_total_afectado = Decimal('0')
        
        # Procesar por lotes
        for i in range(0, len(pagos), batch_size):
            lote = pagos[i:i + batch_size]
            logger.info(f"\n📦 Procesando lote {i // batch_size + 1} ({len(lote)} pagos)...")
            
            for pago in lote:
                pago_id = pago[0]
                numero_original = pago[3]
                monto = Decimal(str(pago[4])) if pago[4] else Decimal('0')
                
                # Normalizar número
                numero_normalizado, fue_modificado = _normalizar_numero_documento(numero_original)
                
                if not fue_modificado:
                    logger.warning(f"⚠️ Pago ID {pago_id}: No se pudo normalizar '{numero_original}'")
                    correcciones_fallidas += 1
                    continue
                
                # Verificar duplicados
                duplicados = verificar_duplicados_antes_correccion(db, numero_original, numero_normalizado)
                if duplicados > 0:
                    duplicados_detectados += 1
                    logger.warning(
                        f"⚠️ Pago ID {pago_id}: Duplicado potencial. "
                        f"'{numero_original}' → '{numero_normalizado}' (ya existe en {duplicados} pagos)"
                    )
                    # En dry_run, continuar. En ejecución real, podría saltarse o requerir confirmación
                    if not dry_run:
                        continue
                
                # Corregir pago
                if corregir_pago(db, pago_id, numero_original, numero_normalizado, dry_run):
                    correcciones_exitosas += 1
                    monto_total_afectado += monto
                else:
                    correcciones_fallidas += 1
            
            # Commit después de cada lote (solo si no es dry_run)
            if not dry_run:
                db.commit()
                logger.info(f"✅ Lote {i // batch_size + 1} guardado")
        
        # Resumen final
        logger.info("\n" + "=" * 80)
        logger.info("📊 RESUMEN FINAL")
        logger.info("=" * 80)
        logger.info(f"Total pagos encontrados: {total_pagos}")
        logger.info(f"Correcciones exitosas: {correcciones_exitosas}")
        logger.info(f"Correcciones fallidas: {correcciones_fallidas}")
        logger.info(f"Duplicados detectados: {duplicados_detectados}")
        logger.info(f"Monto total afectado: ${monto_total_afectado:,.2f}")
        logger.info("=" * 80)
        
        if dry_run:
            logger.info("\n💡 Para ejecutar los cambios reales, ejecuta:")
            logger.info("   python scripts/python/corregir_formato_cientifico_masivo.py --execute")
        
    except Exception as e:
        logger.error(f"❌ Error durante la corrección: {e}", exc_info=True)
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
