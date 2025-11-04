#!/usr/bin/env python3
"""
Script para ejecutar la migración de índices críticos de performance
"""
import os
import sys
from pathlib import Path

# Configurar el path para importar
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(str(backend_dir))

# Configurar variables de entorno
from dotenv import load_dotenv
load_dotenv()

# Importar alembic
from alembic import command
from alembic.config import Config

def main():
    """Ejecutar la migración de índices críticos"""
    alembic_cfg = Config("alembic.ini")
    
    # Configurar la URL de la base de datos desde .env
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL no está configurada en .env")
        sys.exit(1)
    
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    
    print("=" * 70)
    print("🚀 EJECUTANDO MIGRACIÓN: Índices Críticos de Performance")
    print("=" * 70)
    print("📋 Esta migración creará índices para resolver timeouts de 57+ segundos")
    print("📈 Impacto esperado: Reducción de timeouts de 57s a <500ms (114x mejora)")
    print("=" * 70)
    print()
    
    try:
        # Ejecutar upgrade
        command.upgrade(alembic_cfg, "head")
        print()
        print("=" * 70)
        print("✅ Migración ejecutada exitosamente")
        print("=" * 70)
        print()
        print("📊 PRÓXIMOS PASOS:")
        print("1. Verificar que los índices se crearon correctamente")
        print("2. Monitorear tiempos de respuesta en producción")
        print("3. El endpoint /api/v1/notificaciones/estadisticas/resumen debería responder en <500ms")
        print()
    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ Error ejecutando migración: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

