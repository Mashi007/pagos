# -*- coding: utf-8 -*-
"""Inventario multi-archivo Gmail: ruido auditado + detalle por correo."""
from app.services.pagos_gmail.pipeline import (
    _detalle_inventario_archivos_email,
    _filtrar_adjuntos_ruido_pagos_gmail_gemini,
)


def test_filtro_ruido_conserva_adjunto_y_reporta_omitido():
    recibo = ("recibo.jpg", b"x" * 200_000, "image/jpeg", "adjunta")
    logo = ("image.png", b"y" * 10_000, "image/png", "embebida")
    kept, omitidos = _filtrar_adjuntos_ruido_pagos_gmail_gemini([recibo, logo])
    assert len(kept) == 1
    assert kept[0][0] == "recibo.jpg"
    assert len(omitidos) == 1
    assert omitidos[0][0] == "image.png"
    assert omitidos[0][4] == "ruido_embebido_ligero"


def test_filtro_ruido_no_vacia_lista():
    logo1 = ("image.png", b"a" * 8_000, "image/png", "embebida")
    logo2 = ("image.jpg", b"b" * 8_000, "image/jpeg", "embebida")
    kept, omitidos = _filtrar_adjuntos_ruido_pagos_gmail_gemini([logo1, logo2])
    # si ambos son ruido, se conserva la lista original y omitidos vacio
    assert len(kept) == 2
    assert omitidos == []


def test_filtro_un_solo_candidato_nunca_omite():
    logo = ("image.png", b"a" * 8_000, "image/png", "embebida")
    kept, omitidos = _filtrar_adjuntos_ruido_pagos_gmail_gemini([logo])
    assert kept == [logo]
    assert omitidos == []


def test_detalle_inventario_incluye_conteos():
    d = _detalle_inventario_archivos_email(
        n_descubiertos=3,
        n_despues_expand=4,
        n_pdf_multipagina=1,
        n_a_gemini=3,
        n_omitidos_ruido=1,
        nombres_a_gemini=["a.jpg", "b.pdf", "c.png"],
        nombres_omitidos_ruido=["image.png"],
    )
    assert "descubiertos=3" in d
    assert "tras_expand_pdf=4" in d
    assert "a_gemini=3" in d
    assert "omitidos_ruido=1" in d
    assert "a.jpg" in d
