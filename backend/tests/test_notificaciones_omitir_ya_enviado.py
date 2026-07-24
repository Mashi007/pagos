# -*- coding: utf-8 -*-
"""Deduplicación de envíos del día: por préstamo, no por cédula cuando hay prestamo_id."""
from app.services.notificaciones_envio_dedupe import (
    debe_omitir_ya_enviado,
    registrar_envio_exito_en_sets,
)


def test_segundo_prestamo_misma_cedula_no_se_omite():
    ya_pid = {"dias_1_retraso": {100}}
    ya_ced = {"dias_1_retraso": {"V-123"}}
    assert (
        debe_omitir_ya_enviado(
            prestamo_id=100,
            cedula="V-123",
            tipo_tab="dias_1_retraso",
            ya_pid=ya_pid,
            ya_ced=ya_ced,
        )
        is True
    )
    # Mismo titular, otro préstamo: debe enviarse.
    assert (
        debe_omitir_ya_enviado(
            prestamo_id=200,
            cedula="V-123",
            tipo_tab="dias_1_retraso",
            ya_pid=ya_pid,
            ya_ced=ya_ced,
        )
        is False
    )


def test_masivos_sin_prestamo_omite_por_cedula():
    ya_pid = {"masivos": set()}
    ya_ced = {"masivos": {"V-999"}}
    assert (
        debe_omitir_ya_enviado(
            prestamo_id=None,
            cedula="V-999",
            tipo_tab="masivos",
            ya_pid=ya_pid,
            ya_ced=ya_ced,
        )
        is True
    )
    assert (
        debe_omitir_ya_enviado(
            prestamo_id=None,
            cedula="V-111",
            tipo_tab="masivos",
            ya_pid=ya_pid,
            ya_ced=ya_ced,
        )
        is False
    )


def test_registrar_exito_con_prestamo_no_bloquea_otra_cedula_loan():
    ya_pid: dict[str, set[int]] = {}
    ya_ced: dict[str, set[str]] = {}
    registrar_envio_exito_en_sets(
        prestamo_id=10,
        cedula="V-1",
        tipo_tab="prejudicial",
        ya_pid=ya_pid,
        ya_ced=ya_ced,
    )
    assert ya_pid["prejudicial"] == {10}
    assert ya_ced.get("prejudicial", set()) == set()
    assert (
        debe_omitir_ya_enviado(
            prestamo_id=20,
            cedula="V-1",
            tipo_tab="prejudicial",
            ya_pid=ya_pid,
            ya_ced=ya_ced,
        )
        is False
    )


def test_registrar_exito_masivos_usa_cedula():
    ya_pid: dict[str, set[int]] = {}
    ya_ced: dict[str, set[str]] = {}
    registrar_envio_exito_en_sets(
        prestamo_id=None,
        cedula="V-55",
        tipo_tab="masivos",
        ya_pid=ya_pid,
        ya_ced=ya_ced,
    )
    assert ya_ced["masivos"] == {"V-55"}
    assert ya_pid.get("masivos", set()) == set()
