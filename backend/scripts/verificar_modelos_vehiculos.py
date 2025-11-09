#!/usr/bin/env python3
"""
Script para verificar modelos de vehículos en la base de datos
"""

import sys
import logging
from pathlib import Path

from sqlalchemy import create_engine, text
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verificar_modelos_vehiculos():
    """Verificar modelos de vehículos en la base de datos"""
    try:
        engine = create_engine(settings.DATABASE_URL)

        with engine.connect() as conn:
            # Verificar si la tabla existe
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'modelos_vehiculos'
                )
            """))
            tabla_existe = result.scalar()

            if not tabla_existe:
                logger.error("❌ La tabla modelos_vehiculos no existe")
                return

            logger.info("✅ La tabla modelos_vehiculos existe")

            # Contar registros
            result = conn.execute(text("SELECT COUNT(*) FROM modelos_vehiculos"))
            total = result.scalar()
            logger.info(f"📊 Total de modelos: {total}")

            # Obtener algunos registros
            result = conn.execute(text("""
                SELECT id, nombre, marca, activo
                FROM modelos_vehiculos
                LIMIT 10
            """))

            for registro in result:
                estado = "✅ Activo" if registro.activo else "❌ Inactivo"
                logger.info(f"   - ID: {registro.id}, Nombre: {registro.nombre}, Marca: {registro.marca}, {estado}")

    except Exception as e:
        logger.error(f"❌ Error verificando modelos de vehículos: {e}")


if __name__ == "__main__":
    verificar_modelos_vehiculos()
