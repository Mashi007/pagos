#!/usr/bin/env python3
"""
Aplica mejoras: scheduler leader en main.py y SQL en scheduler_leader.py.
Ejecutar desde la raíz del repo: python scripts/apply_scheduler_and_logging_fixes.py
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_PY = os.path.join(ROOT, "backend", "app", "main.py")
SCHEDULER_LEADER_PY = os.path.join(ROOT, "backend", "app", "core", "scheduler_leader.py")


def apply_main_py(path: str) -> bool:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1) Logging UTF-8
    old_log = '''# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)'''
    new_log = '''# Configurar logging con UTF-8 para tildes/caracteres en Render
import sys
import io
_log_stream = io.TextIOWrapper(getattr(sys.stderr, "buffer", sys.stderr), encoding="utf-8", errors="replace")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=_log_stream,
    force=True,
)
logger = logging.getLogger(__name__)'''
    if old_log in content:
        content = content.replace(old_log, new_log, 1)
    else:
        print("  [main.py] Bloque logging no encontrado (puede estar ya aplicado)")
        return False

    # 2) Scheduler leader en startup
    old_sched = """    # Scheduler: reportes de cobranzas a las 6:00 y 13:00 (America/Caracas)
    try:
        start_scheduler()
    except Exception as e:
        logger.exception("No se pudo iniciar el scheduler de reportes cobranzas: %s", e)"""
    new_sched = """    # Scheduler: solo un worker (leader) inicia los jobs para evitar duplicados con --workers 2
    try:
        from app.core.database import SessionLocal
        from app.core.scheduler_leader import try_claim_scheduler_leader, start_scheduler_leader_heartbeat
        db = SessionLocal()
        try:
            if try_claim_scheduler_leader(db):
                start_scheduler()
                start_scheduler_leader_heartbeat()
                app.state._scheduler_leader = True
            else:
                app.state._scheduler_leader = False
        finally:
            db.close()
    except Exception as e:
        logger.exception("No se pudo iniciar el scheduler de reportes cobranzas: %s", e)"""
    if old_sched in content:
        content = content.replace(old_sched, new_sched, 1)
    else:
        print("  [main.py] Bloque scheduler startup no encontrado")

    # 3) Shutdown con heartbeat
    old_shut = """@app.on_event("shutdown")
def on_shutdown():
    \"\"\"Detener scheduler al cerrar la aplicación.\"\"\"
    try:
        from app.core.scheduler import stop_scheduler
        stop_scheduler()
    except Exception as e:
        logger.warning("Al detener scheduler: %s", e)"""
    new_shut = """@app.on_event("shutdown")
def on_shutdown():
    \"\"\"Detener scheduler y heartbeat de leader al cerrar la aplicación.\"\"\"
    try:
        if getattr(app.state, "_scheduler_leader", False):
            from app.core.scheduler_leader import stop_scheduler_leader_heartbeat
            stop_scheduler_leader_heartbeat()
        from app.core.scheduler import stop_scheduler
        stop_scheduler()
    except Exception as e:
        logger.warning("Al detener scheduler: %s", e)"""
    if old_shut in content:
        content = content.replace(old_shut, new_shut, 1)
    else:
        # intentar con "aplicaci�n" (mojibake)
        old_shut_alt = """@app.on_event("shutdown")
def on_shutdown():
    \"\"\"Detener scheduler al cerrar la aplicaci"""
        if old_shut_alt in content:
            content = re.sub(
                r'@app\.on_event\("shutdown"\)\s+def on_shutdown\(\):.*?logger\.warning\("Al detener scheduler: %s", e\)',
                new_shut.replace(""""", '"').replace(""""", '"'),
                content,
                count=1,
                flags=re.DOTALL,
            )
        else:
            print("  [main.py] Bloque shutdown no encontrado")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def apply_scheduler_leader_py(path: str) -> bool:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    old_sql = """    r = db.execute(text(\"\"\"
        UPDATE scheduler_leader
        SET instance_id = :instance_id, heartbeat = now()
        WHERE id = 1
          AND (heartbeat IS NULL OR heartbeat < now() - :stale_interval)
    \"\"\"), {"instance_id": instance, "stale_interval": f"{SCHEDULER_LEADER_STALE_SEC} seconds"})"""
    new_sql = """    r = db.execute(text(\"\"\"
        UPDATE scheduler_leader
        SET instance_id = :instance_id, heartbeat = now()
        WHERE id = 1
          AND (heartbeat IS NULL OR heartbeat < now() - :stale_sec * interval '1 second')
    \"\"\"), {"instance_id": instance, "stale_sec": SCHEDULER_LEADER_STALE_SEC})"""

    old = """    r = db.execute(text(\"\"\"
        UPDATE scheduler_leader
        SET instance_id = :instance_id, heartbeat = now()
        WHERE id = 1
          AND (heartbeat IS NULL OR heartbeat < now() - :stale_interval)
    \"\"\"), {"instance_id": instance, "stale_interval": f"{SCHEDULER_LEADER_STALE_SEC} seconds"})"""
    new = """    r = db.execute(text(\"\"\"
        UPDATE scheduler_leader
        SET instance_id = :instance_id, heartbeat = now()
        WHERE id = 1
          AND (heartbeat IS NULL OR heartbeat < now() - :stale_sec * interval '1 second')
    \"\"\"), {"instance_id": instance, "stale_sec": SCHEDULER_LEADER_STALE_SEC})"""
    if old in content:
        content = content.replace(old, new, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    if "stale_sec * interval" in content:
        print("  [scheduler_leader.py] Ya aplicado")
        return True
    print("  [scheduler_leader.py] Bloque no encontrado")
    return False


def main():
    print("Aplicando mejoras scheduler leader y logging...")
    if os.path.isfile(MAIN_PY):
        ok = apply_main_py(MAIN_PY)
        print("  main.py:", "OK" if ok else "revisar manualmente")
    else:
        print("  main.py no encontrado:", MAIN_PY)
    if os.path.isfile(SCHEDULER_LEADER_PY):
        ok = apply_scheduler_leader_py(SCHEDULER_LEADER_PY)
        print("  scheduler_leader.py:", "OK" if ok else "revisar manualmente")
    else:
        print("  scheduler_leader.py no encontrado:", SCHEDULER_LEADER_PY)
    print("Listo. Ver docs/MEJORAS_SCHEDULER_LEADER_Y_LOGGING.md si algo falla.")


if __name__ == "__main__":
    main()
