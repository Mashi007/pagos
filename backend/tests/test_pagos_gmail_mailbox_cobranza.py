"""Gestión (mailbox=cobranza): solo buzón cobranza@, sin lote IT Master."""
from app.services.pagos_gmail.gmail_service import (
    PAGOS_GMAIL_LOTE_REMITENTE_IT_MASTER,
    is_lote_it_master_message,
    pagos_gmail_manual_redigitaliza_por_remitente_query,
)


def test_redig_cliente_usa_from_no_to_itmaster():
    """Email de cliente en cobranza@: filtro from:<cliente>, no to:itmaster."""
    q = pagos_gmail_manual_redigitaliza_por_remitente_query(
        "cliente@ejemplo.com", criterio="remitente"
    )
    assert "from:cliente@ejemplo.com" in q
    assert f"to:{PAGOS_GMAIL_LOTE_REMITENTE_IT_MASTER}" not in q
    assert "in:inbox" in q


def test_redig_itmaster_sigue_forzando_to_legacy():
    """Flujo legado Informe pagos: itmaster se busca como destinatario."""
    q = pagos_gmail_manual_redigitaliza_por_remitente_query(
        PAGOS_GMAIL_LOTE_REMITENTE_IT_MASTER, criterio="remitente"
    )
    assert f"to:{PAGOS_GMAIL_LOTE_REMITENTE_IT_MASTER}" in q


def test_lote_it_master_requiere_asunto_cedula_y_eml():
    """Un correo cliente→cobranza@ con imagen no es lote IT Master."""
    headers = {
        "from": "Cliente <cliente@ejemplo.com>",
        "to": "cobranza@rapicreditca.com",
        "subject": "Comprobante de pago",
    }
    payload = {
        "parts": [
            {
                "mimeType": "image/jpeg",
                "filename": "comprobante.jpg",
                "body": {"size": 100},
            }
        ]
    }
    es, ced, n = is_lote_it_master_message(headers, payload)
    assert es is False
    assert ced is None
    assert n == 0
