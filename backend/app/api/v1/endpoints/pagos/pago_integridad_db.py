"""Utilidades para errores de integridad en BD."""

from typing import Optional


def _integridad_error_pgcode_y_constraint(exc: BaseException) -> tuple[Optional[str], str]:
    """Obtiene pgcode y nombre de restricción desde IntegrityError (psycopg2 vía SQLAlchemy)."""
    orig = getattr(exc, "orig", None)
    pgcode = getattr(orig, "pgcode", None) or getattr(exc, "pgcode", None)
    if pgcode is not None and not isinstance(pgcode, str):
        pgcode = str(pgcode)
    cname = ""
    diag = getattr(orig, "diag", None)
    if diag is not None:
        cname = str(getattr(diag, "constraint_name", "") or "")
    return (pgcode if isinstance(pgcode, str) else None, cname.strip())
