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
        "app.services.pago_numero_documento.numero_documento_ya_registrado",
        return_value=True,
    ), patch(
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

    assert _es_asiento_banco_drive("Drive", DIGITS) is True
    assert _es_asiento_banco_drive("BANCO/DRIVE", DIGITS) is True
    assert _es_asiento_banco_drive("BNC", DIGITS) is False
    assert _es_asiento_banco_drive("Mercantil", DIGITS) is False

    db = MagicMock()
    with patch(
        "app.services.pago_numero_documento.numero_documento_ya_registrado",
        return_value=True,
    ), patch(
        "app.services.auditoria_email.receipts_service._listar_hits_numero_documento",
        return_value=[("pagos", 1, DIGITS, "Drive")],
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
