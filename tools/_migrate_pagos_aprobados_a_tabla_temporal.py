#!/usr/bin/env python3
"""
Script de migración: Copiar pagos aprobados existentes a tabla pagos_pendiente_descargar.

Este script debe ejecutarse DESPUÉS de aplicar la migración Alembic 021.
Migra todos los pagos en estado "aprobado" que no hayan sido descargados aún
a la tabla temporal pagos_pendiente_descargar.

Uso:
    python tools/_migrate_pagos_aprobados_a_tabla_temporal.py
"""

import sys
import logging
from datetime import datetime

# Agregar path del proyecto
sys.path.insert(0, 'backend')

from app.core.database import SessionLocal, engine
from app.models import Base, PagoReportado, PagoReportadoExportado, PagoPendienteDescargar
from sqlalchemy import select

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_pagos_aprobados():
    """
    Migra pagos aprobados existentes a la tabla temporal.
    
    Lógica:
    - Obtiene todos los pagos en estado "aprobado"
    - Excluye los que ya están marcados como exportados
    - Los inserta en pagos_pendiente_descargar
    """
    db = SessionLocal()
    
    try:
        logger.info("=" * 70)
        logger.info("INICIANDO MIGRACIÓN: Pagos Aprobados → Tabla Temporal")
        logger.info("=" * 70)
        
        # 1. Obtener IDs de pagos ya marcados como exportados
        exportados_ids = db.execute(
            select(PagoReportadoExportado.pago_reportado_id)
        ).scalars().all()
        
        exportados_set = set(exportados_ids)
        logger.info(f"Pagos ya marcados como exportados: {len(exportados_set)}")
        
        # 2. Obtener pagos aprobados que NO están en la tabla temporal
        pagos_aprobados = db.execute(
            select(PagoReportado).where(
                PagoReportado.estado == "aprobado"
            )
        ).scalars().all()
        
        logger.info(f"Total pagos en estado 'aprobado': {len(pagos_aprobados)}")
        
        # 3. Filtrar: solo los que no estén ya en tabla temporal
        pagos_pendiente_ya = db.execute(
            select(PagoPendienteDescargar.pago_reportado_id)
        ).scalars().all()
        
        pendiente_set = set(pagos_pendiente_ya)
        logger.info(f"Pagos ya en tabla temporal: {len(pendiente_set)}")
        
        # 4. Insertar los que no estén
        nuevos_pagos = []
        contador = 0
        
        for pago in pagos_aprobados:
            if pago.id not in pendiente_set and pago.id not in exportados_set:
                nuevo_registro = PagoPendienteDescargar(
                    pago_reportado_id=pago.id
                )
                db.add(nuevo_registro)
                nuevos_pagos.append(pago.id)
                contador += 1
                
                logger.debug(
                    f"  ✓ Agregado pago #{pago.referencia_interna} "
                    f"(ID: {pago.id}) - Cliente: {pago.nombres} {pago.apellidos}"
                )
        
        if contador > 0:
            db.commit()
            logger.info("")
            logger.info("=" * 70)
            logger.info(f"✅ MIGRACIÓN EXITOSA")
            logger.info(f"   Pagos migrados: {contador}")
            logger.info(f"   Pagos aprobados ya descargados (excluidos): {len(exportados_set)}")
            logger.info(f"   Pagos aprobados ya en tabla temporal (excluidos): {len(pendiente_set)}")
            logger.info("=" * 70)
            logger.info("")
            logger.info("Los pagos ya están disponibles para descargar desde el botón")
            logger.info("'Descargar de Tabla Temporal' en /pagos/cobros/pagos-reportados")
            logger.info("")
            return True
        else:
            logger.info("")
            logger.info("=" * 70)
            logger.info("⚠️  NO HAY PAGOS PARA MIGRAR")
            logger.info("   - Todos los aprobados ya están descargados, O")
            logger.info("   - Todos los aprobados ya están en tabla temporal")
            logger.info("=" * 70)
            logger.info("")
            return False
        
    except Exception as e:
        logger.error(f"❌ ERROR durante la migración: {e}", exc_info=True)
        db.rollback()
        return False
    finally:
        db.close()


def validate_migration():
    """
    Valida que la migración se completó correctamente.
    """
    db = SessionLocal()
    
    try:
        logger.info("Validando integridad de la migración...")
        
        # Verificar que no hay duplicados
        subquery = select(PagoPendienteDescargar.pago_reportado_id)
        todos = db.execute(subquery).scalars().all()
        unicos = set(todos)
        
        if len(todos) != len(unicos):
            logger.warning(f"⚠️  Se detectaron duplicados en tabla temporal (se ignorarán)")
        
        # Verificar que todos los registros son aprobados
        pagos_en_tabla = db.execute(
            select(PagoReportado).where(
                PagoReportado.id.in_(unicos)
            )
        ).scalars().all()
        
        no_aprobados = [p for p in pagos_en_tabla if p.estado != "aprobado"]
        
        if no_aprobados:
            logger.warning(f"⚠️  Se encontraron {len(no_aprobados)} pagos no-aprobados en tabla temporal")
            for p in no_aprobados:
                logger.warning(f"    - {p.referencia_interna}: {p.estado}")
        else:
            logger.info(f"✅ Validación completada: {len(unicos)} pagos aprobados en tabla temporal")
        
        return len(no_aprobados) == 0
        
    except Exception as e:
        logger.error(f"Error durante validación: {e}", exc_info=True)
        return False
    finally:
        db.close()


if __name__ == "__main__":
    logger.info(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Ejecutar migración
    success = migrate_pagos_aprobados()
    
    # Validar
    if success:
        validate_migration()
    
    logger.info(f"Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    sys.exit(0 if success else 1)
