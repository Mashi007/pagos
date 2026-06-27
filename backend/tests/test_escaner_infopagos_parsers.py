"""Parsers compartidos de monto/fecha (escáner Infopagos y Gmail)."""
from datetime import date

from app.services.pagos_gmail.helpers import format_monto_excel_pagos_gmail, normalizar_fecha_pago
from app.services.pagos_gmail.parse_campos_comprobante import (
    aplicar_reglas_ocr_post_gemini,
    clave_numero_operacion_canonico,
    duplicado_digitos_misma_longitud_mas_umbral,
    fecha_ocr_borrosa_revision_manual,
    gemini_indico_fecha_borrosa,
    gemini_indico_monto_borroso,
    gemini_indico_serial_borroso,
    hamming_digitos_misma_longitud,
    min_digitos_inequivocos_ocr,
    normalizar_campos_gemini_gmail,
    serial_ocr_borrosa_revision_manual,
    numeros_operacion_coinciden_o_evasion,
    parse_fecha_comprobante,
    parse_monto_comprobante,
    sanitizar_numero_operacion_comprobante,
)

REF = date(2026, 5, 31)


def test_parse_monto_comprobante_miles_venezolanos():
    assert parse_monto_comprobante("1.500,00") == 1500.0
    assert parse_monto_comprobante("1.500") == 1500.0
    assert parse_monto_comprobante("15.000,50") == 15000.5
    assert parse_monto_comprobante("150,50") == 150.5
    assert parse_monto_comprobante("150.25") == 150.25


def test_parse_monto_comprobante_mercantil_asteriscos_y_ocr():
    assert parse_monto_comprobante("***********96,00 USD") == 96.0
    assert parse_monto_comprobante("***********98,00 USD") == 98.0
    assert parse_monto_comprobante("969") == 96.0
    assert parse_monto_comprobante("965") == 96.0
    assert parse_monto_comprobante("980") == 98.0
    assert parse_monto_comprobante("150") == 150.0


def test_parse_monto_comprobante_bnc_asteriscos_114_no_14():
    assert parse_monto_comprobante("**************114.00", moneda="USD") == 114.0
    assert parse_monto_comprobante("*******14.00", moneda="USD") == 114.0
    assert parse_monto_comprobante("*****96.00", moneda="USD") == 96.0
    assert parse_monto_comprobante(14, moneda="USD", institucion="BNC") == 114.0
    assert parse_monto_comprobante(14, moneda="USD", institucion="Mercantil") == 14.0
    assert parse_monto_comprobante(96, moneda="USD", institucion="BNC") == 96.0


def test_parse_monto_comprobante_binance_usdt_no_truncar_cientos():
    """Binance Pay: 580 USDT es monto real; no aplicar heurística Mercantil 580→58."""
    assert parse_monto_comprobante("580", moneda="USD") == 580.0
    assert parse_monto_comprobante("580 USDT", moneda="USD") == 580.0
    assert parse_monto_comprobante("580.00", moneda="USD") == 580.0
    assert parse_monto_comprobante(580, moneda="USD") == 580.0


def test_parse_monto_comprobante_bnc_usd_decimal_ocr():
    assert parse_monto_comprobante("135.00") == 135.0
    assert parse_monto_comprobante("***********135.00") == 135.0
    assert parse_monto_comprobante("135.00 USD") == 135.0
    assert parse_monto_comprobante("135.000", moneda="USD") == 135.0
    assert parse_monto_comprobante("135000", moneda="USD") == 135.0
    assert parse_monto_comprobante("13500", moneda="USD") == 135.0
    assert parse_monto_comprobante("1.350.00", moneda="USD") == 1350.0
    assert parse_monto_comprobante(135000, moneda="USD") == 135.0


def test_parse_monto_comprobante_no_corregir_bs_miles():
    assert parse_monto_comprobante("15.000", moneda="BS") == 15000.0
    assert parse_monto_comprobante("135000", moneda="BS") == 135000.0


