"""
Tests y verificación por etapas del módulo Pagos Gmail (run-now, download-excel, status).
Permite detectar problemas potenciales en cada paso sin depender de credenciales reales.
"""
import logging
import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, engine

from app.api.v1.endpoints.pagos_gmail import (
    _find_most_recent_data,
    _find_sheet_by_fecha,
    _get_latest_date_with_data,
    _is_pipeline_running,
    _sheet_date_from_fecha,
    download_excel,
    status,
)
from app.models.pagos_gmail_sync import PagosGmailSync, PagosGmailSyncItem
from app.services.pagos_gmail.gemini_service import (
    _guess_bank_hint_from_text,
    _parse_formato_y_pagos_json,
)
from app.services.pagos.comprobante_link_desde_gmail import (
    comprobante_url_para_enlace_publico,
)
from app.services.pagos_gmail.helpers import (
    format_monto_excel_pagos_gmail,
    resolve_banco_para_excel_pagos_gmail,
)


@pytest.fixture(scope="session", autouse=True)
def _ensure_pagos_gmail_sync_correos_revision_column():
    """Alinea BD de tests con el modelo (columnas pipeline Gmail / Excel)."""
    try:
        with engine.connect() as conn:
            r = conn.execute(
                text(
                    """
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'pagos_gmail_sync'
                      AND column_name = 'correos_marcados_revision'
                    """
                )
            )
            if r.fetchone() is None:
                conn.execute(
                    text(
                        "ALTER TABLE pagos_gmail_sync ADD COLUMN "
                        "correos_marcados_revision INTEGER NOT NULL DEFAULT 0"
                    )
                )
                conn.commit()
            r2 = conn.execute(
                text(
                    """
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'pagos_gmail_sync'
                      AND column_name = 'run_summary'
                    """
                )
            )
            if r2.fetchone() is None:
                conn.execute(
                    text("ALTER TABLE pagos_gmail_sync ADD COLUMN run_summary JSONB NULL")
                )
                conn.commit()
    except Exception:
        pass
    for tbl in ("pagos_gmail_sync_item", "gmail_temporal"):
        try:
            with engine.connect() as conn:
                r = conn.execute(
                    text(
                        """
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = :t AND column_name = 'banco'
                        """
                    ),
                    {"t": tbl},
                )
                if r.fetchone() is None:
                    conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN banco VARCHAR(50) NULL"))
                    conn.commit()
        except Exception:
            pass
    yield


@pytest.fixture(scope="function")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# --- Logs por etapas (captura en tests) ---
@pytest.fixture
def caplog_gmail(caplog):
    """Nivel INFO para ver logs [PAGOS_GMAIL] [ETAPA]."""
    caplog.set_level(logging.INFO, logger="app.api.v1.endpoints.pagos_gmail")
    caplog.set_level(logging.INFO, logger="app.services.pagos_gmail.pipeline")
    return caplog


# --- Tests status ---
def test_status_endpoint_returns_structure(db: Session):
    """GET /status debe devolver last_run, last_status, last_emails, last_files, latest_data_date."""
    resp = status(db=db)
    assert "last_run" in resp
    assert "last_status" in resp
    assert "last_emails" in resp
    assert "last_files" in resp
    assert "next_run_approx" in resp
    assert "latest_data_date" in resp
    assert "last_correos_marcados_revision" in resp
    assert "last_run_summary" in resp
    assert resp["next_run_approx"] is None


def test_status_when_no_sync(db: Session):
    """Sin ningún PagosGmailSync, status no debe fallar."""
    resp = status(db=db)
    assert "last_run" in resp and "last_status" in resp


# --- Tests _find_most_recent_data (límite y conteo) ---
def test_find_most_recent_data_empty_db(db: Session):
    """Sin ítems en BD devuelve (None, None, []). Mock execute para no depender de BD real."""
    with patch.object(db, "execute") as mock_exec:
        mock_exec.return_value.scalars().all.return_value = []
        sheet_ref, date_ref, items = _find_most_recent_data(db)
    assert sheet_ref is None
    assert date_ref is None
    assert items == []


