# -*- coding: utf-8 -*-
"""Serial único solo en pagos operativos; al borrar/editar se libera."""

from app.models.pago import pago_estado_ocupa_serial
from app.services.pago_numero_documento import (
    liberar_serial_tras_baja_o_cambio,
    numero_documento_ya_registrado,
    serial_revision_apto_para_cartera,
)


class _FakeDb:
    def scalar(self, _q):
        return None

    def execute(self, _q, *a, **k):
        class _R:
            rowcount = 0

            def all(self):
                return []

            def first(self):
                return None

        return _R()

    def flush(self):
        return None


def test_estados_inactivos_no_ocupan_serial():
    assert pago_estado_ocupa_serial("PAGADO") is True
    assert pago_estado_ocupa_serial("PENDIENTE") is True
    assert pago_estado_ocupa_serial(None) is True
    assert pago_estado_ocupa_serial("ANULADO_IMPORT") is False
    assert pago_estado_ocupa_serial("ANULADO") is False
    assert pago_estado_ocupa_serial("DUPLICADO") is False
    assert pago_estado_ocupa_serial("REVERSADO") is False


def test_ya_registrado_sin_filas_operativas_permite_reingreso(monkeypatch):
    monkeypatch.setattr(
        "app.services.pago_numero_documento.documento_colisiona_evasion_registrado",
        lambda *_a, **_k: False,
    )
    assert numero_documento_ya_registrado(_FakeDb(), "740087401373233") is False


def test_serial_revision_apto_para_cartera():
    assert serial_revision_apto_para_cartera("740087401373233") is True
    assert serial_revision_apto_para_cartera("  740087401373233  ") is True
    assert serial_revision_apto_para_cartera(None) is False
    assert serial_revision_apto_para_cartera("") is False
    assert serial_revision_apto_para_cartera("   ") is False


def test_liberar_serial_no_borra_pagos_con_errores():
    """Tras borrar/anular, la fila de revisión debe seguir ocupando el serial."""
    executed = []

    class _RecDb(_FakeDb):
        def execute(self, q, *a, **k):
            executed.append(str(q))
            return super().execute(q, *a, **k)

        def scalar(self, q):
            executed.append(f"scalar:{q}")
            return None

    n = liberar_serial_tras_baja_o_cambio(
        _RecDb(),
        "740087401373233",
        incluir_pagos_con_errores=True,
    )
    joined = " ".join(executed).lower()
    assert n == 0
    assert "pagos_con_errores" not in joined
    assert "pago_con_error" not in joined


def test_liberar_serial_anulado_deja_libre_en_cartera():
    from datetime import datetime
    from decimal import Decimal

    import pytest
    from sqlalchemy import create_engine, func, select, update
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON

    from app.models.pago import Pago
    from app.models.pago_con_error import PagoConError

    pytest.importorskip("sqlalchemy")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    col_pe = PagoConError.__table__.c.errores_descripcion
    tipo_orig = col_pe.type
    col_pe.type = SQLITE_JSON()
    Pago.__table__.create(bind=engine, checkfirst=True)
    PagoConError.__table__.create(bind=engine, checkfirst=True)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        db.add(
            Pago(
                cedula_cliente="V1",
                prestamo_id=1,
                fecha_pago=datetime(2026, 9, 1),
                monto_pagado=Decimal("10.00"),
                numero_documento="740087401373233",
                institucion_bancaria="MERCANTIL",
                estado="PAGADO",
                referencia_pago="740087401373233",
                usuario_registro="test",
            )
        )
        db.add(
            PagoConError(
                cedula_cliente="V1",
                prestamo_id=1,
                fecha_pago=datetime(2026, 9, 1),
                monto_pagado=Decimal("10.00"),
                numero_documento="740087401373233",
                institucion_bancaria="MERCANTIL",
                estado="PENDIENTE",
                referencia_pago="740087401373233",
            )
        )
        db.commit()
        db.execute(
            update(Pago).values(estado="ANULADO")
        )
        db.commit()
        n = liberar_serial_tras_baja_o_cambio(db, "740087401373233")
        db.commit()
        assert n >= 1
        pago_serial = db.scalar(select(Pago.numero_documento).limit(1))
        pe_serial = db.scalar(select(PagoConError.numero_documento).limit(1))
        assert pago_serial is None
        assert pe_serial == "740087401373233"
        assert (
            db.scalar(
                select(func.count()).select_from(PagoConError).where(
                    PagoConError.numero_documento == "740087401373233"
                )
            )
            == 1
        )
    finally:
        db.close()
        col_pe.type = tipo_orig
