"""One-off patch for configuracion_email probar endpoint."""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "api" / "v1" / "endpoints" / "configuracion_email.py"
text = p.read_text(encoding="utf-8")

old1 = """class ProbarEmailRequest(BaseModel):
    email_destino: Optional[str] = None
    email_cc: Optional[str] = None
    subject: Optional[str] = None
    mensaje: Optional[str] = None"""

new1 = """class ProbarEmailRequest(BaseModel):
    email_destino: Optional[str] = None
    email_cc: Optional[str] = None
    subject: Optional[str] = None
    mensaje: Optional[str] = None
    # Opcional: misma cuenta SMTP que un servicio (p. ej. notificaciones, cuentas 3/4).
    # Por defecto cobros (Cuenta 1), comportamiento historico.
    servicio: Optional[str] = None
    tipo_tab: Optional[str] = None"""

old2 = '''def post_email_probar(payload: ProbarEmailRequest = Body(...), db: Session = Depends(get_db)):
    """Envia un correo de prueba por SMTP (config persistida en BD). Con email_config version 2 usa la cuenta Cobros (Cuenta 1), igual que recibos en pagos reportados."""
    _load_email_config_from_db(db)
    _sync_stub_from_settings()
    from app.core.email_config_holder import sync_from_db, get_smtp_config
    from app.core.email import send_email

    sync_from_db()
    cfg_send = get_smtp_config(servicio="cobros")'''

new2 = '''def post_email_probar(payload: ProbarEmailRequest = Body(...), db: Session = Depends(get_db)):
    """Envia un correo de prueba por SMTP (config persistida en BD). Con email_config v2 la cuenta depende de servicio/tipo_tab."""
    _load_email_config_from_db(db)
    _sync_stub_from_settings()
    from app.core.email_config_holder import sync_from_db, get_smtp_config
    from app.core.email import send_email

    sync_from_db()
    raw_svc = (payload.servicio or "cobros").strip().lower()
    if raw_svc not in (
        "cobros",
        "notificaciones",
        "estado_cuenta",
        "tickets",
        "campanas",
        "informe_pagos",
    ):
        raw_svc = "cobros"
    tipo_tab = (payload.tipo_tab or "").strip() or None
    cfg_send = get_smtp_config(servicio=raw_svc, tipo_tab=tipo_tab)'''

old3 = '''    ok, error_msg = send_email(
        to_emails=recipients,
        subject=subject,
        body_text=body,
        respetar_destinos_manuales=True,
        servicio="cobros",
    )'''

new3 = '''    ok, error_msg = send_email(
        to_emails=recipients,
        subject=subject,
        body_text=body,
        respetar_destinos_manuales=True,
        servicio=raw_svc,
        tipo_tab=tipo_tab,
    )'''


def main() -> None:
    global text
    t = text
    if old1 not in t:
        raise SystemExit("block1 not found")
    t = t.replace(old1, new1, 1)
    if old2 not in t:
        raise SystemExit("block2 not found")
    t = t.replace(old2, new2, 1)
    if old3 not in t:
        raise SystemExit("block3 not found")
    t = t.replace(old3, new3, 1)
    p.write_text(t, encoding="utf-8")
    print("patched", p)


if __name__ == "__main__":
    main()