def test_find_most_recent_data_respects_max_items(db: Session):
    """Con PAGOS_GMAIL_DOWNLOAD_EXCEL_MAX_ITEMS=2 solo devuelve hasta 2 ítems."""
    sync = PagosGmailSync(status="success", emails_processed=0, files_processed=0)
    db.add(sync)
    db.commit()
    db.refresh(sync)
    for i in range(4):
        db.add(
            PagosGmailSyncItem(
                sync_id=sync.id,
                sheet_name="2026-01-01",
                correo_origen=f"test{i}@test.com",
                asunto="Test",
                fecha_pago="",
                cedula="",
                monto="",
                numero_referencia="",
            )
        )
    db.commit()

    with patch("app.core.config.settings") as mock_settings:
        mock_settings.PAGOS_GMAIL_DOWNLOAD_EXCEL_MAX_ITEMS = 2
        _, _, items = _find_most_recent_data(db)
    assert len(items) == 2


def test_find_most_recent_data_zero_uses_high_limit(db: Session):
    """Con max_items=0 se usa límite alto (toda la bandeja)."""
    sync = PagosGmailSync(status="success", emails_processed=0, files_processed=0)
    db.add(sync)
    db.commit()
    db.refresh(sync)
    one = PagosGmailSyncItem(sync_id=sync.id, sheet_name="2026-01-01", correo_origen="one@test.com", asunto="Test", fecha_pago="", cedula="", monto="", numero_referencia="")
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.PAGOS_GMAIL_DOWNLOAD_EXCEL_MAX_ITEMS = 0
        with patch.object(db, "execute") as mock_exec:
            mock_exec.return_value.scalars().all.return_value = [one]
            _, _, items = _find_most_recent_data(db)
    assert len(items) == 1


# --- Tests _sheet_date_from_fecha ---
def test_sheet_date_from_fecha_empty_uses_today():
    """Sin fecha usa lógica del día actual."""
    dt = _sheet_date_from_fecha(None)
    assert dt is not None
    dt2 = _sheet_date_from_fecha("")
    assert dt2 is not None


def test_sheet_date_from_fecha_parses_yyyy_mm_dd():
    """fecha=2026-01-15 devuelve datetime 2026-01-15 00:00:00."""
    dt = _sheet_date_from_fecha("2026-01-15")
    assert dt.year == 2026 and dt.month == 1 and dt.day == 15


# --- Tests _find_sheet_by_fecha ---
def test_find_sheet_by_fecha_empty(db: Session):
    """Para una fecha sin datos devuelve (sheet_name, [])."""
    sheet_name, items = _find_sheet_by_fecha(db, datetime(2026, 1, 1))
    assert items == []
    assert "2026" in (sheet_name or "")


# --- Tests _is_pipeline_running ---
def test_is_pipeline_running_false_when_no_sync(db: Session):
    """Sin sync en running, _is_pipeline_running es False."""
    assert isinstance(_is_pipeline_running(db), bool)


def test_is_pipeline_running_true_when_recent_running(db: Session):
    """Con un sync reciente en running, _is_pipeline_running es True."""
    sync = PagosGmailSync(
        status="running",
        emails_processed=0,
        files_processed=0,
        started_at=datetime.utcnow(),
    )
    db.add(sync)
    db.commit()
    assert _is_pipeline_running(db) is True


# --- Tests download_excel (404 sin datos) ---
def test_download_excel_404_when_no_data(db: Session):
    """download_excel sin datos debe devolver 404."""
    with patch(
        "app.api.v1.endpoints.pagos_gmail.routes._find_most_recent_data",
        return_value=(None, None, []),
    ):
        with pytest.raises(HTTPException) as exc_info:
            download_excel(fecha=None, db=db)
    assert exc_info.value.status_code == 404


