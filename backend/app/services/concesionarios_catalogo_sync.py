"""
Rellena la tabla concesionarios desde distinct(prestamos.concesionario) cuando el catalogo esta vacio.
Misma logica que la migracion 080; sirve si el deploy no corrio alembic o la tabla quedo vacia.
"""
import logging

from sqlalchemy import func, select, text
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.concesionario import Concesionario
from app.models.prestamo import Prestamo

logger = logging.getLogger(__name__)


def sincronizar_concesionarios_desde_prestamos_si_catalogo_vacio(db: Session) -> None:
    """
    Si no hay filas en concesionarios pero si hay concesionario en prestamos,
    inserta catalogo y enlaza concesionario_id. Idempotente.
    """
    try:
        n = db.scalar(select(func.count()).select_from(Concesionario)) or 0
    except ProgrammingError as e:
        db.rollback()
        logger.warning(
            "concesionarios: tabla inexistente o error de esquema (migracion 080?): %s",
            e,
        )
        return
    except SQLAlchemyError as e:
        db.rollback()
        logger.warning("concesionarios: no se pudo contar catalogo: %s", e)
        return

    if n > 0:
        return

    try:
        has = (
            db.scalar(
                select(func.count())
                .select_from(Prestamo)
                .where(
                    Prestamo.concesionario.isnot(None),
                    func.trim(Prestamo.concesionario) != "",
                )
            )
            or 0
        )
    except SQLAlchemyError:
        db.rollback()
        return

    if has == 0:
        return

    try:
        db.execute(
            text(
                """
                INSERT INTO concesionarios (nombre, activo, created_at, updated_at)
                SELECT d.nombre, true, now(), now()
                FROM (
                    SELECT DISTINCT btrim(concesionario) AS nombre
                    FROM prestamos
                    WHERE concesionario IS NOT NULL AND btrim(concesionario) <> ''
                ) d
                WHERE NOT EXISTS (SELECT 1 FROM concesionarios c WHERE c.nombre = d.nombre)
                """
            )
        )
        db.execute(
            text(
                """
                UPDATE prestamos p
                SET concesionario_id = c.id
                FROM concesionarios c
                WHERE btrim(p.concesionario) = c.nombre
                """
            )
        )
        db.commit()
        logger.info("concesionarios: catalogo poblado desde prestamos (backfill en caliente)")
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("concesionarios: fallo al sincronizar desde prestamos: %s", e)
