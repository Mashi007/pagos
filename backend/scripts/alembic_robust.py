#!/usr/bin/env python
"""
Script robusto para ejecutar comandos de Alembic con timeouts y manejo de errores mejorado.
Evita congelamientos usando la API de Alembic directamente con timeouts.

Uso: python scripts/alembic_robust.py [comando] [opciones]
Ejemplos:
    python scripts/alembic_robust.py current
    python scripts/alembic_robust.py heads
    python scripts/alembic_robust.py upgrade head
"""
import os
import sys
import signal
import threading
from pathlib import Path
from typing import Optional, Any
import time

# Configurar codificación UTF-8 para Windows
if sys.platform == "win32":
    import io
    try:
        if hasattr(sys.stdout, 'buffer'):
            if sys.stdout.encoding != 'utf-8':
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        elif hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

    try:
        if hasattr(sys.stderr, 'buffer'):
            if sys.stderr.encoding != 'utf-8':
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        elif hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Timeout global (30 segundos por defecto)
TIMEOUT_SECONDS = 30

class TimeoutError(Exception):
    """Excepción para timeouts"""
    pass

def timeout_handler(signum, frame):
    """Manejador de timeout para Unix"""
    raise TimeoutError("Operación excedió el tiempo límite")

def run_with_timeout(func, timeout_seconds: int = TIMEOUT_SECONDS) -> Any:
    """
    Ejecuta una función con timeout usando threading.
    Funciona en Windows y Unix.
    """
    result = [None]
    exception = [None]
    done = threading.Event()

    def target():
        try:
            result[0] = func()
        except Exception as e:
            exception[0] = e
        finally:
            done.set()

    thread = threading.Thread(target=target, daemon=True)
    thread.start()

    if done.wait(timeout=timeout_seconds):
        if exception[0]:
            raise exception[0]
        return result[0]
    else:
        # Timeout alcanzado
        raise TimeoutError(f"Operación excedió el tiempo límite de {timeout_seconds} segundos")

def load_env_file(env_file: Path) -> None:
    """Cargar variables de entorno desde .env"""
    if not env_file.exists():
        return

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

def get_alembic_config() -> 'Config':
    """Obtener configuración de Alembic de forma segura"""
    from alembic.config import Config

    # Asegurar que estamos en el directorio backend
    backend_dir = Path(__file__).parent.parent
    if Path.cwd() != backend_dir:
        os.chdir(backend_dir)
        print(f"[INFO] Cambiado al directorio: {backend_dir}")

    # Verificar que alembic.ini existe
    alembic_ini = backend_dir / "alembic.ini"
    if not alembic_ini.exists():
        raise FileNotFoundError(f"No se encontró alembic.ini en {alembic_ini}")

    # Cargar variables de entorno
    env_file = backend_dir / ".env"
    load_env_file(env_file)

    # Crear configuración
    cfg = Config(str(alembic_ini))

    # Configurar DATABASE_URL si está disponible
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        cfg.set_main_option("sqlalchemy.url", database_url)
    elif not cfg.get_main_option("sqlalchemy.url"):
        print("[WARNING] DATABASE_URL no está configurada. Algunos comandos pueden fallar.")

    return cfg

def execute_command_safe(cmd: str, args: list, timeout: int = TIMEOUT_SECONDS) -> None:
    """Ejecutar comando de Alembic de forma segura con timeout"""
    from alembic import command

    def _execute():
        cfg = get_alembic_config()

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
        elif cmd == "check":
            # Verificar estado sin ejecutar migraciones
            from alembic.script import ScriptDirectory
            script = ScriptDirectory.from_config(cfg)
            heads = script.get_revisions("heads")
            print(f"[INFO] Heads detectados: {len(heads)}")
            for head in heads:
                print(f"  - {head.revision}: {head.doc}")
            current = command.current(cfg)
            if current:
                print(f"[INFO] Revisión actual: {current}")
            else:
                print("[INFO] No hay revisión aplicada")
        else:
            raise ValueError(f"Comando desconocido: {cmd}")

    try:
        print(f"[INFO] Ejecutando comando '{cmd}' con timeout de {timeout}s...")
        start_time = time.time()
        run_with_timeout(_execute, timeout_seconds=timeout)
        elapsed = time.time() - start_time
        print(f"[SUCCESS] Comando completado en {elapsed:.2f}s")
    except TimeoutError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        print("[ERROR] El comando se congeló y fue cancelado por timeout", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Error ejecutando comando: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    """Función principal"""
    if len(sys.argv) < 2:
        print("Uso: python scripts/alembic_robust.py [comando] [opciones]")
        print("\nComandos disponibles:")
        print("  current          - Mostrar revisión actual")
        print("  heads            - Mostrar todas las cabezas")
        print("  history          - Mostrar historial de migraciones")
        print("  upgrade [target] - Aplicar migraciones (default: head)")
        print("  downgrade [target] - Revertir migraciones (default: -1)")
        print("  stamp [target]   - Marcar revisión sin ejecutar")
        print("  check            - Verificar estado sin ejecutar")
        print("\nOpciones:")
        print("  --sql            - Mostrar SQL sin ejecutar")
        print("  --verbose, -v    - Modo verbose")
        print("  --timeout N      - Timeout en segundos (default: 30)")
        sys.exit(1)

    # Parsear argumentos
    cmd = sys.argv[1].lower()
    args = sys.argv[2:] if len(sys.argv) > 2 else []

    # Extraer timeout si está presente
    timeout = TIMEOUT_SECONDS
    if "--timeout" in args:
        idx = args.index("--timeout")
        if idx + 1 < len(args):
            try:
                timeout = int(args[idx + 1])
                args = args[:idx] + args[idx + 2:]
            except ValueError:
                print("[WARNING] Timeout inválido, usando valor por defecto")

    # Ejecutar comando
    execute_command_safe(cmd, args, timeout=timeout)

if __name__ == "__main__":
    main()

