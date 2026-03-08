# Script para aplicar mejoras en pagos_gmail.py (timezone, lock)
import os

path = os.path.join(os.path.dirname(__file__), "app", "api", "v1", "endpoints", "pagos_gmail.py")
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# 1. Insertar _is_pipeline_running antes de @router.post("/run-now")
old_router = 'router = APIRouter(dependencies=[Depends(get_current_user)])\n\n\n@router.post("/run-now")'
new_router = '''router = APIRouter(dependencies=[Depends(get_current_user)])


def _is_pipeline_running(db: Session) -> bool:
    """True si hay una sync en estado running iniciada en los últimos 12 minutos."""
    cutoff = datetime.utcnow() - timedelta(minutes=12)
    row = db.execute(
        select(PagosGmailSync).where(
            and_(
                PagosGmailSync.status == "running",
                PagosGmailSync.started_at >= cutoff,
            )
        ).limit(1)
    ).scalars().first()
    return row is not None


@router.post("/run-now")'''
if "_is_pipeline_running" not in c:
    c = c.replace(old_router, new_router)

# 2. Añadir comprobación de lock en run_now
old_run = '''    """Ejecuta el pipeline una vez (Gmail -> Drive -> Gemini -> Sheets)."""
    sync_id, status = run_pipeline(db)'''
new_run = '''    """Ejecuta el pipeline una vez (Gmail -> Drive -> Gemini -> Sheets)."""
    if _is_pipeline_running(db):
        raise HTTPException(
            status_code=409,
            detail="Ya hay una sincronización en curso. Espere unos minutos.",
        )
    sync_id, status = run_pipeline(db)'''
if "Ya hay una sincronización" not in c:
    c = c.replace(old_run, new_run)

# 3. Timezone America/Caracas en _get_sheet_date_for_download
old_tz = '''def _get_sheet_date_for_download() -> datetime:
    """Después de las 23:50 se considera el día siguiente para la descarga."""
    now = datetime.utcnow()
    if now.hour == 23 and now.minute >= 50:
        return now + timedelta(days=1)
    return now'''
new_tz = '''def _get_sheet_date_for_download() -> datetime:
    """Después de las 23:50 (America/Caracas) se considera el día siguiente."""
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("America/Caracas")
    now = datetime.now(tz)
    base = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if now.hour == 23 and now.minute >= 50:
        base += timedelta(days=1)
    return base.replace(tzinfo=None)'''
if "America/Caracas" not in c or "ZoneInfo" not in c:
    c = c.replace(old_tz, new_tz)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("patch_pagos_gmail.py: aplicado.")
