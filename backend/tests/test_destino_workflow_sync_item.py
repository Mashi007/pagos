"""destino_workflow_sync_item: Nuevo / Viejo / Revisión manual según traza pipeline."""

from app.services.pagos_gmail.destino_workflow import destino_workflow_sync_item


def test_destino_nuevo_cuotas_ok_con_pago():
    assert (
        destino_workflow_sync_item(
            etapa_final="CUOTAS_OK",
            traza_pago_id=92616,
            duplicado_en_pagos=True,
        )
        == "nuevo"
    )


def test_destino_viejo_omitido_duplicado():
    assert (
        destino_workflow_sync_item(
            etapa_final="OMITIDO_DUPLICADO",
            traza_pago_id=None,
            duplicado_en_pagos=False,
        )
        == "viejo"
    )


def test_destino_viejo_serial_en_pagos():
    assert (
        destino_workflow_sync_item(
            etapa_final=None,
            traza_pago_id=None,
            duplicado_en_pagos=True,
        )
        == "viejo"
    )


def test_destino_revision_manual_sin_cuotas():
    assert (
        destino_workflow_sync_item(
            etapa_final="PAGO_SIN_CUOTAS",
            traza_pago_id=100,
            duplicado_en_pagos=False,
        )
        == "revision_manual"
    )


def test_destino_revision_manual_omitido_negocio():
    assert (
        destino_workflow_sync_item(
            etapa_final="OMITIDO_NEGOCIO",
            traza_pago_id=None,
            duplicado_en_pagos=False,
        )
        == "revision_manual"
    )


def test_destino_revision_manual_sin_traza():
    assert (
        destino_workflow_sync_item(
            etapa_final=None,
            traza_pago_id=None,
            duplicado_en_pagos=False,
        )
        == "revision_manual"
    )
