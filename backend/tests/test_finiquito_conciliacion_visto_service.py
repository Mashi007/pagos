from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from app.models.finiquito import FiniquitoCaso
from app.models.finiquito_conciliacion_reserva import FiniquitoConciliacionReserva
from app.models.pago import Pago
from app.services import finiquito_conciliacion_visto_service as service


class DummyDb:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.flushed = False

    def get(self, *_args: object, **_kwargs: object) -> None:
        return None

    def add(self, obj: object) -> None:
        self.added.append(obj)
        setattr(obj, "id", 77)

    def flush(self) -> None:
        self.flushed = True


def test_crear_pago_desde_reserva_compone_numero_documento(monkeypatch) -> None:
    monkeypatch.setattr(
        service,
        "asegurar_cedula_pago_para_fk",
        lambda _db, cedula_raw, _prestamo_id=None, **_kwargs: cedula_raw,
    )
    monkeypatch.setattr(
        service,
        "resolver_monto_registro_pago",
        lambda _db, **kwargs: (kwargs["monto_pagado"], "USD", None, None, None),
    )
    monkeypatch.setattr(service, "conflicto_huella_para_creacion", lambda *_args, **_kwargs: None)

    db = DummyDb()
    reserva = FiniquitoConciliacionReserva(
        id=10,
        caso_id=1,
        prestamo_id=5,
        orden=1,
        cedula_cliente="V123",
        monto_pagado=Decimal("20.50"),
        fecha_pago=datetime(2026, 1, 5, 14, 30),
        numero_documento="  ABC   123  ",
        referencia_pago="",
        institucion_bancaria="Banco",
        conciliado=True,
        moneda_registro="USD",
    )
    caso = FiniquitoCaso(id=1, prestamo_id=5, cedula="V123")

    pago, err = service._crear_o_actualizar_pago_desde_reserva(db, reserva, caso, "tester")

    assert err is None
    assert pago is db.added[0]
    assert pago.numero_documento == "ABC 123"
    assert pago.referencia_pago == "ABC 123"
    assert reserva.pago_id_recriado == 77
    assert db.flushed is True


def test_aplicar_ocr_a_pago_compone_numero_documento() -> None:
    pago = Pago(
        fecha_pago=datetime(2026, 1, 1),
        monto_pagado=Decimal("1.00"),
        referencia_pago="old",
    )

    service._aplicar_ocr_a_pago(
        DummyDb(),
        pago,
        {
            "ok": True,
            "institucion_financiera": "Banco OCR",
            "numero_operacion": "  9988  ",
            "fecha_pago": date(2026, 1, 2),
            "monto": "15.239",
        },
    )

    assert pago.numero_documento == "9988"
    assert pago.referencia_pago == "9988"
    assert pago.institucion_bancaria == "Banco OCR"
    assert pago.fecha_pago == datetime(2026, 1, 2)
    assert pago.monto_pagado == Decimal("15.24")
