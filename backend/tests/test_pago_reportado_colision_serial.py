"""Colisión cartera: mismo serial (sufijo admin), no Hamming de vecinos Mercantil."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.cobros.pago_reportado_documento import (
    _pago_ids_mismo_serial_sufijo_admin,
    pago_reportado_colisiona_tabla_pagos,
    serial_comprobante_canonico_colision,
)


def test_mismo_serial_acepta_sufijo_p_y_cd():
    db = MagicMock()
    db.execute.return_value.all.return_value = [
        (82092, "740087400015996_P7321", None, "740087400015996_P7321"),
    ]
    ids = _pago_ids_mismo_serial_sufijo_admin(db, "740087400015996")
    assert ids == [82092]


def test_mismo_serial_ignora_hamming_en_referencia_pago():
    """Vecino anotado en referencia_pago no es el voucher del estado de cuenta."""
    db = MagicMock()
    db.execute.return_value.all.return_value = [
        (81820, "740087459864184", "740087405194849 §CD:A2450", "740087459864184"),
    ]
    ids = _pago_ids_mismo_serial_sufijo_admin(db, "740087405194849")
    assert ids == []


def test_mismo_serial_otro_cliente_no_cierra():
    db = MagicMock()
    db.execute.return_value.all.return_value = [
        (33313, "740087401551920", "740087401551920", "740087401551920", "V19657168"),
    ]
    ids = _pago_ids_mismo_serial_sufijo_admin(
        db, "740087401551920_P1827", cedula_clave="V8769109"
    )
    assert ids == []


def test_mismo_serial_mismo_cliente_con_cd_cierra():
    db = MagicMock()
    db.execute.return_value.all.return_value = [
        (
            78072,
            "740087400811596 §CD:P78072",
            "740087400811596 §CD:P78072",
            "740087400811596 §CD:P78072",
            "V15369394",
        ),
    ]
    ids = _pago_ids_mismo_serial_sufijo_admin(
        db, "740087400811596_A5805", cedula_clave="V15369394"
    )
    assert ids == [78072]


def test_mismo_serial_rechaza_vecino_hamming_1():
    db = MagicMock()
    db.execute.return_value.all.return_value = [
        (33784, "740087401913897", None, "740087401913897"),
    ]
    ids = _pago_ids_mismo_serial_sufijo_admin(db, "740087401913898")
    assert ids == []
    assert serial_comprobante_canonico_colision("740087401913898") != (
        serial_comprobante_canonico_colision("740087401913897")
    )


def test_colisiona_false_sin_serial_banco_no_cierra_por_rpc():
    db = MagicMock()
    pr = SimpleNamespace(
        numero_operacion="",
        referencia_interna="RPC-20260807-00091",
    )
    assert pago_reportado_colisiona_tabla_pagos(db, pr) is False
    db.execute.assert_not_called()


def test_colisiona_false_si_pago_sin_cuota_pagos():
    db = MagicMock()
    pr = SimpleNamespace(
        numero_operacion="445857312501006336",
        referencia_interna="RPC-20260730-00111",
    )
    db.execute.return_value.all.return_value = []
    db.execute.return_value.first.return_value = None
    with patch(
        "app.services.cobros.pago_reportado_documento._pago_ids_exactos_por_claves",
        return_value=[86456],
    ), patch(
        "app.services.cobros.pago_reportado_documento._pago_cierra_reportado_como_importado",
        return_value=False,
    ):
        assert pago_reportado_colisiona_tabla_pagos(db, pr) is False


def test_colisiona_true_solo_si_cuotas_aplicadas():
    db = MagicMock()
    pr = SimpleNamespace(
        numero_operacion="448005949411418112",
        referencia_interna="RPC-20260813-00110",
    )
    with patch(
        "app.services.cobros.pago_reportado_documento._pago_ids_exactos_por_claves",
        return_value=[89974],
    ), patch(
        "app.services.cobros.pago_reportado_documento._pago_ids_mismo_serial_sufijo_admin",
        return_value=[],
    ), patch(
        "app.services.cobros.pago_reportado_documento._pago_cierra_reportado_como_importado",
        return_value=True,
    ):
        assert pago_reportado_colisiona_tabla_pagos(db, pr) is True
