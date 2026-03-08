# Añadir comprobación de lock en _job_pagos_gmail_pipeline
import os

path = os.path.join(os.path.dirname(__file__), "app", "core", "scheduler.py")
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

old = '''def _job_pagos_gmail_pipeline() -> None:
    """Job cada 15 min: Gmail -> Drive -> Gemini -> Sheets (modulo Pagos)."""
    db = SessionLocal()
    try:
        from app.services.pagos_gmail.pipeline import run_pipeline
        sync_id, status = run_pipeline(db)'''

new = '''def _job_pagos_gmail_pipeline() -> None:
    """Job cada 15 min: Gmail -> Drive -> Gemini -> Sheets (modulo Pagos)."""
    db = SessionLocal()
    try:
        from app.api.v1.endpoints.pagos_gmail import _is_pipeline_running
        from app.services.pagos_gmail.pipeline import run_pipeline
        if _is_pipeline_running(db):
            logger.info("Pagos Gmail pipeline: omitido (ya hay una ejecucion en curso)")
            return
        sync_id, status = run_pipeline(db)'''

if " _is_pipeline_running(db)" not in c or "omitido (ya hay" not in c:
    c = c.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("Scheduler lock: aplicado.")
else:
    print("Scheduler lock: ya estaba aplicado.")
