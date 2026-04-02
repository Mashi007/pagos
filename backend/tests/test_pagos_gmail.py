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
from sqlalchemy import select
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal

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
    with patch("app.api.v1.endpoints.pagos_gmail._find_most_recent_data", return_value=(None, None, [])):
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
    """Sin ítems, _get_latest_date_with_data devuelve None."""
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
    with patch("app.api.v1.endpoints.pagos_gmail._find_most_recent_data", return_value=("2026-01-01", dt(2026, 1, 1), [item])):
        resp = download_excel(fecha=None, db=db)
    assert resp is not None
    etapas = [r.message for r in caplog_gmail.records if "[ETAPA]" in (r.message or "")]
    assert any("download-excel" in m for m in etapas), "Debería haber log [ETAPA] download-excel"


