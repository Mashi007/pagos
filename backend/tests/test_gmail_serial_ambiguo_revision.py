"""Serial Hamming-1 / truncado → revisión manual (regla Cobros, alta Gmail)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.pagos_gmail.parse_campos_comprobante import (
    numeros_operacion_coinciden_o_evasion,
    seriales_banco_ambiguos_para_revision,
)
from app.services.pagos_gmail.plantilla_abcd_proceso_negocio import (
    PAGOS_GMAIL_MOTIVO_SERIAL_AMBIGUO,
    item_sync_candidato_revision_serial_ambiguo,
)


def test_caso_captura_mercantil_hamming_1_es_ambiguo_no_mismo_voucher():
    a = "740087499132585"
    b = "740087489132585"
    assert seriales_banco_ambiguos_para_revision(a, b)
    # Pipeline vigente: no son el mismo documento canónico → no OMITIDO_DUPLICADO.
    assert not numeros_operacion_coinciden_o_evasion(a, b, monto_a=180, monto_b=180)


def test_item_sync_serial_ambiguo_contra_lote_previo():
    db = MagicMock()
    assert item_sync_candidato_revision_serial_ambiguo(
        referencia="740087489132585",
        db=db,
        lote_previo=[
            {"r": "740087499132585", "m": "180", "c": "V1", "f": "2026-06-10"}
        ],
    )


def test_item_sync_serial_ambiguo_contra_cartera():
    db = MagicMock()
    with patch(
        "app.services.pagos_gmail.plantilla_abcd_proceso_negocio.referencia_serial_ambiguo_para_revision",
        return_value=True,
    ) as m:
        assert item_sync_candidato_revision_serial_ambiguo(
            referencia="740087489132585",
            db=db,
            lote_previo=[],
        )
        m.assert_called_once()


def test_item_sync_sin_ambiguo():
    db = MagicMock()
    with patch(
        "app.services.pagos_gmail.plantilla_abcd_proceso_negocio.referencia_serial_ambiguo_para_revision",
        return_value=False,
    ):
        assert not item_sync_candidato_revision_serial_ambiguo(
            referencia="740087489132585",
            db=db,
            lote_previo=[{"r": "999999999999999"}],
        )


def test_motivo_constante_estable():
    assert PAGOS_GMAIL_MOTIVO_SERIAL_AMBIGUO == "serial_ambiguo_revision_manual"
