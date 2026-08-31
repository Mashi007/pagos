# -*- coding: utf-8 -*-
"""Alineación serial recibo escaneado ↔ pagos.numero_documento (clave canónica)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.core.documento import compose_numero_documento_almacenado
from app.services.auditoria_email.receipts_service import (
    _norm_serial,
    receipt_dict,
    serial_estado_recibo,
)


DIGITS = "54879263323"
DIGITS_MERC = "740087406515657"


def test_enviar_revision_descarta_si_serial_control5_en_bd():
    """Serial ya en cartera (_A####) no debe abrir revisión (falso positivo)."""
    from app.services.auditoria_email.receipts_service import (
        _enviar_a_pagos_con_errores,
    )

    ocr = "740087402484647"
    row = SimpleNamespace(
        id=88,
        message_id=1,
        gmail_message_id="g88",
        filename="x.jpg",
        mime_type="image/jpeg",
        size_kb=1,
        cedula="V1",
        monto=96.0,
        banco="Mercantil",
        fecha_pago="07/01/2023",
        numero_referencia=ocr,
        image_url=None,
        status="pending",
        sync_id=None,
        sync_item_id=None,
        gmail_temporal_id=None,
        pago_id=None,
        pago_error_id=None,
        last_error=None,
        route=None,
        ocr_status=None,
        created_at=None,
        resolved_at=None,
    )
    db = MagicMock()
    with patch(
        "app.services.auditoria_email.receipts_service._serial_duplicado_cartera_real",
        return_value=True,
    ), patch(
        "app.services.auditoria_email.receipts_service._descartar_recibo_serial_ya_en_bd",
        return_value={
            "ok": True,
            "descartado": True,
            "motivo": "serial_ya_en_bd",
            "status": "descartado",
        },
    ) as disc:
        out = _enviar_a_pagos_con_errores(db, row, motivo="cualquier_motivo")
    disc.assert_called_once()
    assert out.get("motivo") == "serial_ya_en_bd"
    assert out.get("descartado") is True


def test_revision_manual_descarta_serial_ya_en_bd():
    from app.services.auditoria_email.receipts_service import revision_manual_recibo

    row = SimpleNamespace(
        id=89,
        numero_referencia="740087402484647",
        banco="Mercantil",
        pago_id=None,
        pago_error_id=None,
        status="pending",
    )
    db = MagicMock()
    db.get.return_value = row
    with patch(
        "app.services.auditoria_email.receipts_service._serial_duplicado_cartera_real",
        return_value=True,
    ), patch(
        "app.services.auditoria_email.receipts_service._descartar_recibo_serial_ya_en_bd",
        return_value={"ok": True, "motivo": "serial_ya_en_bd", "descartado": True},
    ) as disc, patch(
        "app.services.auditoria_email.receipts_service._enviar_a_pagos_con_errores"
    ) as env:
        out = revision_manual_recibo(db, 89)
    disc.assert_called_once()
    env.assert_not_called()
    assert out.get("motivo") == "serial_ya_en_bd"


def test_serial_duplicado_control5_visto_via_hits():
    from app.services.auditoria_email.receipts_service import (
        _serial_duplicado_cartera_real,
    )

    ocr = "740087402484647"
    db = MagicMock()
    with patch(
        "app.services.auditoria_email.receipts_service._listar_hits_numero_documento",
        return_value=[("pagos", 501, f"{ocr}_A8532", "Mercantil")],
    ):
        assert (
            _serial_duplicado_cartera_real(
                db, ocr, institucion_recibo="Mercantil"
            )
            is True
        )


def test_norm_serial_control5_visto_a_sufijo():
    """
    Papel 740087402484647 ≡ cartera Control 5 / validador ``…_A8532`` / UI ``· A8532``.
    Debe ser DUPLICADO, no UNICO.
    """
    ocr = "740087402484647"
    variants = [
        f"{ocr}_A8532",
        f"{ocr} · A8532",
        f"{ocr}·A8532",
        f"{ocr} A8532",
        compose_numero_documento_almacenado(ocr, "A8532"),
    ]
    assert {_norm_serial(v) for v in variants} == {ocr}
    assert _norm_serial(ocr) == ocr

    row = SimpleNamespace(
        id=77,
        numero_referencia=ocr,
        banco="Mercantil",
        pago_id=None,
        pago_error_id=None,
    )
    registered = {_norm_serial(f"{ocr}_A8532")}
    assert registered == {ocr}
    db = MagicMock()
    assert (
        serial_estado_recibo(
            db,
            row,
            pending_counts={ocr: 1},
            registered_norms=registered,
        )
        == "DUPLICADO"
    )


def test_norm_serial_igual_canon_gmail_cobros():
    """Recibos delega a serial_comprobante_canonico_colision (misma puerta Gmail)."""
    from app.services.cobros.pago_reportado_documento import (
        serial_comprobante_canonico_colision,
    )

    composed = compose_numero_documento_almacenado(DIGITS_MERC, "D7341")
    for raw in (
        DIGITS_MERC,
        f"MER/{DIGITS_MERC}",
        composed,
        f"{DIGITS_MERC} · D7341",
        "000041214254",
        "41214254",
        "740087402484647_A8532",
        "740087402484647 · A8532",
    ):
        assert _norm_serial(raw) == serial_comprobante_canonico_colision(raw)


def test_norm_serial_alinea_ocr_prefijos_y_bd_compuesta():
    """OCR con MER/BNC ≡ dígitos ≡ valor en BD con §CD:."""
    composed = compose_numero_documento_almacenado(DIGITS, "D1020")
    assert composed and "§CD:" in composed

    variantes = [
        DIGITS,
        f"MER/{DIGITS}",
        f"BNC/{DIGITS}",
        f"BNC{DIGITS}",
        f"BINANCE/{DIGITS}",
        f"  {DIGITS}  ",
        composed,
        f"MER/{composed}",
    ]
    keys = {_norm_serial(v) for v in variantes}
    assert keys == {DIGITS}


def test_norm_serial_ignora_ceros_izquierda_bdv():
    """OCR BDV 000041214254 ≡ Nº documento cartera 41214254."""
    assert _norm_serial("000041214254", institucion="BDV") == "41214254"
    assert _norm_serial("41214254", institucion="Banco de Venezuela") == "41214254"
    assert _norm_serial("000041214254", institucion="BDV") == _norm_serial(
        "41214254", institucion="BDV"
    )


def test_registered_batch_encuentra_bd_sin_ceros_con_ocr_padded():
    """
    Batch de listado: OCR 000041214254 debe marcar registered si BD tiene 41214254.
    (Antes LIKE %000041214254% no encontraba 41214254 → falso UNICO.)
    """
    from app.services.auditoria_email.receipts_service import _registered_serials_batch

    db = MagicMock()

    def _exec(stmt):
        sql = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        m = MagicMock()
        # Exacto upper.in_ : vacío; LIKE %41214254%: hit cartera
        if "like" in sql.lower() or "LIKE" in sql:
            m.all.return_value = [("41214254", "Banco de Venezuela")]
        else:
            m.all.return_value = []
        return m

    db.execute.side_effect = _exec
    found = _registered_serials_batch(db, ["000041214254", "41214254"])
    assert "41214254" in found


def test_normalize_documento_quita_ceros_izquierda():
    from app.core.documento import normalize_documento

    assert normalize_documento("000041214254") == "41214254"
    assert normalize_documento("41214254") == "41214254"


def test_norm_serial_omite_sufijo_d_listado_y_pegado():
    """Misma clave si BD/UI trae · D#### o D#### pegado (caso 7400… · D7341)."""
    composed = compose_numero_documento_almacenado(DIGITS_MERC, "D7341")
    variantes = [
        DIGITS_MERC,
        composed,
        f"{DIGITS_MERC} · D7341",
        f"{DIGITS_MERC}·D7341",
        f"{DIGITS_MERC} D7341",
        f"{DIGITS_MERC}D7341",
        f"MER/{DIGITS_MERC} · D7341",
    ]
    keys = {_norm_serial(v) for v in variantes}
    assert keys == {DIGITS_MERC}


def test_serial_estado_duplicado_si_bd_tiene_codigo_d_listado():
    """Recibo bare 7400… → DUPLICADO si cartera tiene 7400… §CD:D7341."""
    row = SimpleNamespace(
        id=11,
        numero_referencia=DIGITS_MERC,
        banco="Mercantil",
        pago_id=None,
        pago_error_id=None,
    )
    composed = compose_numero_documento_almacenado(DIGITS_MERC, "D7341")
    registered = {_norm_serial(composed)}
    assert registered == {DIGITS_MERC}

    db = MagicMock()
    out = serial_estado_recibo(
        db,
        row,
        pending_counts={DIGITS_MERC: 1},
        registered_norms=registered,
    )
    assert out == "DUPLICADO"


def test_norm_serial_zelle_conserva_alfanum():
    assert _norm_serial("Ab12-Cd34", institucion="Zelle") == "AB12CD34"
    assert _norm_serial("Ab12Cd34") == "1234"  # sin Zelle: solo dígitos


def test_receipt_dict_expone_serial_canon():
    row = SimpleNamespace(
        id=1,
        message_id=2,
        gmail_message_id="g1",
        filename="x.jpg",
        mime_type="image/jpeg",
        size_kb=10,
        cedula="V1",
        monto=1.0,
        banco="BNC",
        fecha_pago="01/01/2026",
        numero_referencia=f"BNC/{DIGITS}",
        image_url=None,
        status="pending",
        sync_id=None,
        sync_item_id=None,
        gmail_temporal_id=None,
        pago_id=None,
        pago_error_id=None,
        last_error=None,
        route="pendiente_aprobacion",
        ocr_status="pagos_gmail",
        created_at=None,
        resolved_at=None,
    )
    d = receipt_dict(row, serial_estado="UNICO")
    assert d["serialCanon"] == DIGITS
    assert d["serial"] == DIGITS
    assert d["serialRaw"] == f"BNC/{DIGITS}"
    assert d["numeroReferencia"] == DIGITS


def test_serial_estado_duplicado_si_bd_tiene_seccion_cd():
    """Recibo OCR BNC/… debe marcar DUPLICADO si cartera tiene … §CD:D…."""
    row = SimpleNamespace(
        id=10,
        numero_referencia=f"BNC/{DIGITS}",
        banco="BNC",
        pago_id=None,
        pago_error_id=None,
    )
    composed = compose_numero_documento_almacenado(DIGITS, "D1020")
    registered = {_norm_serial(composed)}
    assert registered == {DIGITS}

    db = MagicMock()
    out = serial_estado_recibo(
        db,
        row,
        pending_counts={DIGITS: 1},
        registered_norms=registered,
    )
    assert out == "DUPLICADO"


def test_serial_duplicado_via_numero_documento_bnc():
    """Serial recibo = numero_documento en pagos (BNC) → DUPLICADO, no UNICO."""
    from app.services.auditoria_email.receipts_service import (
        _serial_duplicado_cartera_real,
    )

    db = MagicMock()
    with patch(
        "app.services.auditoria_email.receipts_service._listar_hits_numero_documento",
        return_value=[("pagos", 99, DIGITS, "BNC")],
    ):
        assert (
            _serial_duplicado_cartera_real(db, f"BNC/{DIGITS}", institucion_recibo="BNC")
            is True
        )


def test_serial_unico_solo_si_hit_es_drive():
    from app.services.auditoria_email.receipts_service import (
        _es_asiento_banco_drive,
        _serial_duplicado_cartera_real,
    )
    from app.services.pago_autoconciliacion import es_referencia_abonos_drive_notif

    assert _es_asiento_banco_drive("Drive", DIGITS) is True
    assert _es_asiento_banco_drive("BANCO/DRIVE", DIGITS) is True
    assert _es_asiento_banco_drive("BNC", DIGITS) is False
    assert _es_asiento_banco_drive("Mercantil", DIGITS) is False

    # Forma UI con espacios (ojo en cartera) ≡ asiento hoja CONCILIACIÓN
    ui_abonos = "ABONOS - DRIVE - 3402 - 633478BEAB"
    assert es_referencia_abonos_drive_notif(ui_abonos) is True
    assert es_referencia_abonos_drive_notif("ABONOS-DRIVE-3402-633478BEAB") is True
    assert _es_asiento_banco_drive(None, ui_abonos) is True

    db = MagicMock()
    with patch(
        "app.services.auditoria_email.receipts_service._listar_hits_numero_documento",
        return_value=[("pagos", 1, "ABONOS-DRIVE-3402-633478BEAB", "Drive")],
    ):
        assert (
            _serial_duplicado_cartera_real(db, DIGITS, institucion_recibo="BNC")
            is False
        )

    # Solo hit con forma UI espaciada → también se excluye
    with patch(
        "app.services.auditoria_email.receipts_service._listar_hits_numero_documento",
        return_value=[("pagos", 2, ui_abonos, None)],
    ):
        assert (
            _serial_duplicado_cartera_real(db, DIGITS, institucion_recibo="BNC")
            is False
        )


def test_serial_estado_unico_si_solo_match_es_drive():
    row = SimpleNamespace(
        id=12,
        numero_referencia=f"BNC/{DIGITS}",
        banco="BNC",
        pago_id=None,
        pago_error_id=None,
    )
    db = MagicMock()
    with patch(
        "app.services.auditoria_email.receipts_service._serial_duplicado_cartera_real",
        return_value=False,
    ):
        out = serial_estado_recibo(
            db,
            row,
            pending_counts={DIGITS: 1},
            registered_norms=set(),
        )
    assert out == "UNICO"


def test_serial_estado_unico_si_no_esta_en_bd():
    row = SimpleNamespace(
        id=11,
        numero_referencia=f"MER/{DIGITS}",
        banco="MERCANTIL",
        pago_id=None,
        pago_error_id=None,
    )
    db = MagicMock()
    with patch(
        "app.services.auditoria_email.receipts_service._serial_duplicado_cartera_real",
        return_value=False,
    ):
        out = serial_estado_recibo(
            db,
            row,
            pending_counts={DIGITS: 1},
            registered_norms=set(),
        )
    assert out == "UNICO"


def test_serial_estado_unico_aunque_haya_otro_pending_mismo_serial():
    """UNICO = no está en BD; repetición en cola pending no cuenta."""
    row = SimpleNamespace(
        id=12,
        numero_referencia=DIGITS,
        banco="BNC",
        pago_id=None,
        pago_error_id=None,
    )
    db = MagicMock()
    # Si aún consultara otros pending, esto lo marcaría DUPLICADO (viejo criterio).
    db.execute.return_value = [
        (99, DIGITS, "BNC"),
        (100, DIGITS, "BNC"),
    ]
    with patch(
        "app.services.auditoria_email.receipts_service._serial_duplicado_cartera_real",
        return_value=False,
    ):
        out = serial_estado_recibo(
            db,
            row,
            pending_counts={DIGITS: 5},
            registered_norms=None,
        )
    assert out == "UNICO"
    # No debe escanear pending de la cola para decidir UNICO.
    db.execute.assert_not_called()


def test_serial_estado_duplicado_solo_si_existe_en_bd():
    row = SimpleNamespace(
        id=13,
        numero_referencia=DIGITS,
        banco="BNC",
        pago_id=None,
        pago_error_id=None,
    )
    db = MagicMock()
    with patch(
        "app.services.auditoria_email.receipts_service._serial_duplicado_cartera_real",
        return_value=True,
    ):
        assert (
            serial_estado_recibo(db, row, pending_counts={DIGITS: 1}, registered_norms=None)
            == "DUPLICADO"
        )


def test_enrich_sin_cedula_via_serial_marca_duplicado_y_aprobado():
    """Sin cédula OCR: serial en BD → DUPLICADO + Préstamo APROBADO + cédula."""
    from app.services.auditoria_email.receipts_service import (
        enrich_recibos_sin_cedula_via_serial,
    )

    items = [
        {
            "id": 1,
            "cedula": None,
            "banco": "Mercantil",
            "serialRaw": DIGITS_MERC,
            "serialCanon": DIGITS_MERC,
            "serialEstado": "UNICO",
            "prestamoEstados": [],
            "prestamoEstado": None,
        }
    ]
    db = MagicMock()
    with patch(
        "app.services.auditoria_email.receipts_service._cartera_info_por_serial",
        return_value={
            "norm": DIGITS_MERC,
            "duplicado": True,
            "cedula": "V12345678",
            "prestamoEstados": ["APROBADO"],
            "prestamoIds": [99],
        },
    ):
        enrich_recibos_sin_cedula_via_serial(db, items)
    assert items[0]["serialEstado"] == "DUPLICADO"
    assert items[0]["cedula"] == "V12345678"
    assert items[0]["cedulaDesdeSerial"] is True
    assert items[0]["prestamoEstado"] == "APROBADO"
    assert items[0]["prestamoEstados"] == ["APROBADO"]


def test_enrich_sin_cedula_liquidado_no_rellena_prestamo():
    """Serial en LIQUIDADO/DESISTIMIENTO → DUPLICADO sí; Préstamo/cédula no."""
    from app.services.auditoria_email.receipts_service import (
        enrich_recibos_sin_cedula_via_serial,
    )

    items = [
        {
            "id": 3,
            "cedula": None,
            "banco": "Mercantil",
            "serialRaw": DIGITS_MERC,
            "serialCanon": DIGITS_MERC,
            "serialEstado": "UNICO",
            "prestamoEstados": [],
            "prestamoEstado": None,
        }
    ]
    db = MagicMock()
    with patch(
        "app.services.auditoria_email.receipts_service._cartera_info_por_serial",
        return_value={
            "norm": DIGITS_MERC,
            "duplicado": True,
            "cedula": None,
            "prestamoEstados": [],
            "prestamoIds": [],
        },
    ):
        enrich_recibos_sin_cedula_via_serial(db, items)
    assert items[0]["serialEstado"] == "DUPLICADO"
    assert not items[0].get("cedula")
    assert items[0].get("prestamoEstados") == []
    assert items[0].get("prestamoEstado") is None


def test_liquidado_no_es_aprobado_activo_recibos():
    """V21025186 LIQUIDADO (terminado/revisión) nunca cuenta como APROBADO."""
    from app.services.prestamos.cedula_aprobada import (
        prestamo_estado_es_aprobado_activo_recibos,
    )

    assert prestamo_estado_es_aprobado_activo_recibos("APROBADO") is True
    assert prestamo_estado_es_aprobado_activo_recibos("liquidado") is False
    assert prestamo_estado_es_aprobado_activo_recibos("LIQUIDADO") is False
    assert prestamo_estado_es_aprobado_activo_recibos("DESISTIMIENTO") is False
    assert prestamo_estado_es_aprobado_activo_recibos("TERMINADO") is False
    assert prestamo_estado_es_aprobado_activo_recibos("REVISION") is False


def test_liquidado_cualquier_finiquito_sin_cupo():
    from app.services.prestamos.cedula_aprobada import (
        prestamo_estado_es_liquidado_cartera,
        prestamo_sin_cupo_para_recibos,
    )

    db = MagicMock()
    assert prestamo_estado_es_liquidado_cartera("LIQUIDADO") is True
    assert prestamo_estado_es_liquidado_cartera("liquidado") is True
    with patch(
        "app.services.prestamos.cedula_aprobada.saldo_pendiente_prestamo_ui_recibos",
        return_value=0.0,
    ):
        assert prestamo_sin_cupo_para_recibos(db, 230, "LIQUIDADO") is True
        assert prestamo_sin_cupo_para_recibos(db, 1, "APROBADO") is True
    with patch(
        "app.services.prestamos.cedula_aprobada.saldo_pendiente_prestamo_ui_recibos",
        return_value=50.0,
    ):
        assert prestamo_sin_cupo_para_recibos(db, 2, "APROBADO") is False


def test_cedula_liquidada_debe_omitirse_lista_recibos():
    from app.services.prestamos.cedula_aprobada import (
        cedula_debe_omitirse_lista_recibos,
    )

    db = MagicMock()
    with patch(
        "app.services.prestamos.cedula_aprobada.claves_deben_omitirse_lista_recibos",
        return_value={"V21025186"},
    ):
        assert cedula_debe_omitirse_lista_recibos(db, "V21025186") is True

    with patch(
        "app.services.prestamos.cedula_aprobada.claves_deben_omitirse_lista_recibos",
        return_value=set(),
    ):
        assert cedula_debe_omitirse_lista_recibos(db, "V123") is False


def test_claves_deben_omitirse_es_cartera_sin_cupo():
    from app.services.prestamos.cedula_aprobada import (
        claves_deben_omitirse_lista_recibos,
    )

    db = MagicMock()
    with patch(
        "app.services.prestamos.cedula_aprobada.claves_con_prestamo_aprobado_operativo_recibos",
        return_value={"OK1"},
    ), patch(
        "app.services.prestamos.cedula_aprobada.claves_con_prestamo_en_cartera",
        return_value={"OK1", "LIQ1"},
    ):
        assert claves_deben_omitirse_lista_recibos(db, ["OK1", "LIQ1", "MISS"]) == {
            "LIQ1"
        }


def test_recibo_debe_omitir_lista_por_cedula():
    from app.services.auditoria_email.receipts_service import _recibo_debe_omitir_lista

    row = SimpleNamespace(
        cedula="V21025186",
        numero_referencia=None,
        banco=None,
        pago_id=None,
        pago_error_id=None,
    )
    db = MagicMock()
    with patch(
        "app.services.prestamos.cedula_aprobada.cedula_debe_omitirse_lista_recibos",
        return_value=True,
    ):
        assert _recibo_debe_omitir_lista(db, row) is True


def test_recibo_debe_omitir_lista_por_serial_en_bd():
    """Serial ya en pagos/pagos_con_errores → omitir (aunque cédula tenga APROBADO)."""
    from app.services.auditoria_email.receipts_service import _recibo_debe_omitir_lista

    row = SimpleNamespace(
        id=9,
        cedula="V123",
        numero_referencia="740012345678",
        banco="BNC",
        pago_id=None,
        pago_error_id=None,
    )
    db = MagicMock()
    with patch(
        "app.services.auditoria_email.receipts_service._serial_duplicado_cartera_real",
        return_value=True,
    ):
        assert _recibo_debe_omitir_lista(db, row) is True


def test_recibo_no_omite_sin_serial_ni_liquidado():
    from app.services.auditoria_email.receipts_service import _recibo_debe_omitir_lista

    row = SimpleNamespace(
        cedula="V123",
        numero_referencia=None,
        banco=None,
        pago_id=None,
        pago_error_id=None,
    )
    db = MagicMock()
    with patch(
        "app.services.auditoria_email.receipts_service._serial_duplicado_cartera_real",
        return_value=False,
    ), patch(
        "app.services.prestamos.cedula_aprobada.cedula_debe_omitirse_lista_recibos",
        return_value=False,
    ):
        assert _recibo_debe_omitir_lista(db, row) is False


def test_aprobado_sin_saldo_no_es_operativo_recibos():
    """APROBADO con $0 pendiente (Pagado) no pasa OK / columna Préstamo."""
    from app.services.prestamos.cedula_aprobada import (
        prestamo_aprobado_operativo_recibos,
        prestamo_ids_aprobados_con_cupo_recibos,
    )

    db = MagicMock()
    q = MagicMock()
    q.all.return_value = [(42,)]
    db.execute.return_value = q
    with patch(
        "app.services.notificacion_service.sum_saldo_pendiente_cuotas_tabla_amortizacion_ui",
        return_value={42: 0.0},
    ):
        assert prestamo_ids_aprobados_con_cupo_recibos(db, [42]) == set()
        assert prestamo_aprobado_operativo_recibos(db, 42) is False

    with patch(
        "app.services.notificacion_service.sum_saldo_pendiente_cuotas_tabla_amortizacion_ui",
        return_value={42: 15.5},
    ):
        assert prestamo_ids_aprobados_con_cupo_recibos(db, [42]) == {42}
        assert prestamo_aprobado_operativo_recibos(db, 42) is True


def test_enrich_sin_cedula_no_pisa_cedula_existente():
    from app.services.auditoria_email.receipts_service import (
        enrich_recibos_sin_cedula_via_serial,
    )

    items = [
        {
            "id": 2,
            "cedula": "V999",
            "banco": "BNC",
            "serialRaw": DIGITS,
            "serialEstado": "UNICO",
        }
    ]
    db = MagicMock()
    with patch(
        "app.services.auditoria_email.receipts_service._cartera_info_por_serial"
    ) as mock_info:
        enrich_recibos_sin_cedula_via_serial(db, items)
        mock_info.assert_not_called()
    assert items[0]["cedula"] == "V999"
