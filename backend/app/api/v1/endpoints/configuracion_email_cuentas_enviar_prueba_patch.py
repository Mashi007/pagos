# Append this block to configuracion_email_cuentas.py after: return {"message": "Configuracion de 4 cuentas guardada", "version": 2}


def _parse_emails_pruebas(email_pruebas: str) -> List[str]:
    """Convierte el campo email_pruebas (coma, punto y coma o saltos de linea) en lista de emails validos."""
    if not (email_pruebas or "").strip():
        return []
    raw = (email_pruebas or "").replace(",", " ").replace(";", " ").replace("\n", " ")
    emails = [e.strip() for e in raw.split() if e.strip()]
    valid = []
    for e in emails:
        if "@" in e and "." in e.split("@")[-1] and len((e.split("@")[-1].split(".")[-1])) >= 2:
            valid.append(e)
    return valid


@router.post(
    "/enviar-prueba",
    summary="Envia un correo de prueba a todos los correos de pruebas registrados.",
)
def post_email_enviar_prueba(db: Session = Depends(get_db)):
    """
    Envia un email de prueba a cada direccion indicada en 'Correo de pruebas'
    (varios correos separados por coma, punto y coma o espacio).
    Usa la Cuenta 1 (Cobros) para el envio.
    """
    from app.core.email_config_holder import sync_from_db, get_smtp_config
    from app.core.email import send_email

    data = _load_raw_from_db(db)
    if not data:
        raise HTTPException(
            status_code=400,
            detail="No hay configuracion de email guardada. Guarde las cuentas primero.",
        )
    migrated = migrar_config_v1_a_v2(data) if data.get("version") != 2 or "cuentas" not in data else data
    email_pruebas_str = (migrated.get("email_pruebas") or "").strip()
    destinatarios = _parse_emails_pruebas(email_pruebas_str)
    if not destinatarios:
        raise HTTPException(
            status_code=400,
            detail="Configure al menos un correo de pruebas (puede ser varios separados por coma) y vuelva a intentar.",
        )

    sync_from_db()
    cfg = get_smtp_config(servicio="cobros")
    if not (cfg.get("smtp_host") and (cfg.get("smtp_user") or "").strip()):
        raise HTTPException(
            status_code=400,
            detail="Configure la Cuenta 1 (Cobros) con servidor SMTP y usuario antes de enviar la prueba.",
        )
    if not (cfg.get("smtp_password") or "").strip() or (cfg.get("smtp_password") or "").strip() in ("", "***"):
        raise HTTPException(
            status_code=400,
            detail="Falta contrasena SMTP en la Cuenta 1. Configurela antes de enviar la prueba.",
        )

    subject = "Prueba de email - RapiCredit"
    body = "Este es un correo de prueba enviado a todos los correos registrados en Modo pruebas."
    enviados: List[str] = []
    errores: List[dict] = []

    for to in destinatarios:
        ok, err_msg = send_email(
            to_emails=[to],
            subject=subject,
            body_text=body,
            respetar_destinos_manuales=True,
            servicio="cobros",
        )
        if ok:
            enviados.append(to)
            logger.info("Email de prueba enviado a %s", to)
        else:
            errores.append({"email": to, "mensaje": err_msg or "Error al enviar"})
            logger.warning("Email de prueba fallo para %s: %s", to, err_msg)

    return {
        "success": len(errores) == 0,
        "enviados": enviados,
        "errores": errores,
        "mensaje": "Enviado a %d de %d correos." % (len(enviados), len(destinatarios)),
    }
