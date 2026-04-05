"""Correos del area de trabajo Finiquito (operaciones/cobranza, avisos internos)."""
from __future__ import annotations

import logging
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.core.email import send_email
from app.models.finiquito import FiniquitoCaso

logger = logging.getLogger(__name__)

FINIQUITO_EMAIL_OPERACIONES = "operaciones@rapicreditca.com"
FINIQUITO_EMAIL_COBRANZA = "cobranza@rapicreditca.com"
FINIQUITO_EMAIL_ITMASTER = "itmaster@rapicreditca.com"


def enviar_correo_en_proceso_operaciones(
    db: Session,
    caso: FiniquitoCaso,
    *,
    admin_email: str,
    admin_nombre: str = "",
) -> Tuple[bool, Optional[str]]:
    """Aviso a operaciones y cobranza: cliente en proceso de liberacion (finiquito)."""
    dest = [FINIQUITO_EMAIL_OPERACIONES, FINIQUITO_EMAIL_COBRANZA]
    ced = (caso.cedula or "").strip()
    subj = f"[RapiCredit Finiquito] Inicio proceso liberacion - cedula {ced}"
    admin = (admin_email or "").strip() or "(sin email)"
    nom = (admin_nombre or "").strip()
    firma_admin = f"{nom} ({admin})" if nom else admin
    body = (
        f"Se ha marcado como «En proceso» el caso de finiquito del cliente con cedula {ced}.\n\n"
        f"ID caso finiquito: {caso.id}\n"
        f"ID prestamo: {caso.prestamo_id}\n\n"
        f"Accion registrada en el panel por: {firma_admin}\n"
    )
    ok, err = send_email(dest, subj, body, servicio=None)
    if not ok:
        logger.warning(
            "finiquito en_proceso: fallo envio ops/cobranza caso_id=%s err=%s",
            caso.id,
            err,
        )
    return ok, err


def enviar_correo_rechazo_itmaster(caso: FiniquitoCaso) -> Tuple[bool, Optional[str]]:
    """Aviso generico a IT al marcar Rechazado desde la bandeja principal (admin)."""
    subj = "[RapiCredit Finiquito] revisar caso"
    body = "revisar caso"
    ok, err = send_email([FINIQUITO_EMAIL_ITMASTER], subj, body, servicio=None)
    if not ok:
        logger.warning(
            "finiquito rechazo itmaster: fallo envio caso_id=%s err=%s",
            caso.id,
            err,
        )
    return ok, err
