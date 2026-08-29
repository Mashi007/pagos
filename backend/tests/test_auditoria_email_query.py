# -*- coding: utf-8 -*-
"""Filtros fuertes Auditoría Email."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.auditoria_email.demo import filter_demo
from app.services.auditoria_email.query import (
    analizados_label_name,
    build_gmail_query,
    has_date_bound,
    matches_criteria,
)


def test_batch_requires_date_bound():
    assert not has_date_bound({})
    assert has_date_bound({"newerThanDays": 7})
    assert has_date_bound({"dateFrom": "2026-01-01"})


def test_build_query_includes_attachment_newer_sin_excluir_etiquetas():
    q = build_gmail_query(
        {"preset": "ultimos-7", "attachments": "pdf_only", "newerThanDays": 7}
    )
    assert "newer_than:7d" in q
    assert "filename:pdf" in q
    assert "has:attachment" in q
    assert f"-label:{analizados_label_name()}" not in q


def test_build_query_pdf_or_image_igual_pagos_gmail():
    from app.services.pagos_gmail.gmail_service import pagos_gmail_list_q_media_parts

    q = build_gmail_query(
        {"attachments": "pdf_or_image", "newerThanDays": 7}
    )
    media = pagos_gmail_list_q_media_parts()
    assert media in q
    assert "newer_than:7d" in q
    assert "filename:eml" in q
    assert "filename:heic" in q


def test_build_query_pagos_gmail_mode():
    from app.services.pagos_gmail.gmail_service import pagos_gmail_list_q_media_parts

    q = build_gmail_query({"attachments": "pagos_gmail", "newerThanDays": 30})
    assert pagos_gmail_list_q_media_parts() in q
    assert f"-label:{analizados_label_name()}" not in q


def test_build_query_exclude_analizados_opcional():
    q = build_gmail_query(
        {
            "preset": "ultimos-7",
            "attachments": "pdf_only",
            "newerThanDays": 7,
            "excludeAnalizados": True,
        }
    )
    assert f"-label:{analizados_label_name()}" in q


def test_soft_postfilter_trusts_gmail_when_no_filenames():
    row = {
        "subject": "pago",
        "from_email": "a@b.com",
        "has_attachment": True,
        "attachment_types": [],
        "filename_joined": "",
        "attachment_max_kb": 0,
    }
    assert matches_criteria(
        row,
        {"attachments": "pdf_or_image"},
        trust_gmail_attachment_q=True,
    )
    assert not matches_criteria(
        row,
        {"attachments": "pdf_or_image"},
        trust_gmail_attachment_q=False,
    )


def test_demo_estimate_respects_criteria():
    all_rows = filter_demo({})
    assert len(all_rows) == 320
    only_pdfish = filter_demo({"attachments": "pdf_only"})
    assert 0 < len(only_pdfish) < 320
    for row in only_pdfish:
        assert matches_criteria(row, {"attachments": "pdf_only"})
