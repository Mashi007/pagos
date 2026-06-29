import os
import sys
from datetime import date
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.endpoints.cobros.reportados_listado_payload import (
    _kpis_pagos_reportados_payload,
    _list_pagos_reportados_payload,
)


def test_regularizar_reportados_guarded_no_name_error():
    from app.api.v1.endpoints.cobros.reportados_validadores_helpers import (
        _regularizar_reportados_guarded,
    )

    db = MagicMock()
    _regularizar_reportados_guarded(db)


def test_listado_y_kpis_payload_armado_basico():
    """Listado + KPIs: payload mínimo sin barrido real (mocks)."""
    db = MagicMock()
    with patch(
        "app.api.v1.endpoints.cobros.reportados_listado_payload._get_primer_triple_cached",
        return_value=({}, {}, frozenset()),
    ):
        with patch(
            "app.api.v1.endpoints.cobros.reportados_listado_payload._pago_reportado_list_items_from_rows",
            return_value=[],
        ):
            db.execute.return_value.scalars.return_value.all.return_value = []
            out = _list_pagos_reportados_payload(
                db,
                estado=None,
                fecha_desde=date(2026, 3, 25),
                fecha_hasta=date(2026, 6, 23),
                cedula=None,
                institucion=None,
                page=1,
                per_page=20,
                incluir_exportados=False,
                emit_manual_estado_counts_for_kpis=True,
            )
    assert "items" in out
    assert "total" in out

    kpis = _kpis_pagos_reportados_payload(
        db,
        fecha_desde=date(2026, 3, 25),
        fecha_hasta=date(2026, 6, 23),
        cedula=None,
        institucion=None,
        incluir_exportados=False,
        manual_queue_counts={"pendiente": 0, "en_revision": 0},
    )
    assert "pendiente" in kpis
    assert "total" in kpis
