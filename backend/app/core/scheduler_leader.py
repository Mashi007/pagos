# Scheduler leader election - only one process runs the scheduler when using multiple workers/instances.
# Used by app.core.scheduler.start_scheduler().

import logging
import os
import socket
import threading
import time
from typing import Optional, Tuple

from sqlalchemy import text

logger = logging.getLogger(__name__)

# Heartbeat interval; leader must refresh before this expires so another process can take over.
SCHEDULER_LEADER_HEARTBEAT_INTERVAL_SEC = 30
# If heartbeat is older than this, another process may claim leadership.
SCHEDULER_LEADER_STALE_SEC = 120


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


def try_claim_scheduler_leader(db) -> bool:
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
    logger.info("Scheduler no iniciado: otro proceso es lider (instance=%s)", instance)
    return False


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


def _heartbeat_loop() -> None:
    """Background thread: refresh leader heartbeat every SCHEDULER_LEADER_HEARTBEAT_INTERVAL_SEC."""
    from app.core.database import SessionLocal
    while not _heartbeat_stop.wait(timeout=SCHEDULER_LEADER_HEARTBEAT_INTERVAL_SEC):
        db = SessionLocal()
        try:
            if not refresh_scheduler_leader_heartbeat(db):
                logger.warning("Scheduler leader heartbeat: perdimos liderazgo")
                break
        except Exception as e:
            logger.warning("Scheduler leader heartbeat error: %s", e)
        finally:
            db.close()


def start_scheduler_leader_heartbeat() -> None:
    """Start the daemon thread that keeps our scheduler leadership."""
    _heartbeat_stop.clear()
    t = threading.Thread(target=_heartbeat_loop, daemon=True)
    t.start()
    logger.info("Scheduler leader heartbeat iniciado (cada %ds)", SCHEDULER_LEADER_HEARTBEAT_INTERVAL_SEC)


def stop_scheduler_leader_heartbeat() -> None:
    """Stop the heartbeat thread (e.g. on shutdown)."""
    _heartbeat_stop.set()
