# -*- coding: utf-8 -*-
"""Filtro listado: cédulas con 2+ préstamos no aparecen en Lista de Préstamos."""
from __future__ import annotations

from collections import Counter

from app.utils.cedula_almacenamiento import texto_cedula_comparable_bd


def _claves_duplicadas_por_conteo(cedulas: list[str], *, min_prestamos: int = 2) -> set[str]:
    """Espejo en Python de claves_cedula_con_n_prestamos_en_cartera (misma normalización)."""
    c = Counter(texto_cedula_comparable_bd(x) for x in cedulas if (x or "").strip())
    return {k for k, n in c.items() if k and n >= min_prestamos}


def test_claves_duplicadas_dos_prestamos_misma_cedula():
    dup = _claves_duplicadas_por_conteo(
        ["V21450147", "V21450147", "V99999999"],
    )
    assert dup == {"V21450147"}


def test_claves_sin_duplicado_un_prestamo():
    dup = _claves_duplicadas_por_conteo(["V15276832"])
    assert dup == set()
