#!/usr/bin/env python3
"""
Script de despliegue completo para descarga de pagos aprobados.

Este script:
1. Aplica la migración Alembic (si no está aplicada)
2. Ejecuta la migración de datos existentes
3. Verifica integridad

Uso:
    python tools/_deploy_descarga_pagos.py
"""

import sys
import subprocess
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_command(cmd, description):
    """Ejecuta comando y retorna True si es exitoso."""
    logger.info(f"\n{'='*70}")
    logger.info(f"▶️  {description}")
    logger.info(f"{'='*70}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.stdout:
            logger.info(result.stdout)
        
        if result.returncode != 0:
            logger.error(f"❌ Error: {result.stderr}")
            return False
        
        logger.info("✅ Completado")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error ejecutando comando: {e}")
        return False


def main():
    logger.info("=" * 70)
    logger.info("DESPLIEGUE: Descarga de Pagos Aprobados")
    logger.info("=" * 70)
    logger.info(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    steps = [
        (
            "cd backend && alembic upgrade head",
            "Paso 1/3: Aplicar migración Alembic (crear tabla pagos_pendiente_descargar)"
        ),
        (
            "python tools/_migrate_pagos_aprobados_a_tabla_temporal.py",
            "Paso 2/3: Migrar pagos aprobados existentes"
        ),
        (
            "python -c \"import sys; sys.path.insert(0, 'backend'); from app.core.database import SessionLocal; from app.models import PagoPendienteDescargar; db = SessionLocal(); count = db.query(PagoPendienteDescargar).count(); print(f'✅ Verificación: {count} pagos en tabla temporal')\"",
            "Paso 3/3: Verificar integridad"
        ),
    ]
    
    all_success = True
    
    for cmd, description in steps:
        if not run_command(cmd, description):
            all_success = False
            logger.error(f"Fallo en: {description}")
            break
    
    logger.info("\n" + "=" * 70)
    if all_success:
        logger.info("✅ DESPLIEGUE COMPLETADO EXITOSAMENTE")
        logger.info("\nProximos pasos:")
        logger.info("1. Reiniciar la aplicación backend")
        logger.info("2. Ir a https://rapicredit.onrender.com/pagos/cobros/pagos-reportados")
        logger.info("3. Hacer click en 'Descargar de Tabla Temporal' para descargar pagos aprobados")
    else:
        logger.error("❌ DESPLIEGUE FALLIDO - Revisa los errores arriba")
    
    logger.info("=" * 70)
    logger.info(f"Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(main())
