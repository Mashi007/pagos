#!/usr/bin/env python
"""
Script robusto para generar migraciones de Alembic sin congelamientos.
Evita problemas de importación y conexión a la base de datos.

Uso: python scripts/generar_migracion.py [mensaje] [--rev-id REV_ID]
Ejemplos:
    python scripts/generar_migracion.py "agregar campo nuevo"
    python scripts/generar_migracion.py "actualizar modelo" --rev-id abc123
"""
import os
import sys
import signal
import threading
from pathlib import Path
from typing import Optional
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

# Timeout global (60 segundos para generar migraciones)
TIMEOUT_SECONDS = 60

class TimeoutError(Exception):
    """Excepción para timeouts"""
    pass

def run_with_timeout(func, timeout_seconds: int = TIMEOUT_SECONDS):
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

def get_alembic_config():
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

def generar_migracion(mensaje: str, rev_id: Optional[str] = None):
    """Generar migración de Alembic de forma segura"""
    from alembic import command

    def _generar():
        cfg = get_alembic_config()
        
        # Generar migración con autogenerate
        print(f"[INFO] Generando migración: {mensaje}")
        if rev_id:
            command.revision(
                cfg,
                autogenerate=True,
                message=mensaje,
                rev_id=rev_id
            )
        else:
            command.revision(
                cfg,
                autogenerate=True,
                message=mensaje
            )
        print("[SUCCESS] Migración generada exitosamente")

    try:
        print(f"[INFO] Generando migración con timeout de {TIMEOUT_SECONDS}s...")
        start_time = time.time()
        run_with_timeout(_generar, timeout_seconds=TIMEOUT_SECONDS)
        elapsed = time.time() - start_time
        print(f"[SUCCESS] Migración generada en {elapsed:.2f}s")
    except TimeoutError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        print("[ERROR] La generación de migración se congeló y fue cancelada por timeout", file=sys.stderr)
        print("[INFO] Intenta:", file=sys.stderr)
        print("  1. Verificar que la base de datos esté accesible", file=sys.stderr)
        print("  2. Verificar que no haya procesos bloqueando la BD", file=sys.stderr)
        print("  3. Aumentar el timeout con --timeout N", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Error generando migración: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    """Función principal"""
    if len(sys.argv) < 2:
        print("Uso: python scripts/generar_migracion.py [mensaje] [--rev-id REV_ID] [--timeout N]")
        print("\nEjemplos:")
        print('  python scripts/generar_migracion.py "agregar campo nuevo"')
        print('  python scripts/generar_migracion.py "actualizar modelo" --rev-id abc123')
        print('  python scripts/generar_migracion.py "fix bug" --timeout 120')
        sys.exit(1)

    # Parsear argumentos
    mensaje = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 2 else []
    
    # Extraer rev_id si está presente
    rev_id = None
    if "--rev-id" in args:
        idx = args.index("--rev-id")
        if idx + 1 < len(args):
            rev_id = args[idx + 1]
            args = args[:idx] + args[idx + 2:]
    
    # Extraer timeout si está presente
    global TIMEOUT_SECONDS
    if "--timeout" in args:
        idx = args.index("--timeout")
        if idx + 1 < len(args):
            try:
                TIMEOUT_SECONDS = int(args[idx + 1])
                args = args[:idx] + args[idx + 2:]
            except ValueError:
                print("[WARNING] Timeout inválido, usando valor por defecto")
    
    # Generar migración
    generar_migracion(mensaje, rev_id=rev_id)

if __name__ == "__main__":
    main()