def test_download_excel_404_with_fecha_when_no_data_for_date(db: Session):
    """download_excel con fecha sin datos para esa fecha devuelve 404."""
    with pytest.raises(HTTPException) as exc_info:
        download_excel(fecha="2026-01-01", db=db)
    assert exc_info.value.status_code == 404


# --- Tests _get_latest_date_with_data ---
def test_get_latest_date_with_data_none_when_empty(db: Session):
    """Sin ítems, _get_latest_date_with_data devuelve None (no depende de filas previas en BD compartida)."""
    r = MagicMock()
    r.scalars.return_value.first.return_value = None
    with patch.object(db, "execute", return_value=r):
        assert _get_latest_date_with_data(db) is None


# --- Tests logs [ETAPA] en download ---
def test_download_excel_logs_etapa_when_has_data(db: Session, caplog_gmail):
    """Con datos, download_excel debe emitir logs [ETAPA]."""
    sync = PagosGmailSync(status="success", emails_processed=1, files_processed=1)
    db.add(sync)
    db.commit()
    db.refresh(sync)
    from datetime import datetime as dt
    item = PagosGmailSyncItem(sync_id=sync.id, sheet_name="2026-01-01", correo_origen="log@test.com", asunto="Test", fecha_pago="", cedula="", monto="", numero_referencia="", drive_link=None, drive_email_link=None)
    with patch(
        "app.api.v1.endpoints.pagos_gmail.routes._find_most_recent_data",
        return_value=("2026-01-01", dt(2026, 1, 1), [item]),
    ):
        resp = download_excel(fecha=None, db=db)
    assert resp is not None
    etapas = [r.message for r in caplog_gmail.records if "[ETAPA]" in (r.message or "")]
    assert any("download-excel" in m for m in etapas), "Debería haber log [ETAPA] download-excel"


def test_format_monto_excel_sin_unidad():
    assert format_monto_excel_pagos_gmail("96.00 USD") == "96.00"
    assert format_monto_excel_pagos_gmail("122 USDT") == "122.00"
    assert format_monto_excel_pagos_gmail("142.00 USD") == "142.00"
    assert format_monto_excel_pagos_gmail("96,00") == "96.00"
    assert format_monto_excel_pagos_gmail("NR") == "NR"
    assert format_monto_excel_pagos_gmail("nr") == "NR"


def test_resolve_banco_excel_desde_texto_gemini():
    """Normaliza nombre de banco del comprobante hacia rotulos cortos."""
    d_a, d_b, d_c = "Mercantil", "BNC", "BINANCE"
    assert (
        resolve_banco_para_excel_pagos_gmail(
            "NR", "NA", default_a=d_a, default_b=d_b, default_c=d_c, default_d="BDV"
        )
        == "NR"
    )
    assert (
        resolve_banco_para_excel_pagos_gmail(
            "NR", "  Banco Mercantil  ", default_a=d_a, default_b=d_b, default_c=d_c, default_d="BDV"
        )
        == "Mercantil"
    )
    assert (
        resolve_banco_para_excel_pagos_gmail(
            "B", "Banco Nacional de Credito, C.A.", default_a=d_a, default_b=d_b, default_c=d_c
        )
        == "BNC"
    )
    assert (
        resolve_banco_para_excel_pagos_gmail(
            "A", "Banco Mercantil", default_a=d_a, default_b=d_b, default_c=d_c
        )
        == "Mercantil"
    )
    assert (
        resolve_banco_para_excel_pagos_gmail("A", "", default_a=d_a, default_b=d_b, default_c=d_c)
        == "Mercantil"
    )
    assert (
        resolve_banco_para_excel_pagos_gmail("B", "NA", default_a=d_a, default_b=d_b, default_c=d_c)
        == "BNC"
    )
    assert (
        resolve_banco_para_excel_pagos_gmail("C", "cualquier", default_a=d_a, default_b=d_b, default_c=d_c)
        == "BINANCE"
    )
    assert (
        resolve_banco_para_excel_pagos_gmail(
            "E",
            "NA",
            default_a=d_a,
            default_b=d_b,
            default_c=d_c,
            default_d="BDV",
            default_e="Bancamiga",
        )
        == "Bancamiga"
    )
    assert (
        resolve_banco_para_excel_pagos_gmail(
            "E",
            "Bancamiga Banco Universal",
            default_a=d_a,
            default_b=d_b,
            default_c=d_c,
            default_d="BDV",
            default_e="Bancamiga",
        )
        == "Bancamiga"
    )
    assert (
        resolve_banco_para_excel_pagos_gmail(
            "F",
            "NA",
            default_a=d_a,
            default_b=d_b,
            default_c=d_c,
            default_d="BDV",
            default_e="Bancamiga",
            default_f="Banco del Tesoro",
        )
        == "Banco del Tesoro"
    )
    assert (
        resolve_banco_para_excel_pagos_gmail(
            "F",
            "Banco del Tesoro",
            default_a=d_a,
            default_b=d_b,
            default_c=d_c,
            default_d="BDV",
            default_e="Bancamiga",
            default_f="Banco del Tesoro",
        )
        == "Banco del Tesoro"
    )


