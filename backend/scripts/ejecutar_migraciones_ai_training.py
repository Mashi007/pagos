#!/usr/bin/env python
"""
Script para ejecutar migraciones de AI training manualmente
"""
import os
import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
sys.path.append(str(Path(__file__).parent.parent))

from alembic import command
from alembic.config import Config

# Obtener ruta del archivo alembic.ini
alembic_ini_path = Path(__file__).parent.parent / "alembic.ini"

if not alembic_ini_path.exists():
    print(f"[ERROR] No se encontro alembic.ini en {alembic_ini_path}")
    sys.exit(1)

# Configurar Alembic
alembic_cfg = Config(str(alembic_ini_path))

# Cargar DATABASE_URL desde variables de entorno
database_url = os.getenv("DATABASE_URL")
if not database_url:
    print("[ERROR] DATABASE_URL no esta configurada")
    sys.exit(1)

alembic_cfg.set_main_option("sqlalchemy.url", database_url)

print("[INFO] Ejecutando migraciones de AI training...")
print(f"[INFO] DATABASE_URL: {database_url[:50]}...")

try:
    # Verificar si hay múltiples heads
    from alembic.script import ScriptDirectory
    script = ScriptDirectory.from_config(alembic_cfg)
    heads = script.get_revisions("heads")
    
    print(f"[INFO] Heads detectados: {len(heads)}")
    for head in heads:
        print(f"  - {head.revision}: {head}")
    
    if len(heads) > 1:
        # Buscar el merge point 9537ffbe05a6
        try:
            merge_point = script.get_revision("9537ffbe05a6")
            if merge_point:
                print(f"[INFO] Actualizando a merge point 9537ffbe05a6...")
                command.upgrade(alembic_cfg, "9537ffbe05a6")
            else:
                print(f"[WARNING] Merge point no encontrado, actualizando todos los heads...")
                for head in heads:
                    print(f"[INFO] Actualizando a head: {head.revision}")
                    command.upgrade(alembic_cfg, head.revision)
        except Exception as e:
            print(f"[ERROR] Error al actualizar merge point: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        print(f"[INFO] Un solo head, actualizando normalmente...")
        command.upgrade(alembic_cfg, "head")
    
    print("[SUCCESS] Migraciones ejecutadas exitosamente")
    
except Exception as e:
    print(f"[ERROR] Error ejecutando migraciones: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

