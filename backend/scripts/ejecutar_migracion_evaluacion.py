#!/usr/bin/env python3
"""
Script para ejecutar la migración de evaluación de 7 criterios
"""
import os
import sys

# Configurar el path para importar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar variables de entorno
from dotenv import load_dotenv
load_dotenv()

# Importar alembic
from alembic import command
from alembic.config import Config

def main():
    """Ejecutar la migración de Alembic"""
    alembic_cfg = Config("alembic.ini")
    
    # Configurar la URL de la base de datos desde .env
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL no está configurada en .env")
        sys.exit(1)
    
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    
    print("=" * 60)
    print("EJECUTANDO MIGRACIÓN: 7 Criterios de Evaluación")
    print("=" * 60)
    
    try:
        # Ejecutar upgrade
        command.upgrade(alembic_cfg, "head")
        print("\n✅ Migración ejecutada exitosamente")
    except Exception as e:
        print(f"\n❌ Error ejecutando migración: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