def test_monto_requiere_revision_manual_umbral():
    from app.services.pagos_gmail.parse_campos_comprobante import (
        MONTO_UMBRAL_REVISION_MANUAL,
        fusionar_validacion_reglas_monto_alto_escaneo,
        monto_requiere_revision_manual,
    )

    assert MONTO_UMBRAL_REVISION_MANUAL == 1000.0
    assert monto_requiere_revision_manual(1000)
    assert monto_requiere_revision_manual(1000.01)
    assert not monto_requiere_revision_manual(999.99)
    assert monto_requiere_revision_manual(1500, moneda="BS")
    assert monto_requiere_revision_manual(1500, moneda="USD")
    msg = fusionar_validacion_reglas_monto_alto_escaneo(None, 1500, moneda="USD")
    assert msg is not None
    assert "1,000" in msg or "1000" in msg


def test_parse_fecha_comprobante():
    assert parse_fecha_comprobante("31/05/2026", REF) == date(2026, 5, 31)
    assert parse_fecha_comprobante("31/05/26", REF) == date(2026, 5, 31)
    assert parse_fecha_comprobante("2026-05-31", REF) == date(2026, 5, 31)
    assert parse_fecha_comprobante(
        "fecha operacion 21/04/2025 sello", REF
    ) == date(2025, 4, 21)
    assert parse_fecha_comprobante("310526", REF) == date(2026, 5, 31)
    assert parse_fecha_comprobante("09-02-2025", REF) == date(2025, 2, 9)
    assert parse_fecha_comprobante(
        "9824-20250703-151620-DCME-4279-A", REF
    ) == date(2025, 7, 3)
    assert parse_fecha_comprobante("2027-01-01", REF) is None
    assert parse_fecha_comprobante("", REF) is None


def test_format_monto_excel_pagos_gmail_miles():
    assert format_monto_excel_pagos_gmail("1.500") == "1500.00"
    assert format_monto_excel_pagos_gmail("Bs. 15.000,50") == "15000.50"
    assert format_monto_excel_pagos_gmail("NR") == "NR"


def test_normalizar_fecha_pago_valida():
    assert normalizar_fecha_pago("31/05/2026", ref_hoy=REF) == "31/05/2026"


def test_normalizar_campos_gemini_gmail_fecha_futura():
    out = normalizar_campos_gemini_gmail(
        {
            "fecha_pago": "2027-01-01",
            "monto": "10.00",
            "cedula": "NA",
            "numero_referencia": "123",
        }
    )
    assert out["fecha_pago"] == "NA"
    assert out["monto"] == "10.00"


def test_extraer_fecha_desde_asunto_pipeline():
    from app.services.pagos_gmail.helpers import extraer_fecha_desde_asunto_pipeline

    assert extraer_fecha_desde_asunto_pipeline("Eberso Figueroa pago mes 14/06/2026") == "14/06/2026"
    assert extraer_fecha_desde_asunto_pipeline("sin fecha") == ""


def test_pagos_gmail_a_campos_imagen_minimos():
    from app.services.pagos_gmail.gemini_service import _pagos_gmail_a_campos_imagen_minimos

    assert _pagos_gmail_a_campos_imagen_minimos(
        {
            "fecha_pago": "NA",
            "monto": "107.00",
            "numero_referencia": "740009403001332",
        }
    )
    assert not _pagos_gmail_a_campos_imagen_minimos(
        {"fecha_pago": "NA", "monto": "NA", "numero_referencia": "740009403001332"}
    )


def test_normalizar_campos_gemini_gmail_fecha_desde_serial_mercantil():
    out = normalizar_campos_gemini_gmail(
        {
            "fecha_pago": "NA",
            "monto": "96.00",
            "cedula": "NA",
            "numero_referencia": "740087452690993",
        }
    )
    assert out["fecha_pago"] == "NA" or out["fecha_pago"] == ""
    out2 = normalizar_campos_gemini_gmail(
        {
            "fecha_pago": "",
            "monto": "96.00",
            "cedula": "NA",
            "numero_referencia": "9824-20250703-151620-DCME-4279-A",
        }
    )
    assert out2["fecha_pago"] == "03/07/2025"


