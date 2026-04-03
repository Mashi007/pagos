# Scheduler leader election - only one process runs the scheduler when using multiple workers/instances.
# Used by app.core.scheduler.start_scheduler().
#
# Con Gunicorn --workers N, solo un proceso debe ejecutar APScheduler. Si el worker lider muere o se recicla,
# los demas no vuelven a llamar try_claim en el arranque; por eso hay un watcher en todos los procesos que
# reclama el liderazgo cuando el heartbeat en BD queda obsoleto y arranca el scheduler aqui.

import logging
import os
import socket
import threading
import time
from typing import Optional

from sqlalchemy import text

logger = logging.getLogger(__name__)

# Heartbeat interval; leader must refresh before this expires so another process can take over.
SCHEDULER_LEADER_HEARTBEAT_INTERVAL_SEC = 30
# If heartbeat is older than this, another process may claim leadership.
SCHEDULER_LEADER_STALE_SEC = 120
# Cada cuanto un worker no lider intenta convertirse en lider (y arrancar scheduler si hace falta).
SCHEDULER_LEADER_WATCH_INTERVAL_SEC = 45


def _instance_id() -> str:
    """Unique identifier for this process (host + pid)."""
    return f"{socket.gethostname()}-{os.getpid()}"


def _ensure_scheduler_leader_table(db) -> None:
    """Create scheduler_leader table if it does not exist. Single row id=1."""
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS scheduler_leader (
            id INT PRIMARY KEY,
            instance_id TEXT,
            heartbeat TIMESTAMPTZ
        )
    """))
    db.execute(text("""
        INSERT INTO scheduler_leader (id, instance_id, heartbeat)
        VALUES (1, NULL, NULL)
        ON CONFLICT (id) DO NOTHING
    """))
    db.commit()


def try_claim_scheduler_leader(db, *, log_if_not_claimed: bool = True) -> bool:
    """
    Try to become the scheduler leader. Returns True if this process is now the leader.
    Only one process should get True; others should skip starting the scheduler.
    """
    _ensure_scheduler_leader_table(db)
    instance = _instance_id()
    # Claim row if no leader or heartbeat is stale
    r = db.execute(text("""
        UPDATE scheduler_leader
        SET instance_id = :instance_id, heartbeat = now()
        WHERE id = 1
          AND (heartbeat IS NULL OR heartbeat < now() - :stale_sec * interval '1 second')
    """), {"instance_id": instance, "stale_sec": SCHEDULER_LEADER_STALE_SEC})
    db.commit()
    if r.rowcount == 1:
        logger.info("Scheduler leader claimed by %s", instance)
        return True
    if log_if_not_claimed:
        logger.info("Scheduler no iniciado: otro proceso es lider (instance=%s)", instance)
    return False


def _current_leader_instance_id(db) -> Optional[str]:
    _ensure_scheduler_leader_table(db)
    row = db.execute(text("SELECT instance_id FROM scheduler_leader WHERE id = 1")).scalar()
    return str(row) if row is not None else None


def refresh_scheduler_leader_heartbeat(db) -> bool:
    """Refresh our heartbeat so we keep leadership. Returns True if we still own the row."""
    instance = _instance_id()
    r = db.execute(text("""
        UPDATE scheduler_leader
        SET heartbeat = now()
        WHERE id = 1 AND instance_id = :instance_id
    """), {"instance_id": instance})
    db.commit()
    return r.rowcount == 1


_heartbeat_stop = threading.Event()
_heartbeat_thread: Optional[threading.Thread] = None
_watcher_stop = threading.Event()
_watcher_thread: Optional[threading.Thread] = None


def _heartbeat_loop() -> None:
    """Background thread: refresh leader heartbeat every SCHEDULER_LEADER_HEARTBEAT_INTERVAL_SEC."""
    from app.core.database import SessionLocal
    while not _heartbeat_stop.wait(timeout=SCHEDULER_LEADER_HEARTBEAT_INTERVAL_SEC):
        db = SessionLocal()
        try:
            if not refresh_scheduler_leader_heartbeat(db):
                logger.warning(
                    "Scheduler leader heartbeat: perdimos liderazgo; deteniendo scheduler en este proceso"
                )
                try:
                    from app.core.scheduler import stop_scheduler

                    stop_scheduler()
                except Exception:
                    pass
                break
        except Exception as e:
            logger.warning("Scheduler leader heartbeat error: %s", e)
        finally:
            db.close()


def start_scheduler_leader_heartbeat_if_needed() -> None:
    """Inicia el hilo de heartbeat una sola vez por proceso (lider)."""
    global _heartbeat_thread
    if _heartbeat_thread is not None and _heartbeat_thread.is_alive():
        return
    _heartbeat_stop.clear()
    _heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
    _heartbeat_thread.start()
    logger.info("Scheduler leader heartbeat iniciado (cada %ds)", SCHEDULER_LEADER_HEARTBEAT_INTERVAL_SEC)


def start_scheduler_leader_heartbeat() -> None:
    """Compat: igual que start_scheduler_leader_heartbeat_if_needed."""
    start_scheduler_leader_heartbeat_if_needed()


def stop_scheduler_leader_heartbeat() -> None:
    """Stop the heartbeat thread (e.g. on shutdown)."""
    _heartbeat_stop.set()


def _ensure_scheduler_started_in_this_process() -> None:
    """Si este proceso es (o acaba de ser) lider y no hay scheduler, arranca APScheduler + heartbeat."""
    from app.core.scheduler import start_scheduler, scheduler_is_running

    if scheduler_is_running():
        start_scheduler_leader_heartbeat_if_needed()
        return
    start_scheduler()
    start_scheduler_leader_heartbeat_if_needed()


def _scheduler_leader_watcher_loop() -> None:
    from app.core.database import SessionLocal

    while not _watcher_stop.wait(timeout=SCHEDULER_LEADER_WATCH_INTERVAL_SEC):
        db = SessionLocal()
        try:
            claimed = try_claim_scheduler_leader(db, log_if_not_claimed=False)
            if claimed:
                _ensure_scheduler_started_in_this_process()
                continue
            me = _instance_id()
            leader_id = _current_leader_instance_id(db)
            if leader_id == me:
                _ensure_scheduler_started_in_this_process()
        except Exception as e:
            logger.warning("Scheduler leader watcher: %s", e)
        finally:
            db.close()


def start_scheduler_leader_watcher() -> None:
    """
    Todos los workers deben llamar esto en startup. Reclama liderazgo si el anterior proceso murio
    (heartbeat obsoleto en BD) y arranca el scheduler en este proceso.
    """
    global _watcher_thread
    if _watcher_thread is not None and _watcher_thread.is_alive():
        return
    _watcher_stop.clear()
    _watcher_thread = threading.Thread(target=_scheduler_leader_watcher_loop, daemon=True)
    _watcher_thread.start()
    logger.info(
        "Scheduler leader watcher iniciado (cada %ds; stale=%ds)",
        SCHEDULER_LEADER_WATCH_INTERVAL_SEC,
        SCHEDULER_LEADER_STALE_SEC,
    )


def stop_scheduler_leader_watcher() -> None:
    _watcher_stop.set()
