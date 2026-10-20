# -*- coding: utf-8 -*-
"""Catch-up huérfanos APROBADO: lock y forma del resultado."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.pagos_huerfanos_catchup_job import ejecutar_catchup_huerfanos_aprobado


def test_catchup_omitido_si_no_hay_lock():
    db = MagicMock()
    db.execute.return_value.scalar.return_value = False
    out = ejecutar_catchup_huerfanos_aprobado(db, limit=10, usar_lock=True)
    assert out["omitido_por_lock"] is True
    assert out["candidatos"] == 0


def test_catchup_sin_candidatos():
    db = MagicMock()

    def _exec(stmt, params=None):
        m = MagicMock()
        sql = str(stmt)
        if "pg_try_advisory_lock" in sql:
            m.scalar.return_value = True
        elif "pg_advisory_unlock" in sql:
            m.scalar.return_value = True
        else:
            m.fetchall.return_value = []
        return m

    db.execute.side_effect = _exec
    with patch(
        "app.services.pagos_huerfanos_catchup_job.listar_prestamo_ids_huerfanos_aprobado",
        return_value=[],
    ):
        out = ejecutar_catchup_huerfanos_aprobado(db, limit=10, usar_lock=True)
    assert out["omitido_por_lock"] is False
    assert out["candidatos"] == 0
    assert out["ok_incremental"] == 0
    assert out["ok_cascada"] == 0
    assert out["errores"] == 0
