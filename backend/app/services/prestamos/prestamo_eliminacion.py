"""Eliminación completa de un préstamo y dependencias (uso interno / scripts)."""
from __future__ import annotations

import logging

from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.auditoria_cambios_estado_prestamo import AuditoriaCambiosEstadoPrestamo
from app.models.auditoria_cartera_revision import AuditoriaCarteraRevision
from app.models.auditoria_conciliacion_manual import AuditoriaConciliacionManual
from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.datos_importados_conerrores import DatosImportadosConErrores
from app.models.envio_notificacion import EnvioNotificacion
from app.models.pago import Pago
from app.models.pago_con_error import PagoConError
from app.models.prestamo import Prestamo
from app.models.reporte_contable_cache import ReporteContableCache
from app.models.revision_manual_prestamo import RevisionManualPrestamo

logger = logging.getLogger(__name__)


def eliminar_prestamo_por_id(db: Session, prestamo_id: int) -> None:
    """
    Elimina un préstamo y limpia filas hijas (misma lógica que DELETE /prestamos/{id}).
    No hace commit; el llamador controla la transacción.
    """
    pid = int(prestamo_id)
    row = db.get(Prestamo, pid)
    if row is None:
        raise ValueError(f"prestamo_id={pid} no encontrado")

    db.execute(
        delete(RevisionManualPrestamo).where(RevisionManualPrestamo.prestamo_id == pid)
    )
    db.execute(
        delete(AuditoriaCambiosEstadoPrestamo).where(
            AuditoriaCambiosEstadoPrestamo.prestamo_id == pid
        )
    )
    db.execute(
        delete(AuditoriaCarteraRevision).where(AuditoriaCarteraRevision.prestamo_id == pid)
    )
    db.execute(
        update(EnvioNotificacion)
        .where(EnvioNotificacion.prestamo_id == pid)
        .values(prestamo_id=None)
    )
    db.execute(
        update(DatosImportadosConErrores)
        .where(DatosImportadosConErrores.prestamo_id == pid)
        .values(prestamo_id=None)
    )
    db.execute(
        text("UPDATE pagos SET estado = :estado WHERE prestamo_id = :pid"),
        {"estado": "ANULADO_IMPORT", "pid": pid},
    )
    db.execute(
        text("UPDATE pagos SET prestamo_id = NULL WHERE prestamo_id = :pid"),
        {"pid": pid},
    )
    db.execute(
        update(PagoConError).where(PagoConError.prestamo_id == pid).values(prestamo_id=None)
    )

    cuota_ids = list(db.scalars(select(Cuota.id).where(Cuota.prestamo_id == pid)).all())
    if cuota_ids:
        db.execute(delete(CuotaPago).where(CuotaPago.cuota_id.in_(cuota_ids)))
        db.execute(
            delete(AuditoriaConciliacionManual).where(
                AuditoriaConciliacionManual.cuota_id.in_(cuota_ids)
            )
        )
        db.execute(
            delete(ReporteContableCache).where(ReporteContableCache.cuota_id.in_(cuota_ids))
        )

    db.execute(delete(Cuota).where(Cuota.prestamo_id == pid))
    db.flush()
    db.delete(row)
    db.flush()
