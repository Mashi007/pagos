# Parche: un solo proceso ejecuta el scheduler (evitar jobs duplicados y Gmail 429)

## Problema

Con **varios workers** (p. ej. `uvicorn --workers 2`) o **varias instancias** en Render, cada proceso ejecuta `start_scheduler()` en el startup. Eso hace que:

- "Campañas CRM programadas" y "Pagos Gmail pipeline" se ejecuten **dos veces** por intervalo.
- Las dos ejecuciones del pipeline Gmail llaman a la API a la vez y disparan **Gmail 429** (rate limit).

## Solución

Solo **un proceso** debe ser "líder" y arrancar el scheduler. El resto no inicia el scheduler.

Se usa la tabla `scheduler_leader` en la BD: un proceso la reclama y renueva un `heartbeat` cada 30 s. Si ese proceso muere, tras 2 minutos otro puede tomar el control.

## Archivos

1. **Nuevo**: `app/core/scheduler_leader.py`  
   - Crea la tabla `scheduler_leader` si no existe.
   - `try_claim_scheduler_leader(db)` → `True` si este proceso es el líder.
   - Hilo en segundo plano que actualiza `heartbeat` cada 30 s.

2. **Modificar**: `app/core/scheduler.py`

### 1) Añadir imports (después de la línea que importa `SessionLocal`)

```python
from app.core.scheduler_leader import (
    try_claim_scheduler_leader,
    start_scheduler_leader_heartbeat,
)
```

### 2) Al inicio de `start_scheduler()`, antes de crear `_scheduler`

Sustituir:

```python
def start_scheduler() -> None:
    """Inicia el scheduler: ..."""
    global _scheduler
    if _scheduler is not None:
        logger.warning("Scheduler ya esta iniciado.")
        return
    _scheduler = BackgroundScheduler(timezone=SCHEDULER_TZ)
```

por:

```python
def start_scheduler() -> None:
    """Inicia el scheduler solo en el proceso lider (evita jobs duplicados con varios workers)."""
    global _scheduler
    if _scheduler is not None:
        logger.warning("Scheduler ya esta iniciado.")
        return
    db = SessionLocal()
    try:
        if not try_claim_scheduler_leader(db):
            return
    finally:
        db.close()
    _scheduler = BackgroundScheduler(timezone=SCHEDULER_TZ)
```

### 3) Justo después de `_scheduler.start()` (antes del último `logger.info`)

Añadir:

```python
    start_scheduler_leader_heartbeat()
```

para que el proceso líder renueve el heartbeat cada 30 s.

## Tabla creada automáticamente

Al arrancar, el módulo `scheduler_leader` ejecuta:

```sql
CREATE TABLE IF NOT EXISTS scheduler_leader (
    id INT PRIMARY KEY,
    instance_id TEXT,
    heartbeat TIMESTAMPTZ
);
INSERT INTO scheduler_leader (id, instance_id, heartbeat) VALUES (1, NULL, NULL) ON CONFLICT (id) DO NOTHING;
```

No hace falta migración manual.

## Resultado esperado

- Un solo "Running job ... Campañas CRM programadas" por minuto.
- Un solo "Running job ... Pagos Gmail pipeline" cada 15 min.
- Menos probabilidad de Gmail 429 al no duplicar llamadas a la API.

## Gmail 429 (opcional)

Si aun así ves 429, el código actual ya:

- Limita la espera a 120 s (`_GMAIL_429_MAX_WAIT_SECONDS` en `gmail_service.py`).
- Devuelve 0 correos y termina el pipeline sin bloquear 15 min.

Puedes subir `PAGOS_GMAIL_CRON_MINUTES` (p. ej. a 30) para espaciar más las ejecuciones.