def test_normalizar_campos_gemini_gmail():
    out = normalizar_campos_gemini_gmail(
        {
            "fecha_pago": "31/05/2026",
            "monto": "1.500",
            "cedula": "NA",
            "numero_referencia": "123",
        }
    )
    assert out["monto"] == "1500.00"
    assert out["fecha_pago"] == "31/05/2026"


def test_sanitizar_numero_operacion_comprobante():
    assert sanitizar_numero_operacion_comprobante("113907169113907169") == "113907169"
    assert sanitizar_numero_operacion_comprobante("113907169113907166") == "113907166"
    assert sanitizar_numero_operacion_comprobante("Serial: 113907166") == "113907166"
    assert sanitizar_numero_operacion_comprobante("0000091316488") == "0000091316488"
    assert sanitizar_numero_operacion_comprobante("113907169 113907169") == "113907169"
    assert sanitizar_numero_operacion_comprobante("113907169 113907166") == "113907166"


def test_sanitizar_bnc_preferir_serial_sobre_ref():
    assert sanitizar_numero_operacion_comprobante(
        "Ref: 105137683 Serial: 105137674"
    ) == "105137674"
    assert sanitizar_numero_operacion_comprobante(
        "105137683 105137674"
    ) == "105137674"


def test_corregir_numero_operacion_bnc_serial():
    from app.services.pagos_gmail.parse_campos_comprobante import (
        corregir_numero_operacion_bnc,
    )

    assert corregir_numero_operacion_bnc(
        "105137683",
        institucion="BNC",
        texto_auxiliar="Ref: 105137683 Serial: 105137674",
    ) == "105137674"
    assert corregir_numero_operacion_bnc(
        "105137674",
        institucion="BNC",
    ) == "105137674"


def test_sanitizar_numero_operacion_binance_id_completo():
    """ID de orden Binance (18 dígitos) no debe truncarse como Ref+Serial BNC."""
    assert sanitizar_numero_operacion_comprobante("436166756159873024") == "436166756159873024"
    assert sanitizar_numero_operacion_comprobante("436166756") == "436166756"


def test_sanitizar_preferir_serial_mercantil_sobre_dcme():
    assert sanitizar_numero_operacion_comprobante(
        "9213-20260331-151620-DCME-3122-A 740087452690993"
    ) == "740087452690993"
    assert sanitizar_numero_operacion_comprobante(
        "Serial: 740087401612580"
    ) == "740087401612580"
    assert sanitizar_numero_operacion_comprobante(
        "9213-20260331-151620-DCME-3122-A"
    ) == "9213-20260331-151620-DCME-3122-A"


def test_corregir_numero_operacion_mercantil_serial_740087():
    from app.services.pagos_gmail.parse_campos_comprobante import (
        corregir_numero_operacion_mercantil,
        extraer_serial_mercantil_7400,
    )

    dcme = "9276-20260424-140259-DCME-7819-A"
    serial = "740087408543435"
    assert extraer_serial_mercantil_7400(f"{serial}{serial}") == serial
    assert extraer_serial_mercantil_7400(f"Serial: {serial}{serial}") == serial
    assert corregir_numero_operacion_mercantil(
        dcme,
        institucion="Mercantil",
        texto_auxiliar=f"Serial: {serial}",
    ) == serial
    assert corregir_numero_operacion_mercantil(dcme, institucion="Mercantil") == ""
    assert corregir_numero_operacion_mercantil(
        f"{dcme} {serial}",
        institucion="Mercantil",
    ) == serial
    assert corregir_numero_operacion_mercantil(serial, institucion="Mercantil") == serial
    assert corregir_numero_operacion_mercantil(
        serial,
        institucion="Mercantil",
        texto_auxiliar=f"{serial}{serial}",
    ) == serial
    assert sanitizar_numero_operacion_comprobante(
        f"Serial: {serial}{serial}"
    ) == serial
    assert sanitizar_numero_operacion_comprobante(f"{serial}{serial}") == serial


