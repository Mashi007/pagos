"""
Correos internos para solicitudes de reapertura de revisión manual (Visto → cola admin).

- Al crear solicitud: aviso a administradores (usuarios activos rol admin + contactos tickets_notify).
- Al aprobar: aviso al operario para que vea el préstamo en «En revisión» (?) en la lista.

Los envíos son best-effort: fallos SMTP no bloquean la operación en API.
"""
from __future__ import annotations

import logging
from typing import List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.email import send_email
from app.core.email_config_holder import get_tickets_notify_emails, sync_from_db
from app.core.rol_normalization import canonical_rol
from app.models.user import User

logger = logging.getLogger(__name__)


def _dedupe_emails(emails: Sequence[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for raw in emails:
        e = (raw or "").strip()
        if not e or "@" not in e:
            continue
        k = e.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(e)
    return out


def collect_destinatarios_admin_revision_manual(db: Session) -> List[str]:
    """
    Emails para avisar de nuevas solicitudes de reapertura:
    - Usuarios activos con rol canónico admin.
    - Más contactos de Configuración > Email (tickets_notify_emails), sin duplicar.
    """
    sync_from_db()
    from_db: List[str] = []
    try:
        rows = db.execute(select(User.email, User.rol).where(User.is_active.is_(True))).all()
        for email, rol in rows:
            if canonical_rol(rol if isinstance(rol, str) else None) != "admin":
                continue
            if email and isinstance(email, str) and "@" in email.strip():
                from_db.append(email.strip())
    except Exception:
        logger.exception("revision_manual_reapertura: no se pudo listar emails de administradores")

    tickets = get_tickets_notify_emails()
    return _dedupe_emails(list(from_db) + list(tickets))


def notify_admins_nueva_solicitud_reapertura(
    db: Session,
    *,
    prestamo_id: int,
    solicitante_etiqueta: str,
    mensaje_operario: Optional[str],
    solicitud_id: int,
) -> None:
    dest = collect_destinatarios_admin_revision_manual(db)
    if not dest:
        logger.warning(
            "revision_manual_reapertura: sin destinatarios admin/tickets para aviso solicitud_id=%s prestamo_id=%s",
            solicitud_id,
            prestamo_id,
        )
        return

    subject = f"[Revisión manual] Solicitud de reapertura — préstamo #{prestamo_id}"
    body_lines = [
        "Un operario solicitó reabrir la revisión manual de un préstamo que estaba en Visto (revisado).",
        "",
        f"Préstamo: #{prestamo_id}",
        f"Solicitud: #{solicitud_id}",
        f"Solicitante: {solicitante_etiqueta or '(sin identificar)'}",
    ]
    if mensaje_operario and str(mensaje_operario).strip():
        body_lines.extend(["", "Mensaje del operario:", str(mensaje_operario).strip()])
    body_lines.extend(
        [
            "",
            "En el sistema: Administración → Autorizaciones (revisión manual), o la ruta",
            "/pagos/administracion/autorizaciones-revision-manual",
            "",
            "Tras aprobar, el préstamo queda en «En revisión» (?) y el operario podrá editarlo.",
        ]
    )
    body = "\n".join(body_lines)

    try:
        ok, err = send_email(dest, subject, body, servicio="tickets")
        if not ok:
            logger.warning(
                "revision_manual_reapertura: fallo SMTP aviso admin solicitud_id=%s err=%s",
                solicitud_id,
                (err or "")[:500],
            )
        else:
            logger.info(
                "revision_manual_reapertura: correo admin enviado solicitud_id=%s prestamo_id=%s dest_n=%s",
                solicitud_id,
                prestamo_id,
                len(dest),
            )
    except Exception:
        logger.exception(
            "revision_manual_reapertura: excepción al enviar correo admin solicitud_id=%s",
            solicitud_id,
        )


def notify_operario_solicitud_reapertura_aprobada(
    *,
    prestamo_id: int,
    operario_email: Optional[str],
    admin_etiqueta: str,
) -> None:
    to = (operario_email or "").strip()
    if not to or "@" not in to:
        logger.info(
            "revision_manual_reapertura: sin email operario; no se envía aviso de aprobación prestamo_id=%s",
            prestamo_id,
        )
        return

    subject = f"[Revisión manual] Solicitud aprobada — préstamo #{prestamo_id}"
    body = "\n".join(
        [
            f"Su solicitud para reabrir la revisión del préstamo #{prestamo_id} fue aprobada.",
            "",
            "El préstamo quedó en estado «En revisión» (?). Puede continuar en Revisión manual:",
            "actualice la lista o vuelva a entrar a la pantalla para ver el icono de revisando.",
            "",
            f"Resuelto por: {admin_etiqueta or 'administrador'}",
        ]
    )

    try:
        ok, err = send_email([to], subject, body, servicio="tickets")
        if not ok:
            logger.warning(
                "revision_manual_reapertura: fallo SMTP aviso operario prestamo_id=%s err=%s",
                prestamo_id,
                (err or "")[:500],
            )
        else:
            logger.info(
                "revision_manual_reapertura: correo operario enviado prestamo_id=%s",
                prestamo_id,
            )
    except Exception:
        logger.exception(
            "revision_manual_reapertura: excepción al enviar correo operario prestamo_id=%s",
            prestamo_id,
        )
