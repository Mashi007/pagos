#!/usr/bin/env python3
"""
"""

import sys
import logging


from sqlalchemy import create_engine, text
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


    try:
        engine = create_engine(settings.DATABASE_URL)

        with engine.connect() as conn:
            # Verificar si la tabla existe
            result = conn.execute(
                text(
                    """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                );
            """
                )
            )
            tabla_existe = result.scalar()

            if not tabla_existe:
                return



            result = conn.execute(
            )

            result = conn.execute(
            )

                estado = "✅ Activo" if registro.activo else "❌ Inactivo"
                logger.info(
                    f"  ID: {registro.id} | Nombre: {registro.nombre} | {estado}"
                )

                logger.warning(
                )

    except Exception as e:


if __name__ == "__main__":
