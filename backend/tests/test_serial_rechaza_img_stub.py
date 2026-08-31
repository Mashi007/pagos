# -*- coding: utf-8 -*-
"""Serial bancario: rechazar stubs IMG-/nombres de archivo."""
from app.services.pagos_gmail.parse_campos_comprobante import (
    es_falso_serial_imagen_archivo,
    sanitizar_numero_operacion_comprobante,
    _procesar_serial_ocr_post_gemini,
)
from app.services.auditoria_email.receipts_service import _norm_serial


def test_detecta_stub_img_hash():
    assert es_falso_serial_imagen_archivo("IMG-cd169e618b") is True
    assert es_falso_serial_imagen_archivo("img_abc123def0") is True
    assert es_falso_serial_imagen_archivo("inline-0.jpg") is True
    assert es_falso_serial_imagen_archivo("photo.png") is True
    assert es_falso_serial_imagen_archivo("54879263323") is False
    assert es_falso_serial_imagen_archivo("BNC/54879263323") is False
    assert es_falso_serial_imagen_archivo("740087408543435") is False


def test_sanitizar_y_post_gemini_descartan_img():
    assert sanitizar_numero_operacion_comprobante("IMG-cd169e618b") == ""
    assert (
        _procesar_serial_ocr_post_gemini(
            "IMG-cd169e618b", notas="", institucion="BNC"
        )
        == ""
    )


def test_norm_serial_recibos_ignora_img():
    assert _norm_serial("IMG-cd169e618b", institucion="BNC") == ""
    assert _norm_serial("54879263323", institucion="BNC") == "54879263323"
