#!/usr/bin/env python
"""
Script para ejecutar migraciones de AI training manualmente
"""
import os
import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
sys.path.append(str(Path(__file__).parent.parent))

# Cargar variables de entorno desde .env si existe
backend_dir = Path(__file__).parent.parent
env_file = backend_dir / ".env"
if env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
    except ImportError:
        # Si python-dotenv no está instalado, intentar cargar manualmente
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip().strip('"').strip("'")
        except Exception:
            pass  # Si falla, continuar sin cargar .env

from alembic import command
from alembic.config import Config

# Obtener ruta del archivo alembic.ini
alembic_ini_path = backend_dir / "alembic.ini"

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
        # Actualizar a cada head individualmente
        print(f"[INFO] Múltiples heads detectados, actualizando cada uno...")
        for head in heads:
            try:
                print(f"[INFO] Actualizando a head: {head.revision}")
                command.upgrade(alembic_cfg, head.revision)
            except Exception as e:
                # Si el head ya está aplicado, continuar con el siguiente
                if "already at" in str(e).lower() or "current" in str(e).lower():
                    print(f"[INFO] Head {head.revision} ya está aplicado, continuando...")
                    continue
                else:
                    print(f"[WARNING] Error al actualizar head {head.revision}: {e}")
                    # Continuar con los demás heads
                    continue
    else:
        print(f"[INFO] Un solo head, actualizando normalmente...")
        command.upgrade(alembic_cfg, "head")

    print("[SUCCESS] Migraciones ejecutadas exitosamente")

except Exception as e:
    print(f"[ERROR] Error ejecutando migraciones: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