def test_serial_mercantil_14_digitos_truncado_no_aceptado():
    from app.services.pagos_gmail.parse_campos_comprobante import (
        corregir_numero_operacion_mercantil,
        extraer_serial_mercantil_7400,
        serial_mercantil_requiere_rescate,
    )

    truncado = "74008740065053"
    assert len(truncado) == 14
    assert serial_mercantil_requiere_rescate(truncado) is True
    assert extraer_serial_mercantil_7400(truncado) == ""
    assert corregir_numero_operacion_mercantil(truncado, institucion="Mercantil") == ""


def test_resolver_fecha_escaner_rechaza_hoy_y_prefiere_dcme():
    ref = date(2026, 6, 23)
    dcme = "9264-20260618-115409-DCME-5574-A"
    serial = "740087459986093"
    esc = aplicar_reglas_ocr_post_gemini(
        {
            "fecha_pago": "2026-06-23",
            "numero_operacion": serial,
            "notas": dcme,
            "institucion_financiera": "Mercantil",
        },
        perfil="escaner",
        ref_hoy=ref,
    )
    assert esc["fecha_pago"] == date(2026, 6, 18)

    bnc = aplicar_reglas_ocr_post_gemini(
        {
            "fecha_pago": "2026-06-23",
            "numero_operacion": "105137674",
            "notas": "",
            "institucion_financiera": "BNC",
        },
        perfil="escaner",
        ref_hoy=ref,
    )
    assert bnc["fecha_pago"] is None

    bnc_ok = aplicar_reglas_ocr_post_gemini(
        {
            "fecha_pago": "2026-06-18",
            "numero_operacion": "105137674",
            "notas": "",
            "institucion_financiera": "BNC",
        },
        perfil="escaner",
        ref_hoy=ref,
    )
    assert bnc_ok["fecha_pago"] == date(2026, 6, 18)


def test_inferir_fecha_mercantil_desde_dcme_recuadro():
    from app.services.pagos_gmail.parse_campos_comprobante import (
        extraer_codigo_dcme_mercantil_en_texto,
        inferir_fecha_pago_mercantil_desde_texto,
        inferir_fecha_pago_desde_numero_operacion,
    )

    dcme = "9264-20260618-115409-DCME-5574-A"
    serial = "740087459986093"
    assert extraer_codigo_dcme_mercantil_en_texto(dcme) == dcme
    assert inferir_fecha_pago_mercantil_desde_texto(dcme) == "18/06/2026"
    assert inferir_fecha_pago_desde_numero_operacion(serial) == ""
    blob = f"Serial: {serial}\n{dcme}"
    assert inferir_fecha_pago_mercantil_desde_texto(blob) == "18/06/2026"


def test_normalizar_campos_gemini_descarta_dcme_sin_serial():
    out = normalizar_campos_gemini_gmail(
        {
            "fecha_pago": "",
            "monto": "100.00",
            "cedula": "NA",
            "numero_referencia": "9824-20250703-151620-DCME-4279-A",
            "banco": "Mercantil",
        }
    )
    assert out["numero_referencia"] == "NA"
    assert out["fecha_pago"] == "03/07/2025"


def test_clave_numero_operacion_canonico():
    assert clave_numero_operacion_canonico("0000091316488") == "91316488"
    assert clave_numero_operacion_canonico("91316488") == "91316488"
    assert clave_numero_operacion_canonico("0000091316488") == clave_numero_operacion_canonico(
        "91316488"
    )
    assert clave_numero_operacion_canonico("ABC-123") == "ABC-123"


def test_sanitizar_mercantil_preserva_sufijo_visto_admin():
    """Visto Cobros: serial 740087… + _A####/_P#### no debe perderse al sanitizar."""
    serial = "740087405835596"
    assert sanitizar_numero_operacion_comprobante(serial) == serial
    assert sanitizar_numero_operacion_comprobante(f"{serial}_A0042") == f"{serial}_A0042"
    assert sanitizar_numero_operacion_comprobante(f"{serial}_P1234") == f"{serial}_P1234"
    assert clave_numero_operacion_canonico(f"{serial}_A0042") == f"{serial}_A0042"


def test_normalizar_referencia_conserva_ceros():
    from app.services.pagos_gmail.helpers import normalizar_referencia

    assert normalizar_referencia("0000091316488") == "0000091316488"
    assert normalizar_referencia("Serial: 113907166") == "113907166"


