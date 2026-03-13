# Mejoras: Scheduler leader (1 solo worker) y logging UTF-8

Aplica estos cambios para evitar jobs duplicados con 2 workers y mejorar los logs en Render.

---

## 1. `backend/app/main.py`

### 1.1 Logging UTF-8 (líneas ~20-25)

**Sustituir:**
```python
# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
```

**Por:**
```python
# Configurar logging con UTF-8 para tildes/caracteres en Render
import sys
import io
_log_stream = io.TextIOWrapper(getattr(sys.stderr, "buffer", sys.stderr), encoding="utf-8", errors="replace")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=_log_stream,
    force=True,
)
logger = logging.getLogger(__name__)
```

### 1.2 Scheduler solo en el worker líder (bloque try/except del scheduler en `on_startup`)

**Sustituir:**
```python
    # Scheduler: reportes de cobranzas a las 6:00 y 13:00 (America/Caracas)
    try:
        start_scheduler()
    except Exception as e:
        logger.exception("No se pudo iniciar el scheduler de reportes cobranzas: %s", e)
```

**Por:**
```python
    # Scheduler: solo un worker (leader) inicia los jobs para evitar duplicados con --workers 2
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
        logger.exception("No se pudo iniciar el scheduler de reportes cobranzas: %s", e)
```

### 1.3 Shutdown: parar heartbeat si somos líder

**Sustituir:**
```python
@app.on_event("shutdown")
def on_shutdown():
    """Detener scheduler al cerrar la aplicación."""
    try:
        from app.core.scheduler import stop_scheduler
        stop_scheduler()
    except Exception as e:
        logger.warning("Al detener scheduler: %s", e)
```

**Por:**
```python
@app.on_event("shutdown")
def on_shutdown():
    """Detener scheduler y heartbeat de leader al cerrar la aplicación."""
    try:
        if getattr(app.state, "_scheduler_leader", False):
            from app.core.scheduler_leader import stop_scheduler_leader_heartbeat
            stop_scheduler_leader_heartbeat()
        from app.core.scheduler import stop_scheduler
        stop_scheduler()
    except Exception as e:
        logger.warning("Al detener scheduler: %s", e)
```

---

## 2. `backend/app/core/scheduler_leader.py`

### 2.1 SQL con intervalo válido en PostgreSQL

En `try_claim_scheduler_leader`, el `UPDATE` usa `:stale_interval` como texto y en PostgreSQL no se puede restar un string a `now()`. Hay que usar un entero de segundos y el tipo `interval`.

**Sustituir:**
```python
    r = db.execute(text("""
        UPDATE scheduler_leader
        SET instance_id = :instance_id, heartbeat = now()
        WHERE id = 1
          AND (heartbeat IS NULL OR heartbeat < now() - :stale_interval)
    """), {"instance_id": instance, "stale_interval": f"{SCHEDULER_LEADER_STALE_SEC} seconds"})
```

**Por:**
```python
    r = db.execute(text("""
        UPDATE scheduler_leader
        SET instance_id = :instance_id, heartbeat = now()
        WHERE id = 1
          AND (heartbeat IS NULL OR heartbeat < now() - :stale_sec * interval '1 second')
    """), {"instance_id": instance, "stale_sec": SCHEDULER_LEADER_STALE_SEC})
```

---

## 3. Migración para la tabla `scheduler_leader`

Si la tabla no existe, `_ensure_scheduler_leader_table` la crea al arrancar. En PostgreSQL puro la sintaxis usada es válida. Si usas solo SQLite u otra BD, puede hacer falta una migración Alembic que cree:

```sql
CREATE TABLE IF NOT EXISTS scheduler_leader (
    id INT PRIMARY KEY,
    instance_id TEXT,
    heartbeat TIMESTAMPTZ
);
INSERT INTO scheduler_leader (id, instance_id, heartbeat) VALUES (1, NULL, NULL)
ON CONFLICT (id) DO NOTHING;
```

(En PostgreSQL el tipo correcto es `INTEGER` o `SERIAL`; `TIMESTAMPTZ` es válido.)

---

## Resumen

| Mejora | Archivo | Efecto |
|--------|---------|--------|
| Scheduler leader | main.py + scheduler_leader.py | Solo 1 de los 2 workers ejecuta Campañas CRM, Pagos Gmail, etc. |
| SQL intervalo | scheduler_leader.py | El claim de líder funciona correctamente en PostgreSQL. |
| Logging UTF-8 | main.py | Tildes y caracteres se ven bien en los logs de Render. |

Tras aplicar los cambios, haz deploy; en logs deberías ver en un worker `Scheduler leader claimed by ...` y en el otro `Scheduler no iniciado: otro proceso es lider`.
