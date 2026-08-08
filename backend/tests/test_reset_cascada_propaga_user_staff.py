"""
Regresión: reset_y_reaplicar debe propagar user al reaplicar.

Sin user en aplicar_pagos_pendientes_prestamo, un préstamo LIQUIDADO/DESISTIMIENTO
pasa el gate staff, borra cuota_pagos, y la reaplicación queda bloqueada → ledger en 0.
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock

import app.services.pagos_cuotas_reaplicacion as reapl


class _Staff:
    rol = "operator"


def test_reset_cascada_pasa_user_a_aplicar_pendientes(monkeypatch):
    captured: dict = {}

    prestamo = SimpleNamespace(id=42, estado="LIQUIDADO")
    cuota = SimpleNamespace(
        id=1,
        prestamo_id=42,
        numero_cuota=1,
        total_pagado=None,
        fecha_pago=None,
        pago_id=None,
        dias_mora=None,
        monto=100,
        estado="PENDIENTE",
    )

    db = MagicMock()
    db.get.return_value = prestamo
    db.scalar.return_value = 0

    exec_result = MagicMock()
    exec_result.scalars.return_value.all.return_value = [cuota]
    exec_result.rowcount = 1
    db.execute.return_value = exec_result

    monkeypatch.setattr(
        "app.services.pagos_cascada_lock.adquirir_lock_cascada_prestamo",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "app.services.pagos_desistimiento_politica.prestamo_bloquea_aplicacion_a_cuotas",
        lambda *_a, **_k: False,
    )
    monkeypatch.setattr(
        "app.services.pago_huella_funcional.primer_par_huella_duplicada_prestamo",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(reapl, "_delete_cuota_pagos_por_prestamo_sql", lambda *_a, **_k: 3)
    monkeypatch.setattr(reapl, "sincronizar_columna_estado_cuotas", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "app.services.pagos_cascada_aplicacion._marcar_prestamo_liquidado_si_corresponde",
        lambda *_a, **_k: None,
    )

    def _fake_aplicar(prestamo_id, db, **kwargs):
        captured["prestamo_id"] = prestamo_id
        captured["kwargs"] = kwargs
        return 2

    monkeypatch.setattr(
        "app.services.pagos_aplicacion_prestamo.aplicar_pagos_pendientes_prestamo",
        _fake_aplicar,
    )

    out = reapl._reset_y_reaplicar_cascada_prestamo_once(db, 42, user=_Staff())

    assert out.get("ok") is True, out
    assert captured.get("prestamo_id") == 42
    assert "user" in captured.get("kwargs", {})
    assert getattr(captured["kwargs"]["user"], "rol", None) == "operator"


def test_reset_cascada_source_propaga_user():
    src = inspect.getsource(reapl._reset_y_reaplicar_cascada_prestamo_once)
    assert "aplicar_pagos_pendientes_prestamo(" in src
    assert "user=user" in src


def test_forzar_eliminar_requiere_admin():
    """Privilege: forzar-eliminar must stay admin-only (not operator_or_higher)."""
    from app.api.v1.endpoints.pagos import crud_pagos_aplicacion_routes as mod
    from app.core.deps import require_admin

    sig = inspect.signature(mod.forzar_eliminar_pago)
    dep = sig.parameters["current_user"].default
    assert getattr(dep, "dependency", None) is require_admin
