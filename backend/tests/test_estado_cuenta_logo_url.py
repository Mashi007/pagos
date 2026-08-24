# -*- coding: utf-8 -*-
"""Logo en plantilla ESTADO_CUENTA usa la misma URL que el resto de correos."""
from __future__ import annotations

from app.services.estado_cuenta_notificacion_envio import _cuerpo_html_para_item, _logo_url


def test_logo_url_estado_cuenta_usa_ruta_publica_correcta():
    url = _logo_url()
    assert "/logos/rapicredit-public.png" in url
    assert "logo-rapicredit.png" not in url


def test_cuerpo_html_sustituye_logo_url_en_plantilla():
    html = _cuerpo_html_para_item(
        {"nombre": "Juan", "cedula": "123"},
        '<img src="{{logo_url}}" alt="Rapicredit">',
    )
    assert "{{logo_url}}" not in html
    assert "/logos/rapicredit-public.png" in html
