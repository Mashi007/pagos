from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.pagos_gmail.pago_abcd_auto_service import (
    crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_abcd,
)
from app.services.pagos_gmail.pago_nr_auto_service import (
    crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_nr,
)


class _DummyScalars:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class _DummyExecResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return _DummyScalars(self._values)


class _DummyDB:
    def __init__(self):
        self._prestamo = SimpleNamespace(id=101, cliente_id=7, cedula="V12345678")
        self._cliente = SimpleNamespace(id=7, cedula="V12345678")
        self.added = []
        self.rollback_calls = 0
        self.commit_calls = 0

    def execute(self, _query):
        return _DummyExecResult([101])

    def get(self, model, model_id):
        name = getattr(model, "__name__", "")
        if name == "Prestamo" and int(model_id) == 101:
            return self._prestamo
        if name == "Cliente" and int(model_id) == 7:
            return self._cliente
        return None

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        for obj in self.added:
            if hasattr(obj, "id") and getattr(obj, "id", None) is None:
                setattr(obj, "id", 9001)

    def rollback(self):
        self.rollback_calls += 1

    def commit(self):
        self.commit_calls += 1


@pytest.fixture
def patched_abcd(monkeypatch):
    import app.services.pagos_gmail.pago_abcd_auto_service as mod

    monkeypatch.setattr(
        "app.services.pago_huella_funcional.conflicto_huella_para_creacion",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "app.services.pago_huella_metricas.registrar_rechazo_huella_funcional",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(mod, "numero_documento_ya_registrado", lambda *_a, **_k: False)
    monkeypatch.setattr(
        mod,
        "resolver_monto_registro_pago",
        lambda *_a, **_k: (
            Decimal("96.00"),
            "USD",
            Decimal("0.00"),
            Decimal("0.00"),
            date(2026, 1, 1),
        ),
    )
    return mod


@pytest.fixture
def patched_nr(monkeypatch):
    import app.services.pagos_gmail.pago_nr_auto_service as mod

    monkeypatch.setattr(
        "app.services.pago_huella_funcional.conflicto_huella_para_creacion",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "app.services.pago_huella_metricas.registrar_rechazo_huella_funcional",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(mod, "numero_documento_ya_registrado", lambda *_a, **_k: False)
    monkeypatch.setattr(
        mod,
        "resolver_monto_registro_pago",
        lambda *_a, **_k: (
            Decimal("122.00"),
            "USD",
            Decimal("0.00"),
            Decimal("0.00"),
            date(2026, 1, 1),
        ),
    )
    return mod


def test_abcd_exige_validadores_autoconciliacion_y_cuotas(patched_abcd, monkeypatch):
    db = _DummyDB()
    monkeypatch.setattr(
        "app.api.v1.endpoints.pagos._aplicar_pago_a_cuotas_interno",
        lambda *_a, **_k: (1, 0),
    )

    def _estado_ok(pago, _cc, _cp):
        pago.conciliado = True

    monkeypatch.setattr(
        "app.api.v1.endpoints.pagos._estado_conciliacion_post_cascada", _estado_ok
    )
    monkeypatch.setattr(patched_abcd, "validar_suma_aplicada_vs_monto_pago", lambda *_a, **_k: None)
    monkeypatch.setattr(patched_abcd, "pago_tiene_aplicaciones_cuotas", lambda *_a, **_k: True)

    out = crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_abcd(
        db,
        cedula_columna="V12345678",
        fecha_pago_str="01/01/2026",
        monto_str="96.00",
        numero_referencia="REF-ABCD-1",
        institucion_bancaria="Mercantil",
        link_comprobante="https://example.com/c.png",
        fmt="A",
    )

    assert out["ok"] is True
    assert out["etapa_final"] == "CUOTAS_OK"
    assert db.commit_calls >= 1
    assert db.rollback_calls == 0


def test_abcd_falla_si_no_queda_aplicado_a_cuotas(patched_abcd, monkeypatch):
    db = _DummyDB()
    monkeypatch.setattr(
        "app.api.v1.endpoints.pagos._aplicar_pago_a_cuotas_interno",
        lambda *_a, **_k: (0, 0),
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.pagos._estado_conciliacion_post_cascada",
        lambda pago, _cc, _cp: setattr(pago, "conciliado", True),
    )
    monkeypatch.setattr(patched_abcd, "validar_suma_aplicada_vs_monto_pago", lambda *_a, **_k: None)
    monkeypatch.setattr(patched_abcd, "pago_tiene_aplicaciones_cuotas", lambda *_a, **_k: False)

    out = crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_abcd(
        db,
        cedula_columna="V12345678",
        fecha_pago_str="01/01/2026",
        monto_str="96.00",
        numero_referencia="REF-ABCD-2",
        institucion_bancaria="Mercantil",
        link_comprobante="https://example.com/c.png",
        fmt="B",
    )

    assert out["ok"] is False
    assert out["motivo"] == "sin_cuotas_aplicadas"
    assert db.rollback_calls >= 1


def test_nr_exige_validadores_autoconciliacion_y_cuotas(patched_nr, monkeypatch):
    db = _DummyDB()
    monkeypatch.setattr(
        "app.api.v1.endpoints.pagos._aplicar_pago_a_cuotas_interno",
        lambda *_a, **_k: (0, 1),
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.pagos._estado_conciliacion_post_cascada",
        lambda pago, _cc, _cp: setattr(pago, "conciliado", True),
    )
    monkeypatch.setattr(patched_nr, "validar_suma_aplicada_vs_monto_pago", lambda *_a, **_k: None)
    monkeypatch.setattr(patched_nr, "pago_tiene_aplicaciones_cuotas", lambda *_a, **_k: True)

    out = crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_nr(
        db,
        cedula_columna="V12345678",
        fecha_pago_str="01/01/2026",
        monto_operacion_str="122.00",
        numero_referencia="REF-NR-1",
        institucion_bancaria="BINANCE",
        link_comprobante="https://example.com/c.png",
    )

    assert out["ok"] is True
    assert out["etapa_final"] == "CUOTAS_OK"
    assert db.commit_calls >= 1
    assert db.rollback_calls == 0


def test_nr_falla_si_no_queda_aplicado_a_cuotas(patched_nr, monkeypatch):
    db = _DummyDB()
    monkeypatch.setattr(
        "app.api.v1.endpoints.pagos._aplicar_pago_a_cuotas_interno",
        lambda *_a, **_k: (0, 0),
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.pagos._estado_conciliacion_post_cascada",
        lambda pago, _cc, _cp: setattr(pago, "conciliado", True),
    )
    monkeypatch.setattr(patched_nr, "validar_suma_aplicada_vs_monto_pago", lambda *_a, **_k: None)
    monkeypatch.setattr(patched_nr, "pago_tiene_aplicaciones_cuotas", lambda *_a, **_k: False)

    out = crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_nr(
        db,
        cedula_columna="V12345678",
        fecha_pago_str="01/01/2026",
        monto_operacion_str="122.00",
        numero_referencia="REF-NR-2",
        institucion_bancaria="BINANCE",
        link_comprobante="https://example.com/c.png",
    )

    assert out["ok"] is False
    assert out["motivo"] == "sin_cuotas_aplicadas"
    assert db.rollback_calls >= 1
