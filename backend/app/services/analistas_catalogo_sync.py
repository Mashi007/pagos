"""
Rellena la tabla analistas desde distinct(prestamos.analista) cuando el catálogo está vacío.
Misma lógica que la migración 026; sirve si el deploy no corrió alembic o la tabla quedó vacía.
"""
import logging

from sqlalchemy import func, select, text
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.analista import Analista
from app.models.prestamo import Prestamo

logger = logging.getLogger(__name__)


def sincronizar_analistas_desde_prestamos_si_catalogo_vacio(db: Session) -> None:
    """
    Si no hay filas en analistas pero sí hay analista en préstamos, inserta catálogo y enlaza analista_id.
    Idempotente: si ya hay analistas, no hace nada. PostgreSQL (btrim / ON CONFLICT).
    """
    try:
        n = db.scalar(select(func.count()).select_from(Analista)) or 0
    except ProgrammingError as e:
        db.rollback()
        logger.warning("analistas: tabla inexistente o error de esquema (¿migración 026?): %s", e)
        return
    except SQLAlchemyError as e:
        db.rollback()
        logger.warning("analistas: no se pudo contar catálogo: %s", e)
        return

    if n > 0:
        return

    try:
        has = db.scalar(
            select(func.count()).select_from(Prestamo).where(
                Prestamo.analista.isnot(None),
                func.trim(Prestamo.analista) != "",
            )
        ) or 0
    except SQLAlchemyError:
        db.rollback()
        return

    if has == 0:
        return

    try:
        db.execute(
            text(
                """
                INSERT INTO analistas (nombre, activo, created_at, updated_at)
                SELECT d.nombre, true, now(), now()
                FROM (
                    SELECT DISTINCT btrim(analista) AS nombre
                    FROM prestamos
                    WHERE analista IS NOT NULL AND btrim(analista) <> ''
                ) d
                WHERE NOT EXISTS (SELECT 1 FROM analistas a WHERE a.nombre = d.nombre)
                """
            )
        )
        db.execute(
            text(
                """
                UPDATE prestamos p
                SET analista_id = a.id
                FROM analistas a
                WHERE btrim(p.analista) = a.nombre
                """
            )
        )
        db.commit()
        logger.info("analistas: catálogo poblado desde préstamos (backfill en caliente)")
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("analistas: fallo al sincronizar desde préstamos: %s", e)
