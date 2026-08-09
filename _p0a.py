from pathlib import Path

p = Path("backend/app/services/evidencias_notificacion_service.py")
t = p.read_text(encoding="utf-8")

# 1 constant
if 'ETIQUETA_ERROR = "EVIDENCIA_ERROR"' not in t:
    t = t.replace(
        'ETIQUETA_PROCESADO = "EVIDENCIA_OK"\n',
        'ETIQUETA_PROCESADO = "EVIDENCIA_OK"\nETIQUETA_ERROR = "EVIDENCIA_ERROR"\n',
        1,
    )
    print("const ok")

# 2 query
needle_q = 'f\'-label:"{ETIQUETA_PROCESADO}"\''
repl_q = 'f\'-label:"{ETIQUETA_PROCESADO}" -label:"{ETIQUETA_ERROR}"\''
if needle_q not in t:
    raise SystemExit("q needle missing: " + repr([line for line in t.splitlines() if "ETIQUETA_PROCESADO" in line and "label" in line][:5]))
t = t.replace(needle_q, repl_q, 1)
print("q ok")

# 3 empty fields
if '"errores_marcados"' not in t:
    t = t.replace(
        '"etiqueta_agotada": False,\n    }',
        '"etiqueta_agotada": False,\n        "errores_marcados": 0,\n        "sin_avance": False,\n    }',
        1,
    )
    print("empty ok")

# 4 err label ensure
if "err_label_id = ensure_user_label_id" not in t:
    t = t.replace(
        "ok_label_id = ensure_user_label_id(service, ETIQUETA_PROCESADO)\n",
        "ok_label_id = ensure_user_label_id(service, ETIQUETA_PROCESADO)\n"
        "    err_label_id = ensure_user_label_id(service, ETIQUETA_ERROR)\n",
        1,
    )
    print("err_label ok")

# 5 marcar_error helper after _marcar_procesado
if "def _marcar_error" not in t:
    marker = '''            return False

    lote_objetivo = max(1, min(int(max_messages), 200))'''
    insert = '''            return False

    def _marcar_error(mid: str, motivo: str) -> bool:
        """Excluye del escaneo mensajes con fallo definitivo."""
        if not mid or not err_label_id:
            return False
        try:
            add_message_user_labels_only(service, mid, [err_label_id])
            logger.info("[EVIDENCIAS] %s mid=%s motivo=%s", ETIQUETA_ERROR, mid, motivo)
            return True
        except Exception as ex:
            logger.warning("[EVIDENCIAS] etiquetar %s %s: %s", ETIQUETA_ERROR, mid, ex)
            return False

    lote_objetivo = max(1, min(int(max_messages), 200))'''
    if marker not in t:
        raise SystemExit("marcar insert marker missing")
    t = t.replace(marker, insert, 1)
    print("marcar_error ok")

# 6 counters
if "errores_marcados = 0" not in t.split("revisados = 0")[1][:400]:
    t = t.replace(
        "    sin_correo = 0\n    sin_pdf = 0\n    truncado = False\n",
        "    sin_correo = 0\n    sin_pdf = 0\n    errores_marcados = 0\n    truncado = False\n",
        1,
    )
    print("counter ok")

# 7 fail paths
pairs = [
    (
        "        if not email_cliente:\n            sin_correo += 1\n            omitidos += 1\n            continue\n",
        "        if not email_cliente:\n            sin_correo += 1\n            omitidos += 1\n            if _marcar_error(mid, \"sin_correo\"):\n                errores_marcados += 1\n            continue\n",
    ),
    (
        "        if not raw:\n            sin_pdf += 1\n            omitidos += 1\n            continue\n",
        "        if not raw:\n            sin_pdf += 1\n            omitidos += 1\n            if _marcar_error(mid, \"sin_raw_eml\"):\n                errores_marcados += 1\n            continue\n",
    ),
    (
        "        if not pdf_bytes:\n            sin_pdf += 1\n            omitidos += 1\n            continue\n",
        "        if not pdf_bytes:\n            sin_pdf += 1\n            omitidos += 1\n            if _marcar_error(mid, \"pdf_generation_failed\"):\n                errores_marcados += 1\n            continue\n",
    ),
]
for a, b in pairs:
    if a not in t:
        raise SystemExit("fail path missing: " + a[:60])
    t = t.replace(a, b, 1)
print("fail paths ok")

