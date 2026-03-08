"""
Helpers para el cron de Pagos Gmail: crear hoja del día siguiente a las 23:59.
"""
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials
from app.services.pagos_gmail.drive_service import build_drive_service, get_or_create_sheet_for_date

logger = logging.getLogger(__name__)

SCHEDULER_TZ = "America/Caracas"


def ensure_sheet_for_tomorrow() -> None:
    """
    Crea la hoja del día siguiente (Pagos_Cobros_DDMesAAAA) en Drive si no existe.
    Llamar a las 23:59 (America/Caracas) para tener la hoja lista a medianoche.
    """
    creds = get_pagos_gmail_credentials()
    if not creds:
        logger.warning("Pagos Gmail: no credentials, skip ensure_sheet_for_tomorrow")
        return
    try:
        from googleapiclient.discovery import build
        drive_svc, _ = build_drive_service(creds)
        sheets_svc = build("sheets", "v4", credentials=creds, cache_discovery=False)
        tz = ZoneInfo(SCHEDULER_TZ)
        now = datetime.now(tz)
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        sheet_id = get_or_create_sheet_for_date(drive_svc, sheets_svc, tomorrow)
        if sheet_id:
            logger.info("Pagos Gmail: hoja del día siguiente creada/verificada: %s", tomorrow.date())
        else:
            logger.warning("Pagos Gmail: no se pudo crear hoja para %s", tomorrow.date())
    except Exception as e:
        logger.exception("Pagos Gmail ensure_sheet_for_tomorrow: %s", e)
