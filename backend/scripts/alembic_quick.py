#!/usr/bin/env python
"""
Script rápido y simple para ejecutar comandos comunes de Alembic.
Versión simplificada sin timeouts complejos, para uso rápido.

Uso: python scripts/alembic_quick.py [comando]
"""
import os
import sys
from pathlib import Path

# Configurar codificación UTF-8 para Windows
if sys.platform == "win32":
    import io
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Cambiar al directorio backend
backend_dir = Path(__file__).parent.parent
if Path.cwd() != backend_dir:
    os.chdir(backend_dir)

# Cargar .env
env_file = backend_dir / ".env"
if env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
    except ImportError:
        pass

# Importar y configurar Alembic
try:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(backend_dir / "alembic.ini"))

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        cfg.set_main_option("sqlalchemy.url", database_url)

    # Ejecutar comando
    if len(sys.argv) < 2:
        cmd = "current"
    else:
        cmd = sys.argv[1].lower()

    if cmd == "current":
        command.current(cfg, verbose=True)
    elif cmd == "heads":
        command.heads(cfg, verbose=True)
    elif cmd == "upgrade":
        target = sys.argv[2] if len(sys.argv) > 2 else "head"
        command.upgrade(cfg, target)
    else:
        print(f"Comando desconocido: {cmd}")
        print("Comandos: current, heads, upgrade [target]")
        sys.exit(1)

except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)

