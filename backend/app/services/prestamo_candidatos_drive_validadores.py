"""
Validadores compartidos para snapshot y guardado de candidatos préstamo (Drive / CONCILIACIÓN).

1) Formato de cédula: se delega a `validate_cedula` en el job y en `_motivos_no_100`.
2) Tabla `prestamos` (misma cédula normalizada): tipo **V** — a lo sumo un préstamo (no segundo crédito).
3) Sin duplicado en hoja: `duplicada_en_hoja` en payload (conteo por columna E en refresh).
"""
from __future__ import annotations

from typing import Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.prestamo import Prestamo


def cedula_cmp_es_tipo_venezolano_v(cmp_e: str) -> bool:
    """
    True si la cédula normalizada corresponde a documento venezolano con letra V
    (primera letra de la clave comparada, p. ej. V12345678).
    """
    u = (cmp_e or "").strip().upper()
    return bool(u) and u[0] == "V"


def conteo_prestamos_por_cedula_norm(db: Session) -> Dict[str, int]:
    """Número de filas en `prestamos` por cédula normalizada (misma regla que check-cédulas)."""
    from app.api.v1.endpoints.clientes import _normalizar_cedula_carga_masiva

    out: Dict[str, int] = {}
    for cel in db.execute(select(Prestamo.cedula)).scalars().all() or []:
        n = _normalizar_cedula_carga_masiva(cel or "")
        if not n:
            continue
        out[n] = out.get(n, 0) + 1
    return out
