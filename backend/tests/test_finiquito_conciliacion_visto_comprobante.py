"""Vinculación de comprobante reserva Visto → pago_comprobante_imagen al recrear pagos."""

from __future__ import annotations

from types import SimpleNamespace

from app.services.finiquito_conciliacion_visto_service import (
    _extraer_comprobante_id_hex,
    _vincular_comprobante_reserva_al_pago,
)


class _FakeDb:
    def __init__(self, rows: dict[str, object]) -> None:
        self._rows = rows
        self.added: list[object] = []

    def get(self, _model, pk: str) -> object | None:
        return self._rows.get(str(pk))

    def flush(self) -> None:
        return None

    def add(self, row: object) -> None:
        self.added.append(row)


def test_extraer_comprobante_id_hex_desde_url_absoluta() -> None:
    cid = "a" * 32
    url = f"https://api.example.com/api/v1/pagos/comprobante-imagen/{cid}?t=1"
    assert _extraer_comprobante_id_hex(url, None) == cid


def test_vincular_reutiliza_imagen_bd_existente() -> None:
    cid = "b" * 32
    pago = SimpleNamespace(
        link_comprobante=f"/api/v1/pagos/comprobante-imagen/{cid}",
        documento_ruta=None,
    )
    reserva = SimpleNamespace(
        id=1,
        link_comprobante=None,
        documento_ruta=None,
        comprobante_imagen_data=b"jpeg-bytes",
        comprobante_content_type="image/jpeg",
    )
    db = _FakeDb({cid: SimpleNamespace(imagen_data=b"stored")})
    _vincular_comprobante_reserva_al_pago(db, reserva, pago)
    assert f"/api/v1/pagos/comprobante-imagen/{cid}" in (pago.link_comprobante or "")
    assert pago.documento_ruta is None
    assert db.added == []


def test_vincular_inserta_nueva_imagen_si_link_es_drive() -> None:
    pago = SimpleNamespace(
        link_comprobante="https://drive.google.com/file/d/abc123/view",
        documento_ruta=None,
    )
    reserva = SimpleNamespace(
        id=2,
        link_comprobante=pago.link_comprobante,
        documento_ruta=None,
        comprobante_imagen_data=b"\xff\xd8\xff\xd9",
        comprobante_content_type="image/jpeg",
    )
    db = _FakeDb({})
    _vincular_comprobante_reserva_al_pago(db, reserva, pago)
    assert len(db.added) == 1
    assert "comprobante-imagen" in (pago.link_comprobante or "")
    assert pago.documento_ruta is None
