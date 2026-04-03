"""Correos del area de trabajo Finiquito (operaciones/cobranza y aviso al cliente)."""
from __future__ import annotations

import logging
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.core.email import send_email
from app.models.cliente import Cliente
from app.models.finiquito import FiniquitoCaso

logger = logging.getLogger(__name__)

FINIQUITO_EMAIL_OPERACIONES = "operaciones@rapicreditca.com"
FINIQUITO_EMAIL_COBRANZA = "cobranza@rapicreditca.com"
FINIQUITO_WHATSAPP_LINEA = "424-4579934"


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


def enviar_correo_contactar_cliente_finiquito(
    db: Session,
    caso: FiniquitoCaso,
) -> Tuple[bool, Optional[str]]:
    """Aviso al cliente: proceso de finiquito y linea WhatsApp."""
    if not caso.cliente_id:
        return False, "Caso sin cliente_id; no se puede resolver el correo."
    cl = db.query(Cliente).filter(Cliente.id == caso.cliente_id).first()
    if not cl:
        return False, "Cliente no encontrado."
    to = (cl.email or "").strip()
    if not to or "@" not in to:
        return False, "El cliente no tiene correo electronico registrado."
    subj = "[RapiCredit] Su proceso de finiquito"
    wa = FINIQUITO_WHATSAPP_LINEA
    body = (
        "Estimado/a cliente,\n\n"
        "Le informamos que su proceso de finiquito en RapiCredit esta en gestion.\n\n"
        f"Para cualquier consulta, escribanos al WhatsApp: {wa}.\n\n"
        "Saludos cordiales,\n"
        "RapiCredit\n"
    )
    html = (
        "<p>Estimado/a cliente,</p>"
        "<p>Le informamos que su proceso de finiquito en <strong>RapiCredit</strong> "
        "esta en gestion.</p>"
        "<p>Para cualquier consulta, escribanos al WhatsApp: "
        f"<strong>{wa}</strong>.</p>"
        "<p>Saludos cordiales,<br/>RapiCredit</p>"
    )
    ok, err = send_email([to], subj, body, body_html=html, servicio=None)
    if not ok:
        logger.warning(
            "finiquito contactar_cliente: fallo envio caso_id=%s err=%s",
            caso.id,
            err,
        )
    return ok, err
