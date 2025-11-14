#!/usr/bin/env python
"""
Script helper para ejecutar comandos de Alembic sin problemas de serialización.
Uso: python scripts/alembic_helper.py [comando] [opciones]
Ejemplos:
    python scripts/alembic_helper.py current
    python scripts/alembic_helper.py heads
    python scripts/alembic_helper.py upgrade head
"""
import os
import sys
from pathlib import Path

# Asegurar que estamos en el directorio backend
# El script está en backend/scripts/, así que backend_dir es el padre del directorio scripts
backend_dir = Path(__file__).parent.parent
if Path.cwd() != backend_dir:
    os.chdir(backend_dir)
    print(f"[INFO] Cambiado al directorio: {backend_dir}")

# Verificar que alembic.ini existe
alembic_ini = backend_dir / "alembic.ini"
if not alembic_ini.exists():
    print(f"[ERROR] No se encontro alembic.ini en {alembic_ini}")
    sys.exit(1)

# Ejecutar comando de Alembic
try:
    from alembic import command
    from alembic.config import Config
    
    cfg = Config(str(alembic_ini))
    
    # Obtener comando y argumentos
    if len(sys.argv) < 2:
        print("Uso: python scripts/alembic_helper.py [comando] [opciones]")
        print("Comandos disponibles: current, heads, history, upgrade, downgrade, stamp")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    args = sys.argv[2:] if len(sys.argv) > 2 else []
    
    if cmd == "current":
        command.current(cfg, verbose=True)
    elif cmd == "heads":
        command.heads(cfg, verbose=True)
    elif cmd == "history":
        verbose = "--verbose" in args or "-v" in args
        command.history(cfg, verbose=verbose)
    elif cmd == "upgrade":
        target = args[0] if args else "head"
        sql = "--sql" in args
        command.upgrade(cfg, target, sql=sql)
    elif cmd == "downgrade":
        target = args[0] if args else "-1"
        sql = "--sql" in args
        command.downgrade(cfg, target, sql=sql)
    elif cmd == "stamp":
        target = args[0] if args else "head"
        command.stamp(cfg, target)
    else:
        print(f"[ERROR] Comando desconocido: {cmd}")
        print("Comandos disponibles: current, heads, history, upgrade, downgrade, stamp")
        sys.exit(1)
        
except ImportError as e:
    print(f"[ERROR] Alembic no esta instalado: {e}")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Error ejecutando comando: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

