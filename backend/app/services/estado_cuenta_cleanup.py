"""
Limpieza periódica de la tabla estado_cuenta_codigos.

Elimina filas expiradas o ya usadas con más de 24 horas de antigüedad
para evitar crecimiento indefinido de la tabla.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, delete, or_
from sqlalchemy.orm import Session

from app.models.estado_cuenta_codigo import EstadoCuentaCodigo

logger = logging.getLogger(__name__)

# Antigüedad mínima para borrar: 24 horas (códigos expirados o usados hace más de 24 h)
HORAS_RETENCION = 24


def limpiar_estado_cuenta_codigos(db: Session) -> dict:
    """
    Borra de estado_cuenta_codigos las filas que:
    - ya expiraron (expira_en < ahora), o
    - ya fueron usadas y tienen más de 24 h desde creación (usado=True y creado_en < cutoff).

    cutoff = now_utc - 24 horas.
    Retorna {"borrados": N}.
    """
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now_utc - timedelta(hours=HORAS_RETENCION)

    # Borrar: expirados (expira_en < now) O (usados y creados hace más de 24 h)
    stmt = delete(EstadoCuentaCodigo).where(
        or_(
            EstadoCuentaCodigo.expira_en < now_utc,
            and_(
                EstadoCuentaCodigo.usado == True,
                EstadoCuentaCodigo.creado_en < cutoff,
            ),
        )
    )
    result = db.execute(stmt)
    borrados = result.rowcount if hasattr(result, "rowcount") else 0
    db.commit()
    logger.info(
        "estado_cuenta_cleanup: borrados=%s (expirados o usados hace más de %s h)",
        borrados,
        HORAS_RETENCION,
    )
    return {"borrados": borrados}
