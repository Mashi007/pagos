"""Reserva de comprobantes antes de Conciliar cartera (revisión manual)."""

from __future__ import annotations

from types import SimpleNamespace

from app.services.revision_manual_conciliacion_cartera_service import (
    _FuenteComprobanteConciliar,
    _reservar_comprobantes_prestamo,
    purgar_reserva_conciliacion_prestamo,
)


class _FakeDb:
    def __init__(
        self,
        *,
        pagos: list[object] | None = None,
        reservas: list[object] | None = None,
    ) -> None:
        self.pagos = pagos or []
        self.reservas = reservas or []
        self.added: list[object] = []
        self.deleted: list[object] = []

    def flush(self) -> None:
        return None

    def add(self, row: object) -> None:
        self.added.append(row)

    def delete(self, row: object) -> None:
        self.deleted.append(row)

    def execute(self, _stmt):
        sql = str(_stmt)
        rows = self.reservas if "revision_manual_conciliacion_reserva" in sql else self.pagos
        return type(
            "R",
            (),
            {"scalars": lambda s: type("S", (), {"all": lambda s2: list(rows)})()},
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


def test_purgar_preserva_reservas_con_imagen_para_reintento() -> None:
    reserva_retry = SimpleNamespace(id=1, prestamo_id=99, comprobante_imagen_data=b"jpeg")
    reserva_vacia = SimpleNamespace(id=2, prestamo_id=99, comprobante_imagen_data=b"")
    reserva_sin_data = SimpleNamespace(id=3, prestamo_id=99, comprobante_imagen_data=None)
    db = _FakeDb(reservas=[reserva_retry, reserva_vacia, reserva_sin_data])

    borradas = purgar_reserva_conciliacion_prestamo(
        db, 99, conservar_con_imagen=True
    )

    assert borradas == 2
    assert reserva_retry not in db.deleted
    assert reserva_vacia in db.deleted
    assert reserva_sin_data in db.deleted


def test_reservar_no_duplica_reserva_preservada_con_misma_imagen(monkeypatch) -> None:
    prestamo = SimpleNamespace(id=99, cedula="V12345678")
    reserva_retry = SimpleNamespace(
        id=1,
        prestamo_id=99,
        orden=1,
        comprobante_imagen_data=b"jpeg",
    )
    fuente = _FuenteComprobanteConciliar(
        fuente="pago",
        fuente_id=1,
        link_comprobante="https://x/api/v1/pagos/comprobante-imagen/" + "c" * 32,
        documento_ruta=None,
        referencia="DOC1",
        cedula_cliente="V12345678",
    )

    monkeypatch.setattr(
        "app.services.revision_manual_conciliacion_cartera_service._iter_fuentes_comprobante_conciliar_revision",
        lambda _db, _prestamo: [fuente],
    )
    monkeypatch.setattr(
        "app.services.revision_manual_conciliacion_cartera_service._evaluar_fuentes_comprobante_reserva",
        lambda _db, _fuentes: ([(fuente, b"jpeg", "c.jpg")], []),
    )

    db = _FakeDb(reservas=[reserva_retry])
    out = _reservar_comprobantes_prestamo(db, prestamo)  # type: ignore[arg-type]

    assert out["ok"] is True
    assert out.get("reservas") == 1
    assert out.get("reservas_preservadas") == 1
    assert out.get("reservas_nuevas") == 0
    assert db.added == []
