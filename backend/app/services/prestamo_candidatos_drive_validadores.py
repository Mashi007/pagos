"""
Validadores compartidos para snapshot y guardado de candidatos préstamo (Drive / CONCILIACIÓN).

1) Formato de cédula: se delega a `validate_cedula` en el job y en `_motivos_no_100`.
2) Tabla `prestamos` (misma cédula normalizada):
   - **V** o **E**: máximo **un** préstamo en estado **APROBADO** (LIQUIDADO y otros no cuentan).
   - **J** (jurídico): puede tener **uno o más** créditos; no aplica el tope de un solo APROBADO.
3) Sin duplicado en hoja: `duplicada_en_hoja` en payload (conteo por columna E en refresh).
"""
from __future__ import annotations

from typing import Dict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.prestamo import Prestamo


def cedula_cmp_es_tipo_venezolano_v(cmp_e: str) -> bool:
    """
    True si la cédula normalizada corresponde a documento con letra V
    (primera letra de la clave comparada, p. ej. V12345678).
    """
    u = (cmp_e or "").strip().upper()
    return bool(u) and u[0] == "V"


def cedula_cmp_es_tipo_j(cmp_e: str) -> bool:
    """True si la cédula normalizada empieza por **J** (persona jurídica / RIF típico)."""
    u = (cmp_e or "").strip().upper()
    return bool(u) and u[0] == "J"


def cedula_cmp_es_tipo_v_o_e(cmp_e: str) -> bool:
    """
    True si la cédula normalizada empieza por **V** o **E** (misma clave que carga masiva).
    Regla de negocio: solo pueden tener un préstamo en cartera; más de uno no cumple validador.
    """
    u = (cmp_e or "").strip().upper()
    return bool(u) and u[0] in ("V", "E")


def _conteo_prestamos_por_cedula_norm_filtrado(
    db: Session,
    *,
    solo_aprobado: bool,
) -> Dict[str, int]:
    """Conteo por cédula normalizada (misma regla que check-cédulas / carga masiva)."""
    from app.api.v1.endpoints.clientes import _normalizar_cedula_carga_masiva

    stmt = select(Prestamo.cedula)
    if solo_aprobado:
        stmt = stmt.where(func.upper(func.trim(func.coalesce(Prestamo.estado, ""))) == "APROBADO")
    out: Dict[str, int] = {}
    for cel in db.execute(stmt).scalars().all() or []:
        n = _normalizar_cedula_carga_masiva(cel or "")
        if not n:
            continue
        out[n] = out.get(n, 0) + 1
    return out


def conteo_prestamos_por_cedula_norm(db: Session) -> Dict[str, int]:
    """Total de filas en `prestamos` por cédula (cualquier estado)."""
    return _conteo_prestamos_por_cedula_norm_filtrado(db, solo_aprobado=False)


def conteo_prestamos_aprobados_por_cedula_norm(db: Session) -> Dict[str, int]:
    """
    Préstamos en estado APROBADO por cédula normalizada.
    Regla V/E en Drive: máximo un APROBADO activo; LIQUIDADO u otros no bloquean un nuevo alta.
    """
    return _conteo_prestamos_por_cedula_norm_filtrado(db, solo_aprobado=True)