# 8 return block
old_end = '''    mensaje = f"[{etiqueta_activa}] " + mensaje
    if etiqueta_agotada:
        mensaje += ". Etiqueta agotada (no quedan pendientes sin EVIDENCIA_OK)."
    else:
        mensaje += ". Quedan mas mensajes; continue escaneando esta etiqueta."

    return {
        "ok": True,
        "error": None,
        "mensaje": mensaje,
        "candidatos": candidatos,
        "revisados": revisados,
        "guardados": guardados,
        "omitidos": omitidos,
        "ya_existentes": ya_existentes,
        "sin_correo": sin_correo,
        "sin_pdf": sin_pdf,
        "etiquetados": etiquetados,
        "etiquetas_faltantes": etiquetas_faltantes,
        "truncado": truncado,
        "emails_guardados": emails_guardados,
        "candidatos_por_etiqueta": candidatos_por_etiqueta,
        "etiqueta_escaneada": etiqueta_activa,
        "etiqueta_agotada": bool(etiqueta_agotada) and not truncado,
    }
'''
new_end = '''    if errores_marcados:
        mensaje += f". Marcados {ETIQUETA_ERROR}={errores_marcados}"

    sin_avance = (
        not truncado and guardados == 0 and candidatos == 0
    ) or (
        not truncado
        and guardados == 0
        and revisados > 0
        and errores_marcados >= revisados
    )

    mensaje = f"[{etiqueta_activa}] " + mensaje
    if etiqueta_agotada or sin_avance:
        mensaje += (
            f". Etiqueta agotada (no quedan no leidos sin "
            f"{ETIQUETA_PROCESADO}/{ETIQUETA_ERROR})."
        )
        etiqueta_agotada = True
    else:
        mensaje += ". Quedan mas mensajes; continue escaneando esta etiqueta."

    return {
        "ok": True,
        "error": None,
        "mensaje": mensaje,
        "candidatos": candidatos,
        "revisados": revisados,
        "guardados": guardados,
        "omitidos": omitidos,
        "ya_existentes": ya_existentes,
        "sin_correo": sin_correo,
        "sin_pdf": sin_pdf,
        "etiquetados": etiquetados,
        "etiquetas_faltantes": etiquetas_faltantes,
        "truncado": truncado,
        "emails_guardados": emails_guardados,
        "candidatos_por_etiqueta": candidatos_por_etiqueta,
        "etiqueta_escaneada": etiqueta_activa,
        "etiqueta_agotada": bool(etiqueta_agotada) and not truncado,
        "errores_marcados": errores_marcados,
        "sin_avance": bool(sin_avance) and not truncado,
    }
'''
if old_end not in t:
    raise SystemExit("return end missing")
t = t.replace(old_end, new_end, 1)
print("return ok")

# candidatos 0 msg
t = t.replace(
    'f\'(excluyendo etiqueta "{ETIQUETA_PROCESADO}").\'',
    'f"(excluyendo {ETIQUETA_PROCESADO}/{ETIQUETA_ERROR})."',
    1,
)

# 9 eliminar_evidencias full replace by finding def and next def
start = t.find("def eliminar_evidencias(")
end = t.find("\ndef regenerar_pdf_evidencia(", start)
if start < 0 or end < 0:
    raise SystemExit(f"eliminar bounds {start} {end}")
new_elim = '''def eliminar_evidencias(
    db: Session,
    ids: list[int],
    *,
    reabrir_gmail: bool = True,
) -> dict[str, Any]:
    """
    Borra evidencias por id.
    Si ``reabrir_gmail``, quita EVIDENCIA_OK/EVIDENCIA_ERROR y deja UNREAD
    para que puedan volver a escanearse.
    """
    clean = sorted({int(x) for x in (ids or []) if x is not None and int(x) > 0})
    out: dict[str, Any] = {"deleted": 0, "gmail_reabiertos": 0, "gmail_errores": 0}
    if not clean:
        return out

    mids: list[str] = []
    deleted = 0
    chunk_size = 200
    for i in range(0, len(clean), chunk_size):
        chunk = clean[i : i + chunk_size]
        rows = (
            db.execute(
                select(EvidenciaNotificacion).where(EvidenciaNotificacion.id.in_(chunk))
            )
            .scalars()
            .all()
        )
        for row in rows:
            mid = (row.gmail_message_id or "").strip()
            if mid:
                mids.append(mid)
            db.delete(row)
            deleted += 1
    if deleted:
        db.commit()
        logger.info("[EVIDENCIAS] eliminadas=%s ids_sample=%s", deleted, clean[:10])
    out["deleted"] = deleted

    if not reabrir_gmail or not mids:
        return out

    try:
        from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials
        from app.services.pagos_gmail.gmail_service import (
            build_gmail_service,
            get_existing_user_label_id,
            modify_message_labels_add_remove,
        )

        creds = get_pagos_gmail_credentials()
        if creds is None:
            logger.warning("[EVIDENCIAS] reabrir Gmail: sin credenciales")
            return out
        service = build_gmail_service(creds)
        rem = [
            x
            for x in (
                get_existing_user_label_id(service, ETIQUETA_PROCESADO),
                get_existing_user_label_id(service, ETIQUETA_ERROR),
            )
            if x
        ]
        for mid in mids:
            try:
                modify_message_labels_add_remove(
                    service,
                    mid,
                    add_label_ids=["UNREAD"],
                    remove_label_ids=rem,
                )
                out["gmail_reabiertos"] += 1
            except Exception as ex:
                out["gmail_errores"] += 1
                logger.warning("[EVIDENCIAS] reabrir Gmail %s: %s", mid, ex)
    except Exception as ex:
        logger.warning("[EVIDENCIAS] reabrir Gmail lote: %s", ex)
    return out


'''
t = t[:start] + new_elim + t[end + 1 :]  # end points at \ndef -> keep one newline via [end+1:]? 
# end is index of \ndef regenerar - we want to keep "\ndef regenerar..."
# t[end:] starts with \ndef regenerar - good if we don't include leading newline in new_elim twice
# new_elim ends with \n\n so use t[end:] which is \ndef...
t = t[:start] + new_elim + t[end+1:]  # skip the \n before def in end... wait end finds "\ndef regenerar" so t[end:] = "\ndef regenerar"
# new_elim already ends with blank line; t[end:] starts with \n - OK as \n\ndef
print("eliminar ok")

p.write_text(t, encoding="utf-8")
print("written")