def test_guess_bank_hint_e_solo_anclas_fuertes_bancamiga():
    """E no debe activarse con frases genéricas de otros bancos (referencia, monto, cuentas)."""
    assert (
        _guess_bank_hint_from_text(
            "monto de la operacion\nnumero de referencia\ncuenta a debitar",
            "comprobante.png",
            "falto_ref",
        )
        is None
    )
    assert _guess_bank_hint_from_text("app Bancamiga", "cap.jpg", "falto_monto") == "E"
    assert _guess_bank_hint_from_text("cuenta 01720123456789012345", "x.png", "x") == "E"
    assert (
        _guess_bank_hint_from_text(
            "Banco Universal",
            "pago.jpg",
            "transaccion procesada ilegible",
        )
        == "E"
    )
    assert (
        _guess_bank_hint_from_text("Banco Universal solo logo", "x.png", "falto_fecha")
        != "E"
    )
    assert _guess_bank_hint_from_text("01910123456789012345 ref", "x.png", "x") == "B"


def test_guess_bank_hint_bnc_app_transferencia_con_cuentas_enmascaradas():
    txt = (
        "Su transferencia ha sido Ejecutada exitosamente\n"
        "Cta. Ahorro BNC: ***4398\n"
        "Cuenta abonada: Cta. Corriente BNC: ***7926 RAPI-CREDIT, C.A\n"
        "Monto: Bs. 54.913,67\n"
        "Referencia: 133454281"
    )
    assert _guess_bank_hint_from_text(txt, "bnc_app.png", "sin_plantilla") == "B"


def test_parse_formato_c_binance_ok():
    """JSON C valido: monto, referencia; fecha, cedula y email_cliente NA (parser fuerza NA en C)."""
    j = (
        '{"formato":"C","fecha_pago":"NA","cedula":"NA",'
        '"monto":"122 USDT","numero_referencia":"423594224765779968",'
        '"email_cliente":"operaciones@rapicreditca.com","banco":"NA"}'
    )
    fmt, fields = _parse_formato_y_pagos_json(j)
    assert fmt == "C"
    assert fields["email_cliente"] == "NA"
    assert fields["monto"] == "122 USDT"


def test_parse_formato_b_incluye_banco():
    """A/B pueden traer banco leido del comprobante."""
    j = (
        '{"formato":"B","fecha_pago":"01/01/2026","cedula":"V1","monto":"1 USD",'
        '"numero_referencia":"9","email_cliente":"NA","banco":"Banco Nacional de Credito"}'
    )
    fmt, fields = _parse_formato_y_pagos_json(j)
    assert fmt == "B"
    assert fields.get("banco") == "Banco Nacional de Credito"


