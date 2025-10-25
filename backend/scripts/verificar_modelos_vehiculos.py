#!/usr/bin/env python3
"""
Script para verificar datos de modelos de vehículos
"""

import sys
import os
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verificar_modelos_vehiculos():
    """Verificar datos en la tabla modelos_vehiculos"""
    try:
        # Conectar a la base de datos
        engine = create_engine(settings.DATABASE_URL)

        with engine.connect() as conn:
            # Verificar si la tabla existe
            result = conn.execute(
                text(
                    """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'modelos_vehiculos'
                );
            """
                )
            )
            tabla_existe = result.scalar()

            if not tabla_existe:
                logger.error("❌ La tabla 'modelos_vehiculos' no existe")
                return

            logger.info("✅ La tabla 'modelos_vehiculos' existe")

            # Contar registros totales
            result = conn.execute(text("SELECT COUNT(*) FROM modelos_vehiculos"))
            total_registros = result.scalar()
            logger.info(f"📊 Total de registros: {total_registros}")

            # Contar registros activos
            result = conn.execute(
                text("SELECT COUNT(*) FROM modelos_vehiculos WHERE activo = true")
            )
            registros_activos = result.scalar()
            logger.info(f"✅ Registros activos: {registros_activos}")

            # Mostrar todos los registros
            result = conn.execute(
                text("SELECT id, nombre, activo FROM modelos_vehiculos ORDER BY nombre")
            )
            registros = result.fetchall()

            logger.info("📋 Registros en la tabla:")
            for registro in registros:
                estado = "✅ Activo" if registro.activo else "❌ Inactivo"
                logger.info(
                    f"  ID: {registro.id} | Nombre: {registro.nombre} | {estado}"
                )

            if registros_activos == 0:
                logger.warning(
                    "⚠️ No hay registros activos. Esto explicaría por qué no se cargan los modelos."
                )

    except Exception as e:
        logger.error(f"❌ Error verificando modelos de vehículos: {e}")


if __name__ == "__main__":
    verificar_modelos_vehiculos()
