"""Usuario de sistema para jobs programados (guardado automático Drive)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.user_utils import user_to_response
from app.models.user import User
from app.schemas.auth import UserResponse


def usuario_respuesta_para_job_scheduler(db: Session) -> UserResponse:
    """
    Usuario con el que se registran altas automáticas nocturnas (préstamos desde Drive).
    Debe existir en tabla `usuarios`; si no, se usa un UserResponse mínimo con el email configurado.
    """
    email = (
        getattr(settings, "SCHEDULER_SYSTEM_USER_EMAIL", None) or "itmaster@rapicreditca.com"
    ).strip()
    row = db.execute(select(User).where(User.email == email).limit(1)).scalars().first()
    if row is not None:
        return user_to_response(row)
    return UserResponse(
        id=0,
        email=email,
        nombre="Sistema",
        apellido="Scheduler",
        cargo=None,
        rol="admin",
        is_active=True,
        created_at="",
        updated_at=None,
        last_login=None,
    )


def email_usuario_para_job_scheduler() -> str:
    return (
        getattr(settings, "SCHEDULER_SYSTEM_USER_EMAIL", None) or "itmaster@rapicreditca.com"
    ).strip()