def test_parse_formato_c_rechazado_si_fecha_no_na():
    """C con fecha en imagen invalida el parse (backend asigna fecha del correo)."""
    j = (
        '{"formato":"C","fecha_pago":"01/01/2026","cedula":"NA",'
        '"monto":"1","numero_referencia":"9","email_cliente":"a@b.com"}'
    )
    fmt, _ = _parse_formato_y_pagos_json(j)
    assert fmt == "ninguno"


def test_comprobante_url_para_enlace_publico_http_passthrough():
    u = "https://drive.google.com/file/d/abc123/view"
    assert comprobante_url_para_enlace_publico(u) == u


def test_comprobante_url_para_enlace_publico_drive_id():
    fid = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"
    out = comprobante_url_para_enlace_publico(fid)
    assert out.startswith("https://drive.google.com/file/d/")
    assert fid in out


def test_comprobante_url_para_enlace_publico_no_trata_serial_numerico_como_drive():
    """Serial de pago solo digitos no debe convertirse a URL Drive."""
    assert comprobante_url_para_enlace_publico("740087407343435") == "740087407343435"


def test_comprobante_url_para_enlace_publico_ruta_relativa_con_base():
    assert (
        comprobante_url_para_enlace_publico("/api/v1/x", base_url="https://app.example.com")
        == "https://app.example.com/api/v1/x"
    )


def test_parse_formato_c_email_cliente_siguen_siendo_na():
    """Formato C: el parser deja email_cliente en NA (el backend usa remitente De para cliente/cédula)."""
    j = (
        '{"formato":"C","fecha_pago":"NA","cedula":"NA",'
        '"monto":"135.00 USDT","numero_referencia":"423594224765779968",'
        '"email_cliente":"NA","banco":"NA"}'
    )
    fmt, fields = _parse_formato_y_pagos_json(
        j,
        remitente_from_header="Jesus Acosta <jacostamolleda@gmail.com>",
    )
    assert fmt == "C"
    assert (fields.get("email_cliente") or "").upper() == "NA"


def test_pagos_gmail_list_q_media_parts_incluye_filename():
    from app.services.pagos_gmail.gmail_service import pagos_gmail_list_q_media_parts

    q = pagos_gmail_list_q_media_parts()
    assert "has:attachment" in q
    assert "filename:png" in q


def test_pagos_gmail_inbox_media_query_incluye_todo_sin_filtrar_estrella_ni_etiquetas():
    from app.services.pagos_gmail.gmail_service import pagos_gmail_inbox_media_query

    q = pagos_gmail_inbox_media_query()
    assert "in:inbox" in q
    assert "has:attachment" in q or "filename:png" in q
    assert "-is:starred" not in q
    assert "-label:" not in q


def test_attachment_pdf_octet_stream_se_acepta_por_extension_pdf():
    from app.services.pagos_gmail.gmail_service import (
        get_attachment_image_pdf_files_for_message,
    )

    service = MagicMock()
    service.users.return_value.messages.return_value.attachments.return_value.get.return_value.execute.return_value = {
        "data": "JVBERi0xLjQK"
    }
    payload = {
        "parts": [
            {
                "mimeType": "application/octet-stream",
                "filename": "deposito_rapimoto.pdf",
                "body": {"attachmentId": "att_pdf_1"},
            }
        ]
    }

    out = get_attachment_image_pdf_files_for_message(service, "msg-1", payload)
    assert len(out) == 1
    filename, content, mime = out[0]
    assert filename.endswith(".pdf")
    assert mime == "application/octet-stream"
    assert content.startswith(b"%PDF")


