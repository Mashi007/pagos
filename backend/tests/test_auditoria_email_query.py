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


def test_asunto_con_or_se_limita_al_asunto():
    """La forma {a OR b} busca en todo el mensaje, no en el asunto. El
    post-filtro local sí mira solo el asunto, así que Gmail devolvía medio buzón
    y el lote gastaba un fetch por correo para no aceptar ninguno."""
    criterios = {
        "newerThanDays": 7,
        "subject": "comprobante OR pago",
        "subjectMode": "contains",
    }
    q = build_gmail_query(criterios)
    assert "subject:(comprobante OR pago)" in q
    assert "{comprobante OR pago}" not in q

    # Query y post-filtro deben coincidir: el asunto manda.
    def correo(asunto):
        return {
            "subject": asunto,
            "from_email": "cliente@banco.com",
            "internal_date": None,
            "attachment_names": ["c.pdf"],
            "has_attachment": True,
        }

    assert matches_criteria(correo("Comprobante de pago"), criterios)
    assert matches_criteria(correo("Pago realizado"), criterios)
    assert not matches_criteria(correo("Consulta de saldo"), criterios)


def test_build_query_pdf_or_image_no_exige_indice_gmail():
    from app.services.pagos_gmail.gmail_service import pagos_gmail_list_q_media_parts

    q = build_gmail_query(
        {"attachments": "pdf_or_image", "newerThanDays": 7}
    )
    assert "newer_than:7d" in q
    assert pagos_gmail_list_q_media_parts() not in q
    assert "has:attachment" not in q


def test_build_query_pagos_gmail_mode():
    from app.services.pagos_gmail.gmail_service import pagos_gmail_list_q_media_parts

    q = build_gmail_query({"attachments": "pagos_gmail", "newerThanDays": 30})
    assert pagos_gmail_list_q_media_parts() not in q
    assert "has:attachment" not in q
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
        "has_attachment": False,
        "attachment_types": [],
        "filename_joined": "",
        "attachment_max_kb": 0,
    }
    # Foto pegada: Gmail no indexa filename. El post-filtro no la tira.
    assert matches_criteria(
        row,
        {"attachments": "pdf_or_image", "subject": "pago"},
        trust_gmail_attachment_q=True,
    )
    assert matches_criteria(
        row,
        {"attachments": "pdf_or_image", "subject": "pago"},
        trust_gmail_attachment_q=False,
    )


def test_asunto_no_exige_indice_adjuntos_gmail():
    """Con asunto (Pago / comprobante) el lote no depende de has:attachment."""
    from app.services.pagos_gmail.gmail_service import pagos_gmail_list_q_media_parts

    q = build_gmail_query(
        {
            "attachments": "pagos_gmail",
            "subject": "comprobante OR pago",
            "subjectMode": "contains",
            "dateFrom": "2026-01-01",
            "dateTo": "2026-03-01",
        }
    )
    assert "subject:(comprobante OR pago)" in q
    assert pagos_gmail_list_q_media_parts() not in q
    assert "has:attachment" not in q


def test_sin_asunto_tambien_incluye_embebidos_sin_indice():
    from app.services.pagos_gmail.gmail_service import pagos_gmail_list_q_media_parts

    q = build_gmail_query({"attachments": "pdf_or_image", "newerThanDays": 7})
    assert pagos_gmail_list_q_media_parts() not in q
    assert "has:attachment" not in q


def test_demo_estimate_respects_criteria():
    all_rows = filter_demo({})
    assert len(all_rows) == 320
    only_pdfish = filter_demo({"attachments": "pdf_only"})
    assert 0 < len(only_pdfish) < 320
    for row in only_pdfish:
        assert matches_criteria(row, {"attachments": "pdf_only"})
