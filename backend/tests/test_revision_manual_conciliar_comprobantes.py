"""Reserva de comprobantes antes de Conciliar cartera (revisión manual)."""

from __future__ import annotations

from types import SimpleNamespace

from app.services.revision_manual_conciliacion_cartera_service import (
    _FuenteComprobanteConciliar,
    _reservar_comprobantes_prestamo,
)


class _FakeDb:
    def __init__(self) -> None:
        self.added: list[object] = []

    def flush(self) -> None:
        return None

    def add(self, row: object) -> None:
        self.added.append(row)

    def execute(self, _stmt):
        return type(
            "R",
            (),
            {"scalars": lambda s: type("S", (), {"all": lambda s2: []})()},
        )()


def test_reservar_falla_si_hay_omitidos_sin_confirmacion(monkeypatch) -> None:
    prestamo = SimpleNamespace(id=99, cedula="V12345678")
    fuentes = [
        _FuenteComprobanteConciliar(
            fuente="pago",
            fuente_id=1,
            link_comprobante="https://x/api/v1/pagos/comprobante-imagen/" + "a" * 32,
            documento_ruta=None,
            referencia="DOC1",
            cedula_cliente="V12345678",
        ),
        _FuenteComprobanteConciliar(
            fuente="gmail_sync",
            fuente_id=2,
            link_comprobante="https://drive.google.com/file/d/roto/view",
            documento_ruta=None,
            referencia="DOC2",
            cedula_cliente="V12345678",
        ),
    ]

    def fake_eval(_db, _fuentes):
        return [(fuentes[0], b"jpeg", "c.jpg")], [{"referencia": "DOC2"}]

    monkeypatch.setattr(
        "app.services.revision_manual_conciliacion_cartera_service._iter_fuentes_comprobante_conciliar_revision",
        lambda _db, _prestamo: fuentes,
    )
    monkeypatch.setattr(
        "app.services.revision_manual_conciliacion_cartera_service._evaluar_fuentes_comprobante_reserva",
        fake_eval,
    )

    db = _FakeDb()
    out = _reservar_comprobantes_prestamo(db, prestamo)  # type: ignore[arg-type]

    assert out["ok"] is False
    assert out.get("requiere_confirmacion_comprobantes_omitidos") is True
    assert out.get("reservas") == 1
    assert len(db.added) == 1


def test_reservar_continua_si_usuario_confirma_omitidos(monkeypatch) -> None:
    prestamo = SimpleNamespace(id=99, cedula="V12345678")
    fuentes = [
        _FuenteComprobanteConciliar(
            fuente="pago",
            fuente_id=1,
            link_comprobante="https://x/api/v1/pagos/comprobante-imagen/" + "b" * 32,
            documento_ruta=None,
            referencia="DOC1",
            cedula_cliente="V12345678",
        ),
    ]

    monkeypatch.setattr(
        "app.services.revision_manual_conciliacion_cartera_service._iter_fuentes_comprobante_conciliar_revision",
        lambda _db, _p: fuentes,
    )
    monkeypatch.setattr(
        "app.services.revision_manual_conciliacion_cartera_service._evaluar_fuentes_comprobante_reserva",
        lambda _db, _f: ([(fuentes[0], b"jpeg", "c.jpg")], []),
    )

    db = _FakeDb()
    out = _reservar_comprobantes_prestamo(
        db,
        prestamo,  # type: ignore[arg-type]
        confirmar_comprobantes_omitidos=True,
    )

    assert out["ok"] is True
    assert out.get("reservas") == 1