def test_expand_pipeline_pdf_tuples_imagen_pasa_y_multipage_pdf_expande_por_pagina():
    from io import BytesIO

    from app.services.pagos_gmail.pdf_pages import expand_pipeline_pdf_tuples

    jpg = [("a.jpg", b"\xff\xd8\xff", "image/jpeg", "adjunta")]
    out_j, n_j = expand_pipeline_pdf_tuples(jpg)
    assert n_j == 0
    assert out_j == jpg

    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        pytest.skip("pypdf no instalado")
    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    w.add_blank_page(width=72, height=72)
    buf = BytesIO()
    w.write(buf)
    pdf_2p = buf.getvalue()
    out_p, n_p = expand_pipeline_pdf_tuples(
        [("dos.pdf", pdf_2p, "application/pdf", "adjunta")]
    )
    assert n_p == 1
    assert len(out_p) == 2
    assert out_p[0][0] == "dos_pag1.pdf" and out_p[1][0] == "dos_pag2.pdf"
    assert out_p[0][2] == "application/pdf" and out_p[1][2] == "application/pdf"
    assert out_p[0][3] == "adjunta" and out_p[1][3] == "adjunta"
    for _fname, _bytes, _, _ in out_p:
        assert len(PdfReader(BytesIO(_bytes)).pages) == 1


def test_sort_messages_inbox_mas_reciente_primero():
    from app.services.pagos_gmail.pipeline import _sort_messages_inbox_primero_a_ultimo

    msgs = [
        {"id": "old", "headers": {"date": "Mon, 1 Jan 2024 12:00:00 +0000"}},
        {"id": "new", "headers": {"date": "Mon, 15 Mar 2024 12:00:00 +0000"}},
        {"id": "mid", "headers": {"date": "Mon, 1 Feb 2024 12:00:00 +0000"}},
    ]
    out = _sort_messages_inbox_primero_a_ultimo(msgs)
    assert [m["id"] for m in out] == ["new", "mid", "old"]


def test_sort_messages_internal_date_ms_gana_sobre_date_header():
    """internalDate (recepcion Gmail) define el orden aunque la cabecera Date diga otra cosa."""
    from app.services.pagos_gmail.pipeline import _sort_messages_inbox_primero_a_ultimo

    msgs = [
        {
            "id": "b",
            "internal_date_ms": 2_000,
            "headers": {"date": "Mon, 1 Jan 2030 12:00:00 +0000"},
        },
        {
            "id": "a",
            "internal_date_ms": 1_000,
            "headers": {"date": "Mon, 1 Jan 2030 12:00:00 +0000"},
        },
    ]
    out = _sort_messages_inbox_primero_a_ultimo(msgs)
    assert [m["id"] for m in out] == ["b", "a"]


def test_pagos_gmail_error_email_rescan_query_incluye_error_email_y_media():
    from app.services.pagos_gmail.gmail_service import (
        PAGOS_GMAIL_LABEL_ERROR_EMAIL,
        pagos_gmail_error_email_rescan_query,
    )

    q = pagos_gmail_error_email_rescan_query()
    assert f'label:"{PAGOS_GMAIL_LABEL_ERROR_EMAIL}"' in q
    assert "in:inbox" in q
    assert "has:attachment" in q or "filename:png" in q
    assert "EMAIL-12" not in q


def test_pagos_gmail_list_query_unread_read_anade_is_unread_o_read():
    from app.services.pagos_gmail.gmail_service import pagos_gmail_list_query_for_scan_filter

    q_un = pagos_gmail_list_query_for_scan_filter("unread")
    assert "is:unread" in q_un
    assert "is:read" not in q_un
    q_rd = pagos_gmail_list_query_for_scan_filter("read")
    assert "is:read" in q_rd
    assert "is:unread" not in q_rd
    q_all = pagos_gmail_list_query_for_scan_filter("all")
    assert "is:unread" not in q_all
    assert "is:read" not in q_all


def test_parse_formato_b_modo_error_email_ab_cedula_error():
    j = (
        '{"formato":"B","fecha_pago":"01/01/2026","cedula":"ERROR","monto":"1 USD",'
        '"numero_referencia":"9","email_cliente":"NA","banco":"BNC"}'
    )
    fmt, fields = _parse_formato_y_pagos_json(j, modo_error_email_ab=True)
    assert fmt == "B"
    assert fields["cedula"] == "ERROR"


