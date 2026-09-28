# -*- coding: utf-8 -*-
"""Filtro listado: cupo excedido V/E (2+ APROBADO); J con N APROBADO sí listan."""
from __future__ import annotations

from collections import Counter

from app.utils.cedula_almacenamiento import (
    max_aprobados_permitidos_por_prefijo,
    prefijo_politica_cupo_aprobados,
    texto_cedula_comparable_bd,
)


def _claves_cupo_excedido_aprobados(filas: list[tuple[str, str]]) -> set[str]:
    """Espejo en Python de claves_cedula_cupo_aprobado_excedido_en_cartera."""
    c = Counter(
        texto_cedula_comparable_bd(ced)
        for ced, est in filas
        if (ced or "").strip() and (est or "").strip().upper() == "APROBADO"
    )
    out: set[str] = set()
    for clave, n in c.items():
        if not clave:
            continue
        pref = prefijo_politica_cupo_aprobados(clave)
        max_n = max_aprobados_permitidos_por_prefijo(pref)
        if max_n is not None and n > max_n:
            out.add(clave)
    return out


def test_dos_aprobados_v_misma_cedula_oculta():
    dup = _claves_cupo_excedido_aprobados(
        [
            ("V21450147", "APROBADO"),
            ("V21450147", "APROBADO"),
            ("V99999999", "APROBADO"),
        ],
    )
    assert dup == {"V21450147"}


def test_tres_aprobados_j_no_oculta():
    """Jurídico: varios APROBADO legítimos (p. ej. J503848898)."""
    dup = _claves_cupo_excedido_aprobados(
        [
            ("J503848898", "APROBADO"),
            ("J503848898", "APROBADO"),
            ("J503848898", "APROBADO"),
        ],
    )
    assert dup == set()


def test_liquidado_mas_aprobado_no_oculta():
    """Renovación típica: pagó el primero (LIQUIDADO) y tiene uno APROBADO."""
    dup = _claves_cupo_excedido_aprobados(
        [
            ("V19530552", "LIQUIDADO"),
            ("V19530552", "APROBADO"),
        ],
    )
    assert dup == set()


def test_un_solo_aprobado_no_oculta():
    dup = _claves_cupo_excedido_aprobados([("V15276832", "APROBADO")])
    assert dup == set()


def test_claves_cupo_excedido_cache_evita_segundo_scan():
    import pytest
    from unittest.mock import MagicMock

    try:
        from app.services.prestamos import cupo_cedula_aprobados as cupo
    except ImportError as e:
        pytest.skip(f"deps incompletas: {e}")

    cupo.invalidate_claves_cedula_cupo_aprobado_excedido()
    db = MagicMock()
    exec1 = MagicMock()
    exec1.all.return_value = [("V11111111",)]
    db.execute.return_value = exec1
    a = cupo.claves_cedula_cupo_aprobado_excedido_en_cartera(db)
    b = cupo.claves_cedula_cupo_aprobado_excedido_en_cartera(db)
    assert a == {"V11111111"}
    assert b == {"V11111111"}
    assert db.execute.call_count == 1
    cupo.invalidate_claves_cedula_cupo_aprobado_excedido()
    cupo.claves_cedula_cupo_aprobado_excedido_en_cartera(db)
    assert db.execute.call_count == 2
