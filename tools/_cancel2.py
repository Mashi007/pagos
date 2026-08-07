from pathlib import Path

# tarea finish handling
path = Path("backend/app/api/v1/endpoints/notificaciones/routes.py")
text = path.read_text(encoding="utf-8")

old = '''        pausado = bool(res.get("pausado_limite_gmail"))
        total_lista = int(para_persist.get("total_en_lista") or 0)
        procesados_fin = int(res.get("procesados") or total_lista or 0)
        det["procesados"] = procesados_fin
        det["total_en_lista"] = total_lista
        det["pausado_limite_gmail"] = pausado
        if pausado:
            from app.services.cuota_estado import hoy_negocio

            det["fecha_negocio_pausa"] = hoy_negocio().isoformat()
            det["fecha_negocio_inicio"] = (
                omitir_desde.isoformat()
                if omitir_desde is not None
                else hoy_negocio().isoformat()
            )
            det["reanudable_siguiente_dia"] = True
        para_persist["detalles"] = det
        persist_ultimo_envio_batch(
            db,
            resultado=para_persist,
            origen="api_enviar_caso_manual",
            inicio_utc=inicio_utc,
            en_proceso=False,
            estado="pausado_limite_gmail" if pausado else "finalizado",
            error=(
                (str(res.get("motivo_pausa") or "")[:5000] or None) if pausado else None
            ),
        )
        from app.services.cuota_estado import hoy_negocio
        from app.services.notificaciones_lotes_continuar import (
            quitar_lote_continuar,
            upsert_lote_continuar,
        )

        if pausado or (total_lista > 0 and procesados_fin < total_lista):
'''

new = '''        pausado = bool(res.get("pausado_limite_gmail"))
        cancelado = bool(res.get("cancelado_usuario"))
        total_lista = int(para_persist.get("total_en_lista") or 0)
        procesados_fin = int(res.get("procesados") or total_lista or 0)
        det["procesados"] = procesados_fin
        det["total_en_lista"] = total_lista
        det["pausado_limite_gmail"] = pausado
        det["cancelado_usuario"] = cancelado
        if pausado or cancelado:
            from app.services.cuota_estado import hoy_negocio

            det["fecha_negocio_pausa"] = hoy_negocio().isoformat()
            det["fecha_negocio_inicio"] = (
                omitir_desde.isoformat()
                if omitir_desde is not None
                else hoy_negocio().isoformat()
            )
            det["reanudable_siguiente_dia"] = True
        para_persist["detalles"] = det
        if cancelado:
            estado_fin = "cancelado_usuario"
        elif pausado:
            estado_fin = "pausado_limite_gmail"
        else:
            estado_fin = "finalizado"
        persist_ultimo_envio_batch(
            db,
            resultado=para_persist,
            origen="api_enviar_caso_manual",
            inicio_utc=inicio_utc,
            en_proceso=False,
            estado=estado_fin,
            error=(
                (str(res.get("motivo_pausa") or "")[:5000] or None)
                if (pausado or cancelado)
                else None
            ),
        )
        from app.services.cuota_estado import hoy_negocio
        from app.services.notificaciones_envio_cancel import limpiar_cancelacion_lote
        from app.services.notificaciones_lotes_continuar import (
            quitar_lote_continuar,
            upsert_lote_continuar,
        )

        try:
            limpiar_cancelacion_lote(db)
        except Exception:
            pass

        if pausado or cancelado or (total_lista > 0 and procesados_fin < total_lista):
'''

if "cancelado_usuario" in text and 'estado_fin = "cancelado_usuario"' in text:
    print("tarea already")
elif old not in text:
    raise SystemExit("tarea block missing")
else:
    text = text.replace(old, new, 1)
    # also fix upsert estado line
    text = text.replace(
        'estado="pausado_limite_gmail" if pausado else "incompleto",',
        'estado=("pausado_limite_gmail" if pausado else ("cancelado_usuario" if cancelado else "incompleto")),',
        1,
    )
    path.write_text(text, encoding="utf-8")
    print("tarea ok")

# upsert estado uses cancelado - need ensure cancelado in scope - yes

# batch resumen: treat cancelado as not active
path = Path("backend/app/services/notificaciones_envio_batch_resumen.py")
text = path.read_text(encoding="utf-8")
for old_s, new_s, label in [
    (
        'if estado in ("finalizado", "pausado_limite_gmail"):\n        return False',
        'if estado in ("finalizado", "pausado_limite_gmail", "cancelado_usuario"):\n        return False',
        "sigue",
    ),
    (
        'if estado in ("finalizado", "pausado_limite_gmail"):\n        return False\n    det = ultimo.get("detalles")\n    det_rec = det if isinstance(det, dict) else {}\n    if bool(det_rec.get("pausado_limite_gmail")) and estado != "en_proceso":\n        return False',
        'if estado in ("finalizado", "pausado_limite_gmail", "cancelado_usuario"):\n        return False\n    det = ultimo.get("detalles")\n    det_rec = det if isinstance(det, dict) else {}\n    if bool(det_rec.get("pausado_limite_gmail") or det_rec.get("cancelado_usuario")) and estado != "en_proceso":\n        return False',
        "marca",
    ),
]:
    if new_s in text:
        print(label, "already")
    elif old_s not in text:
        print(label, "MISSING")
    else:
        text = text.replace(old_s, new_s, 1)
        print(label, "ok")