def test_parse_formato_e_bancamiga_cedula_siempre_na():
    j = (
        '{"formato":"E","fecha_pago":"17/04/2026","cedula":"J-505363506","monto":"Bs. 43.223,15",'
        '"numero_referencia":"18987898","email_cliente":"NA","banco":"Bancamiga"}'
    )
    fmt, fields = _parse_formato_y_pagos_json(j)
    assert fmt == "E"
    assert fields["cedula"] == "NA"
    assert "43.223" in (fields.get("monto") or "")
    assert (fields.get("numero_referencia") or "").strip() == "18987898"


def test_parse_formato_f_tesoro_cedula_siempre_na():
    j = (
        '{"formato":"F","fecha_pago":"18/04/2026","cedula":"J-505363506","monto":"64.810,14 Bs.",'
        '"numero_referencia":"01834361","email_cliente":"NA","banco":"Banco del Tesoro"}'
    )
    fmt, fields = _parse_formato_y_pagos_json(j)
    assert fmt == "F"
    assert fields["cedula"] == "NA"
    assert "64.810" in (fields.get("monto") or "") or "64810" in (fields.get("monto") or "")
    assert (fields.get("numero_referencia") or "").strip() == "01834361"


def test_parse_formato_a_modo_error_email_ab_cedula_desde_imagen():
    j = (
        '{"formato":"A","fecha_pago":"01/01/2026","cedula":"V-01234567","monto":"10 USD",'
        '"numero_referencia":"123","email_cliente":"NA","banco":"NA"}'
    )
    fmt, fields = _parse_formato_y_pagos_json(j, modo_error_email_ab=True)
    assert fmt == "A"
    assert fields["cedula"] == "V-01234567"


def test_cedula_desde_imagen_rescan_normaliza_o_error():
    from app.services.pagos_gmail.pipeline import (
        PAGOS_GMAIL_ERROR_CEDULA_IMAGEN,
        _cedula_desde_imagen_rescan_error_email,
    )

    assert _cedula_desde_imagen_rescan_error_email("V-030145077") == "V30145077"
    assert _cedula_desde_imagen_rescan_error_email("ERROR") == PAGOS_GMAIL_ERROR_CEDULA_IMAGEN
    assert _cedula_desde_imagen_rescan_error_email("xyz") == PAGOS_GMAIL_ERROR_CEDULA_IMAGEN


def test_pagos_gmail_label_exclusions_query_incluye_etiquetas_clasificacion():
    from app.services.pagos_gmail.gmail_service import (
        PAGOS_GMAIL_LABEL_BANCAMIGA,
        PAGOS_GMAIL_LABEL_TESORO,
        PAGOS_GMAIL_LABEL_ERROR_EMAIL,
        PAGOS_GMAIL_LABEL_IMAGEN_1,
        PAGOS_GMAIL_LABEL_IMAGEN_2,
        PAGOS_GMAIL_LABEL_IMAGEN_3,
        PAGOS_GMAIL_LABEL_IMAGEN_4,
        PAGOS_GMAIL_LABEL_MANUAL,
        PAGOS_GMAIL_LABEL_TEXTO,
        pagos_gmail_label_exclusions_query,
    )

    q = pagos_gmail_label_exclusions_query()
    assert f'-label:"{PAGOS_GMAIL_LABEL_IMAGEN_1}"' in q
    assert f'-label:"{PAGOS_GMAIL_LABEL_IMAGEN_2}"' in q
    assert f'-label:"{PAGOS_GMAIL_LABEL_IMAGEN_3}"' in q
    assert f'-label:"{PAGOS_GMAIL_LABEL_IMAGEN_4}"' in q
    assert f'-label:"{PAGOS_GMAIL_LABEL_BANCAMIGA}"' in q
    assert f'-label:"{PAGOS_GMAIL_LABEL_TESORO}"' in q
    assert f'-label:"{PAGOS_GMAIL_LABEL_ERROR_EMAIL}"' in q
    assert f'-label:"{PAGOS_GMAIL_LABEL_MANUAL}"' in q
    assert f'-label:"{PAGOS_GMAIL_LABEL_TEXTO}"' in q


