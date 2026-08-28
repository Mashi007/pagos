"""Demo ~320 correos cuando Gmail no está conectado."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from app.services.auditoria_email.query import matches_criteria

_SUBJECTS = (
    "Comprobante de pago transferencia",
    "Captura pago cuota",
    "Promesa de pago esta semana",
    "Reclamo por cobro indebido",
    "Intimación legal - abogado",
    "Delivery Status Notification (Failure)",
    "Urgente: cuota vencida",
    "Consulta saldo",
    "Pago Bs. comprobante PDF",
    "Transferencia Zelle adjunto",
)

_FROM = (
    "cliente{n}@gmail.com",
    "pagos{n}@outlook.com",
    "mailer-daemon@googlemail.com",
    "cobranza.externa{n}@yahoo.com",
)


def generate_demo_messages(n: int = 320) -> List[Dict[str, Any]]:
    now = datetime.utcnow()
    out: List[Dict[str, Any]] = []
    for i in range(n):
        subj = _SUBJECTS[i % len(_SUBJECTS)]
        if i % 7 == 0:
            subj = f"{subj} V{10000000 + i}"
        if i % 5 == 0:
            subj = f"{subj} USD {50 + (i % 40)}"
        frm_tpl = _FROM[i % len(_FROM)]
        frm = frm_tpl.format(n=i % 90)
        has_att = i % 3 != 0
        types: List[str] = []
        max_kb = None
        filenames = ""
        if has_att:
            if i % 4 == 0:
                types = ["comprobante.pdf"]
                max_kb = 80 + (i % 200)
            elif i % 4 == 1:
                types = ["captura.jpg"]
                max_kb = 30 + (i % 120)
            else:
                types = ["pago.png", "detalle.pdf"]
                max_kb = 120 + (i % 80)
            filenames = "|".join(types)
        out.append(
            {
                "gmail_message_id": f"demo-{i:04d}",
                "gmail_thread_id": f"demo-th-{i // 3:04d}",
                "from_email": frm,
                "from_name": f"Remitente {i}",
                "subject": subj,
                "snippet": f"Mensaje demo #{i}. {subj}",
                "internal_date": now - timedelta(hours=i * 3),
                "has_attachment": has_att,
                "attachment_types": types,
                "attachment_max_kb": max_kb,
                "filename_joined": filenames,
                "label_ids": ["INBOX"],
                "source": "demo",
            }
        )
    return out


def filter_demo(criteria: Dict[str, Any], *, limit: int | None = None) -> List[Dict[str, Any]]:
    rows = [r for r in generate_demo_messages(320) if matches_criteria(r, criteria)]
    if limit is not None:
        return rows[: max(0, int(limit))]
    return rows
