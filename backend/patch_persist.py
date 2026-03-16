# Patch configuracion_email.py: _persist_email_config no debe borrar config version 2 (4 cuentas)
path = "app/api/v1/endpoints/configuracion_email.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

old = '''def _persist_email_config(db: Session) -> None:
    """Guarda el stub actual en la tabla configuracion para que persista entre reinicios y workers."""
    from app.core.email_config_holder import prepare_for_db_storage

    try:
        payload_data = prepare_for_db_storage(_email_config_stub)
        payload = json.dumps(payload_data)
        row = db.get(Configuracion, CLAVE_EMAIL_CONFIG)
        if row:
            row.valor = payload
        else:
            db.add(Configuracion(clave=CLAVE_EMAIL_CONFIG, valor=payload))
        db.commit()
    except Exception as e:
        logger.exception("Error persistiendo config email en BD: %s", e)
        db.rollback()
        raise'''

new = '''# Claves globales que comparten stub y config version 2. Al guardar desde legacy, solo se fusionan estas.
_STUB_GLOBAL_KEYS = (
    "modo_pruebas", "email_pruebas", "emails_pruebas",
    "email_activo", "email_activo_notificaciones", "email_activo_informe_pagos",
    "email_activo_estado_cuenta", "email_activo_cobros", "email_activo_campanas", "email_activo_tickets",
    "modo_pruebas_notificaciones", "modo_pruebas_informe_pagos", "modo_pruebas_estado_cuenta",
    "modo_pruebas_cobros", "modo_pruebas_campanas", "modo_pruebas_tickets",
    "tickets_notify_emails",
)


def _persist_email_config(db: Session) -> None:
    """Guarda el stub actual en la tabla configuracion para que persista entre reinicios y workers.
    Si en BD ya existe config version 2 (4 cuentas), solo fusiona las claves globales del stub
    para no sobrescribir cuentas/asignacion y evitar doble proceso o perdida de activacion/desactivacion."""
    from app.core.email_config_holder import prepare_for_db_storage

    try:
        row = db.get(Configuracion, CLAVE_EMAIL_CONFIG)
        if row and row.valor:
            try:
                data = json.loads(row.valor)
                if isinstance(data, dict) and data.get("version") == 2 and "cuentas" in data:
                    for key in _STUB_GLOBAL_KEYS:
                        if key in _email_config_stub:
                            data[key] = _email_config_stub[key]
                    payload = json.dumps(data)
                    row.valor = payload
                    db.commit()
                    return
            except (json.JSONDecodeError, TypeError):
                pass
        payload_data = prepare_for_db_storage(_email_config_stub)
        payload = json.dumps(payload_data)
        if row:
            row.valor = payload
        else:
            db.add(Configuracion(clave=CLAVE_EMAIL_CONFIG, valor=payload))
        db.commit()
    except Exception as e:
        logger.exception("Error persistiendo config email en BD: %s", e)
        db.rollback()
        raise'''

if old in c:
    c = c.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("OK: _persist_email_config actualizado")
else:
    print("NO ENCONTRADO")
    # try without docstring accent
    if "def _persist_email_config" in c and "prepare_for_db_storage(_email_config_stub)" in c:
        print("Fragmentos encontrados; puede haber diferencia de encoding en docstring")