def test_inferir_fecha_pago_desde_numero_operacion_dcme():
    from app.services.pagos_gmail.parse_campos_comprobante import (
        inferir_fecha_pago_desde_numero_operacion,
    )

    assert (
        inferir_fecha_pago_desde_numero_operacion(
            "9824-20250703-151620-DCME-4279-A", REF
        )
        == "03/07/2025"
    )
    assert inferir_fecha_pago_desde_numero_operacion("740087452690993", REF) == ""


def test_escaner_gem_resultado_mas_completo_prefiere_fecha():
    from app.services.pagos_gmail.gemini_service import _escaner_gem_resultado_mas_completo
    from datetime import date

    prim = {"ok": True, "fecha_pago": None, "numero_operacion": "123"}
    seg = {"ok": True, "fecha_pago": date(2025, 7, 3), "numero_operacion": "123"}
    out = _escaner_gem_resultado_mas_completo(prim, seg)
    assert out is seg
    assert numeros_operacion_coinciden_o_evasion(
        "740087452690993", "0993"
    )
    assert numeros_operacion_coinciden_o_evasion(
        "0993", "740087452690993"
    )
    assert numeros_operacion_coinciden_o_evasion(
        "7400874101194", "740087410119497"
    )
    assert numeros_operacion_coinciden_o_evasion(
        "740087410119497", "7400874101194"
    )
    assert not numeros_operacion_coinciden_o_evasion(
        "123456789012345", "6789"
    )
    assert numeros_operacion_coinciden_o_evasion(
        "7400874101194", "7400874101195"
    )
    assert not numeros_operacion_coinciden_o_evasion(
        "7400874101194", "7400874101284"
    )
    assert not duplicado_digitos_misma_longitud_mas_umbral(
        "7400874101194", "7400874101284"
    )
    assert hamming_digitos_misma_longitud("7400874101194", "7400874101195") == 1
    assert hamming_digitos_misma_longitud("7400874101194", "7400874101284") == 2
    assert not numeros_operacion_coinciden_o_evasion("12345", "678912345")
    assert not numeros_operacion_coinciden_o_evasion(
        "0993",
        "740087452690993",
        monto_a=135.0,
        monto_b=96.0,
    )
    assert numeros_operacion_coinciden_o_evasion(
        "0993",
        "740087452690993",
        monto_a=135.0,
        monto_b=135.0,
    )


def test_fecha_ocr_borrosa_revision_manual_criterio():
    assert fecha_ocr_borrosa_revision_manual(digitos_inequivocos=8) is False
    assert fecha_ocr_borrosa_revision_manual(digitos_inequivocos=7) is False
    assert fecha_ocr_borrosa_revision_manual(digitos_inequivocos=6) is True
    assert fecha_ocr_borrosa_revision_manual(
        digitos_inequivocos=7, dos_fechas_validas_distintas=True
    ) is True
    assert fecha_ocr_borrosa_revision_manual(
        digitos_inequivocos=8, digitos_ambiguos_afectan_calendario=True
    ) is True


def test_gemini_indico_fecha_borrosa_y_parse_conservador():
    assert gemini_indico_fecha_borrosa("", "fecha borrosa L<0,875") is True
    assert gemini_indico_fecha_borrosa("2026-06-18", "") is False
    assert parse_fecha_comprobante("03/05/2024", REF) is not None
    assert parse_fecha_comprobante("03/05/2024", REF, conservador=True) is None


def test_parse_monto_comprobante_no_truncar_600_a_60():
    """El backend no debe 'corregir' 60→600 ni 600→60 sin evidencia en el string."""
    assert parse_monto_comprobante("600") == 600.0
    assert parse_monto_comprobante("600,00") == 600.0
    assert parse_monto_comprobante("600.00", moneda="USD") == 600.0
    assert parse_monto_comprobante("60") == 60.0
    assert parse_monto_comprobante("60,00 USD", moneda="USD") == 60.0


