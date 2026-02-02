"""
Envío de email con link a Google Sheet del informe de pagos (6:00, 13:00, 16:30 America/Caracas).
Usa destinatarios y texto desde informe_pagos_config_holder; SMTP desde email_config_holder.
"""
import logging
from datetime import datetime
from typing import List

import pytz

from app.core.informe_pagos_config_holder import (
    get_destinatarios_informe_emails,
    get_google_sheets_id,
    sync_from_db as informe_sync,
)
from app.core.email import send_email
from app.core.email_config_holder import sync_from_db as email_sync

logger = logging.getLogger(__name__)

TZ = "America/Caracas"

# Etiquetas por periodo para el asunto/cuerpo
PERIODO_LABEL = {"6am": "6:00 AM", "1pm": "1:00 PM", "4h30": "4:30 PM"}


def _periodo_actual() -> str:
    """Devuelve '6am' | '1pm' | '4h30' según la hora actual (America/Caracas)."""
    tz = pytz.timezone(TZ)
    now = datetime.now(tz)
    h, m = now.hour, now.minute
    if h < 6 or (h == 6 and m == 0):
        return "6am"
    if h < 13 or (h == 13 and m == 0):
        return "1pm"
    if h < 16 or (h == 16 and m < 30):
        return "4h30"
    return "6am"


def enviar_informe_pagos_email() -> bool:
    """
    Envía correo con link a la Google Sheet del informe de pagos (periodo actual).
    Asunto: Informe de pagos – [fecha] – [6:00 AM / 1:00 PM / 4:30 PM].
    Cuerpo: Envío informe de pagos del [fecha] - [hora]. Ver detalle en la hoja: [LINK].
    Si no hay destinatarios o no hay Sheet configurado, no envía y devuelve False.
    """
    informe_sync()
    email_sync()
    destinatarios = get_destinatarios_informe_emails()
    if not destinatarios:
        logger.warning("Informe pagos: no hay destinatarios configurados.")
        return False
    sheet_id = get_google_sheets_id()
    if not sheet_id:
        logger.warning("Informe pagos: no hay Google Sheet configurado.")
        return False
    link = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
    tz = pytz.timezone(TZ)
    now = datetime.now(tz)
    fecha_str = now.strftime("%d/%m/%Y")
    periodo = _periodo_actual()
    hora_label = PERIODO_LABEL.get(periodo, periodo)
    asunto = f"Informe de pagos – {fecha_str} – {hora_label}"
    cuerpo = (
        f"Envío informe de pagos del {fecha_str} - {hora_label}. "
        f"Ver detalle en la hoja: {link}"
    )
    ok, err = send_email(to_emails=destinatarios, subject=asunto, body_text=cuerpo)
    if ok:
        logger.info("Informe pagos enviado a %s destinatarios (%s).", len(destinatarios), hora_label)
    else:
        logger.warning("Informe pagos no enviado: %s", err)
    return ok
