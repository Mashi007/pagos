"""Eliminar varios reportes de cola no toca la tabla pagos."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.cobros.eliminar_reportados_cola import (
    MAX_ELIMINAR_SELECCIONADOS,
    eliminar_pagos_reportados_seleccionados,
)


def _pr(**kwargs):
    base = dict(
        id=1,
        estado="en_revision",
        referencia_interna="RPC-20260813-00001",
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_eliminar_seleccionados_borra_cola_y_commit():
    db = MagicMock()
    a = _pr(id=10, estado="pendiente")
    b = _pr(id=11, estado="en_revision")
    db.execute.return_value.scalars.return_value.all.return_value = [a, b]
    out = eliminar_pagos_reportados_seleccionados(db, [10, 11])
    assert out["ok"] is True
    assert [x["id"] for x in out["eliminados"]] == [10, 11]
    assert db.delete.call_count == 2
    db.commit.assert_called_once()


def test_eliminar_seleccionados_importado_borra_reporte_no_toca_pagos():
    db = MagicMock()
    pr = _pr(id=12, estado="importado")
    db.execute.return_value.scalars.return_value.all.return_value = [pr]
    out = eliminar_pagos_reportados_seleccionados(db, [12])
    assert out["ok"] is True
    assert [x["id"] for x in out["eliminados"]] == [12]
    db.delete.assert_called_once()
    db.commit.assert_called_once()


def test_eliminar_seleccionados_omite_aprobado_no_toca_pagos():
    db = MagicMock()
    pr = _pr(id=12, estado="aprobado")
    db.execute.return_value.scalars.return_value.all.return_value = [pr]
    out = eliminar_pagos_reportados_seleccionados(db, [12])
    assert out["ok"] is False
    assert out["eliminados"] == []
    assert out["omitidos"][0]["motivo"] == "estado_no_eliminable"
    assert "aprobado=1" in (out["mensaje"] or "")
    db.delete.assert_not_called()
    db.commit.assert_not_called()


def test_eliminar_seleccionados_cap_max():
    db = MagicMock()
    ids = list(range(1, MAX_ELIMINAR_SELECCIONADOS + 2))
    out = eliminar_pagos_reportados_seleccionados(db, ids)
    assert out["ok"] is False
    db.execute.assert_not_called()