def test_gemini_indico_monto_borroso_y_aplicar_reglas():
    assert gemini_indico_monto_borroso(60, "monto borroso, duda 600 vs 60") is True
    assert gemini_indico_monto_borroso(600, "") is False
    esc = aplicar_reglas_ocr_post_gemini(
        {"monto": 60, "notas": "monto borroso L<0,875"},
        perfil="escaner",
    )
    assert esc["monto"] is None
    assert esc["_ocr_monto_borroso"] is True
    gmail = aplicar_reglas_ocr_post_gemini(
        {"monto": "600", "notas": "monto borroso revisión manual"},
        perfil="gmail",
    )
    assert gmail["monto"] == "NA"


def test_serial_borroso_mismo_criterio_matematico_fecha():
    assert min_digitos_inequivocos_ocr(8) == 7
    assert min_digitos_inequivocos_ocr(15) == 14
    assert min_digitos_inequivocos_ocr(13) == 12
    assert serial_ocr_borrosa_revision_manual(digitos_inequivocos=14, total_digitos=15) is False
    assert serial_ocr_borrosa_revision_manual(digitos_inequivocos=13, total_digitos=15) is True
    assert serial_ocr_borrosa_revision_manual(digitos_inequivocos=11, total_digitos=13) is True
    assert serial_ocr_borrosa_revision_manual(digitos_inequivocos=12, total_digitos=13) is False
    assert gemini_indico_serial_borroso("7400874101194", "serial borroso L<0,875") is True
    assert gemini_indico_serial_borroso("7400874101194", "") is False


def test_aplicar_reglas_ocr_post_gemini_perfiles():
    gmail = aplicar_reglas_ocr_post_gemini(
        {
            "fecha_pago": "31/05/2026",
            "numero_referencia": "113907169113907169",
            "banco": "BNC",
            "notas": "",
        },
        perfil="gmail",
    )
    assert gmail["numero_referencia"] == "113907169"
    assert gmail["fecha_pago"] == "31/05/2026"

    gmail_b = aplicar_reglas_ocr_post_gemini(
        {
            "fecha_pago": "2026-06-18",
            "numero_referencia": "7400874101194",
            "notas": "serial borroso L<0,875",
        },
        perfil="gmail",
    )
    assert gmail_b["numero_referencia"] == "NA"

    cob = aplicar_reglas_ocr_post_gemini(
        {
            "fecha_deposito": "03/05/2024",
            "numero_deposito": "105137674",
            "numero_documento": "NA",
            "notas": "",
        },
        perfil="cobranza",
    )
    assert cob["fecha_deposito"] == "NA"
    assert cob["numero_deposito"] == "105137674"


def test_escaner_imagen_aparenta_portrait():
    import io

    from PIL import Image

    from app.services.pagos_gmail.gemini_service import _escaner_imagen_aparenta_portrait

    buf_land = io.BytesIO()
    Image.new("RGB", (800, 400), "white").save(buf_land, format="JPEG")
    buf_port = io.BytesIO()
    Image.new("RGB", (400, 800), "white").save(buf_port, format="JPEG")

    assert _escaner_imagen_aparenta_portrait(buf_land.getvalue(), "land.jpg", "image/jpeg") is False
    assert _escaner_imagen_aparenta_portrait(buf_port.getvalue(), "port.jpg", "image/jpeg") is True


def test_escaner_necesita_rescate_rotacion_mercantil_sin_serial():
    from app.services.pagos_gmail.gemini_service import _escaner_necesita_rescate_rotacion

    assert _escaner_necesita_rescate_rotacion({"ok": False}) is True
    assert (
        _escaner_necesita_rescate_rotacion(
            {
                "ok": True,
                "numero_operacion": "9818-20251111-111511-DCME-3280-A",
                "institucion_financiera": "Mercantil",
                "fecha_pago": REF,
                "monto": 20.0,
            }
        )
        is True
    )
    assert (
        _escaner_necesita_rescate_rotacion(
            {
                "ok": True,
                "numero_operacion": "740087404834849",
                "institucion_financiera": "Mercantil",
                "fecha_pago": REF,
                "monto": 20.0,
            }
        )
        is False
    )