path.write_text(text, encoding="utf-8")

# Add POST cancel endpoint after GET ultimo
path = Path("backend/app/api/v1/endpoints/notificaciones/routes.py")
text = path.read_text(encoding="utf-8")
if 'def post_cancelar_envio_batch' in text or "/envio-batch/cancelar" in text:
    print("endpoint already")
else:
    anchor = '@router.get("/envio-batch/ultimo")'
    pos = text.find(anchor)
    if pos < 0:
        raise SystemExit("get ultimo missing")
    # find next @router after this one
    next_r = text.find("\n@router.", pos + 10)
    endpoint = '''
@router.post("/envio-batch/cancelar")
def post_cancelar_envio_batch(db: Session = Depends(get_db)):
    """
    Solicita cancelar el lote en curso. El worker corta entre correos (no a media SMTP).
    El progreso queda en cola continuar para reanudar luego; la UI deja de quedar en limbo.
    """
    from app.services.notificaciones_envio_batch_resumen import (
        get_ultimo_envio_batch_dict,
        persist_ultimo_envio_batch,
    )
    from app.services.notificaciones_envio_cancel import solicitar_cancelacion_lote
    from app.services.cuota_estado import hoy_negocio
    from app.services.notificaciones_lotes_continuar import upsert_lote_continuar

    ultimo = get_ultimo_envio_batch_dict(db)
    det = ultimo.get("detalles") if isinstance(ultimo, dict) else {}
    if not isinstance(det, dict):
        det = {}
    tipo = str((ultimo or {}).get("tipo_caso") or det.get("tipo_caso") or "").strip()
    token = str(det.get("token_seguimiento") or "").strip()
    flag = solicitar_cancelacion_lote(
        db, tipo_caso=tipo or None, token_seguimiento=token or None
    )
    # Cierre inmediato en BD para que la UI no reenganche el sondeo.
    if isinstance(ultimo, dict):
        try:
            total = int(ultimo.get("total_en_lista") or det.get("total_en_lista") or 0)
            procesados = int(det.get("procesados") or 0)
        except (TypeError, ValueError):
            total, procesados = 0, 0
        det2 = dict(det)
        det2["en_proceso"] = False
        det2["cancelado_usuario"] = True
        det2["fecha_negocio_pausa"] = hoy_negocio().isoformat()
        if not det2.get("fecha_negocio_inicio"):
            det2["fecha_negocio_inicio"] = hoy_negocio().isoformat()
        det2["reanudable_siguiente_dia"] = True
        persist_ultimo_envio_batch(
            db,
            resultado={
                "enviados": int(ultimo.get("enviados") or 0),
                "fallidos": int(ultimo.get("fallidos") or 0),
                "sin_email": int(ultimo.get("sin_email") or 0),
                "omitidos_config": int(ultimo.get("omitidos_config") or 0),
                "omitidos_paquete_incompleto": int(
                    ultimo.get("omitidos_paquete_incompleto") or 0
                ),
                "enviados_whatsapp": int(ultimo.get("enviados_whatsapp") or 0),
                "fallidos_whatsapp": int(ultimo.get("fallidos_whatsapp") or 0),
                "detalles": det2,
                "total_en_lista": total or ultimo.get("total_en_lista"),
                "tipo_caso": tipo or ultimo.get("tipo_caso"),
                "omitidos_desistimiento": ultimo.get("omitidos_desistimiento"),
                "omitidos_ya_enviado": ultimo.get("omitidos_ya_enviado"),
            },
            origen=str(ultimo.get("origen") or "api_enviar_caso_manual"),
            error="cancelado_por_usuario",
            inicio_utc=str(ultimo.get("inicio_utc") or "") or None,
            en_proceso=False,
            estado="cancelado_usuario",
        )
        if tipo and total > 0 and procesados < total:
            upsert_lote_continuar(
                db,
                tipo_caso=tipo,
                total_en_lista=total,
                procesados=procesados,
                enviados=int(ultimo.get("enviados") or 0),
                fallidos=int(ultimo.get("fallidos") or 0),
                estado="cancelado_usuario",
                fecha_negocio_inicio=str(det2.get("fecha_negocio_inicio") or hoy_negocio().isoformat()),
                fecha_negocio_pausa=hoy_negocio().isoformat(),
                inicio_utc=str(ultimo.get("inicio_utc") or "") or None,
                motivo="cancelado_por_usuario",
            )
    db.commit()
    return {
        "ok": True,
        "mensaje": (
            "Cancelacion solicitada. El servidor dejara de enviar tras el correo en curso "
            "(si habia uno). Puede reanudar el pendiente mas tarde; los ya enviados se omiten."
        ),
        "cancel": flag,
        "tipo_caso": tipo or None,
    }


'''
    text = text[:next_r] + endpoint + text[next_r:]
    path.write_text(text, encoding="utf-8")
    print("endpoint ok")
