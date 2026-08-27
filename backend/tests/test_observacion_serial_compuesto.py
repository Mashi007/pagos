from app.services.observacion_serial_compuesto import (
    MARCA_OBS_SERIAL_COMPUESTO,
    aplicar_supresion_revision_serial_compuesto,
    observaciones_suprimen_caso_revision,
    texto_tiene_marca_serial_compuesto,
)


def test_texto_tiene_marca_serial_compuesto():
    assert texto_tiene_marca_serial_compuesto(f"100% | {MARCA_OBS_SERIAL_COMPUESTO}")
    assert texto_tiene_marca_serial_compuesto("serial mixto detectado")
    assert not texto_tiene_marca_serial_compuesto("BNC/125201931")
    assert not texto_tiene_marca_serial_compuesto("")


def test_aplicar_supresion_revision_serial_compuesto():
    assert aplicar_supresion_revision_serial_compuesto(True, "monto alto") is True
    assert (
        aplicar_supresion_revision_serial_compuesto(
            True, f"match ok | {MARCA_OBS_SERIAL_COMPUESTO}"
        )
        is False
    )
    assert observaciones_suprimen_caso_revision(None, "serial Mixto") is True
