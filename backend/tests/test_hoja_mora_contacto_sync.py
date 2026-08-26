"""Tests hoja mora contacto sync."""

from app.services.hoja_mora_contacto_sync import contacto_para_filas_hoja


def test_contacto_para_filas_hoja_sin_db(monkeypatch):
    """Lookup por mapa precargado (misma regla E/V)."""
    mapa = {"V84491751": ("a@mail.com", "04141111111")}

    class FakeDb:
        pass

    monkeypatch.setattr(
        "app.services.hoja_mora_contacto_sync._contacto_bd_por_cedula_norm",
        lambda _db, _ceds: mapa,
    )
    out = contacto_para_filas_hoja(FakeDb(), ["E84491751", ""])
    assert out[0] == ("a@mail.com", "04141111111")
    assert out[1] == (None, None)
