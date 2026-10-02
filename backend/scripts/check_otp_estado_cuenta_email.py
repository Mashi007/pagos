#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprueba (sin enviar correo) que el servicio OTP de estado de cuenta puede emitir emails.

Uso en servidor / Render shell (con DATABASE_URL y SECRET_KEY del entorno):
  cd backend && python3 scripts/check_otp_estado_cuenta_email.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.email_config_holder import (  # noqa: E402
    get_email_activo,
    get_email_activo_servicio,
    get_modo_pruebas_email,
    get_smtp_config,
    sync_from_db,
)


def main() -> int:
    sync_from_db()
    servicio = "estado_cuenta"
    activo_global = get_email_activo()
    activo_svc = get_email_activo_servicio(servicio)
    modo_pr, emails_pr = get_modo_pruebas_email(servicio=servicio)
    cfg = get_smtp_config(servicio="estado_cuenta_otp")

    smtp_user = (cfg.get("smtp_user") or "").strip()
    from_email = (cfg.get("from_email") or smtp_user or "").strip()
    host = (cfg.get("smtp_host") or "").strip()
    pwd = (cfg.get("smtp_password") or "").strip()

    print("=== OTP estado de cuenta (remitente: tucuenta@ via servicio estado_cuenta_otp) ===")
    print(f"email_activo (global):     {activo_global}")
    print(f"email_activo_estado_cuenta: {activo_svc}")
    print(f"modo_pruebas_estado_cuenta: {modo_pr} -> destinos prueba: {emails_pr or '(ninguno)'}")
    print(f"SMTP host:                 {host or '(vacío)'}")
    print(f"SMTP user:                 {smtp_user or '(vacío)'}")
    print(f"From:                      {from_email or '(vacío)'}")
    print(f"SMTP password configurada:  {'sí' if pwd and pwd != '***' else 'NO'}")

    ok = bool(activo_global and activo_svc and host and smtp_user and pwd and pwd != "***")
    if modo_pr and emails_pr:
        print(
            "\nAVISO: modo pruebas activo para estado_cuenta; "
            "envíos automáticos van a correos de prueba, no al cliente."
        )
    if ok:
        print("\nRESULTADO: configuración mínima OK para intentar envío OTP.")
        return 0
    print("\nRESULTADO: FALTA configuración; los OTP no se enviarán correctamente.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
