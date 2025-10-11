# app/db/base.py
"""
Importar Base y todos los modelos para que Alembic los detecte.
IMPORTANTE: Las importaciones de modelos se hacen de forma lazy para evitar ciclos circulares.
"""

from app.db.session import Base

# NO importar modelos aquí directamente - causa importación circular al startup
# Los modelos se importarán cuando sea necesario (en init_db.py o en migraciones)

__all__ = ["Base"]
