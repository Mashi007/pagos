# -*- coding: utf-8 -*-
"""Filtro listado: solo cédulas con 2+ APROBADO se ocultan (LIQUIDADO+APROBADO sí listan)."""
from __future__ import annotations

from collections import Counter

from app.utils.cedula_almacenamiento import texto_cedula_comparable_bd


def _claves_duplicadas_aprobados(
    filas: list[tuple[str, str]],
    *,
    min_aprobados: int = 2,
) -> set[str]:
    """Espejo en Python de claves_cedula_con_n_aprobados_en_cartera."""
    c = Counter(
        texto_cedula_comparable_bd(ced)
        for ced, est in filas
        if (ced or "").strip() and (est or "").strip().upper() == "APROBADO"
    )
    return {k for k, n in c.items() if k and n >= min_aprobados}


def test_dos_aprobados_misma_cedula_oculta():
    dup = _claves_duplicadas_aprobados(
        [
            ("V21450147", "APROBADO"),
            ("V21450147", "APROBADO"),
            ("V99999999", "APROBADO"),
        ],
    )
    assert dup == {"V21450147"}


def test_liquidado_mas_aprobado_no_oculta():
    """Renovación típica: pagó el primero (LIQUIDADO) y tiene uno APROBADO."""
    dup = _claves_duplicadas_aprobados(
        [
            ("V19530552", "LIQUIDADO"),
            ("V19530552", "APROBADO"),
        ],
    )
    assert dup == set()


def test_un_solo_aprobado_no_oculta():
    dup = _claves_duplicadas_aprobados([("V15276832", "APROBADO")])
    assert dup == set()
