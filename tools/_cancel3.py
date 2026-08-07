from pathlib import Path
path = Path("backend/app/api/v1/endpoints/notificaciones/routes.py")
text = path.read_text(encoding="utf-8")

start = text.find('        pausado = bool(res.get("pausado_limite_gmail"))')
end = text.find('        db.commit()\n        logger.info(\n            "[notif] enviar_caso_manual BG fin tipo=%s', start)
if start < 0 or end < 0:
    raise SystemExit(f"bounds {start} {end}")

new_block = '''        pausado = bool(res.get("pausado_limite_gmail"))
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
            fecha_ini = None
            if omitir_desde is not None:
                fecha_ini = omitir_desde.isoformat()
            else:
                pend0 = None
                try:
                    from app.services.notificaciones_lotes_continuar import (
                        obtener_lote_continuar as _obt,
                    )

                    pend0 = _obt(db, tipo)
                except Exception:
                    pend0 = None
                fecha_ini = str((pend0 or {}).get("fecha_negocio_inicio") or "") or hoy_negocio().isoformat()
            est_cola = (
                "pausado_limite_gmail"
                if pausado
                else ("cancelado_usuario" if cancelado else "incompleto")
            )
            upsert_lote_continuar(
                db,
                tipo_caso=tipo,
                total_en_lista=total_lista,
                procesados=procesados_fin,
                enviados=int(res.get("enviados") or 0),
                fallidos=int(res.get("fallidos") or 0),
                estado=est_cola,
                fecha_negocio_inicio=fecha_ini,
                fecha_negocio_pausa=hoy_negocio().isoformat(),
                inicio_utc=inicio_utc,
                motivo=str(res.get("motivo_pausa") or "")[:2000] or None,
            )
        else:
            quitar_lote_continuar(db, tipo)
'''

text = text[:start] + new_block + text[end:]
# fix log line to include cancelado
text = text.replace(
    '"[notif] enviar_caso_manual BG fin tipo=%s token=%s enviados=%s total_lista=%s pausado_gmail=%s procesados=%s",\n            tipo,\n            token_seguimiento[:12],\n            res.get("enviados"),\n            res.get("total_en_lista"),\n            pausado,\n            procesados_fin,\n        )',
    '"[notif] enviar_caso_manual BG fin tipo=%s token=%s enviados=%s total_lista=%s pausado_gmail=%s cancelado=%s procesados=%s",\n            tipo,\n            token_seguimiento[:12],\n            res.get("enviados"),\n            res.get("total_en_lista"),\n            pausado,\n            cancelado,\n            procesados_fin,\n        )',
    1,
)
path.write_text(text, encoding="utf-8")
print("tarea rewritten")

# batch resumen
path = Path("backend/app/services/notificaciones_envio_batch_resumen.py")
text = path.read_text(encoding="utf-8")
text2 = text.replace(
    'if estado in ("finalizado", "pausado_limite_gmail"):',
    'if estado in ("finalizado", "pausado_limite_gmail", "cancelado_usuario"):',
)
text2 = text2.replace(
    'if bool(det_rec.get("pausado_limite_gmail")) and estado != "en_proceso":',
    'if bool(det_rec.get("pausado_limite_gmail") or det_rec.get("cancelado_usuario")) and estado != "en_proceso":',
)
path.write_text(text2, encoding="utf-8")
print("resumen", text != text2)

# endpoint
path = Path("backend/app/api/v1/endpoints/notificaciones/routes.py")
text = path.read_text(encoding="utf-8")
if "/envio-batch/cancelar" in text:
    print("endpoint already")
else:
    marker = '    return {\n        "ultimo": finalizar_envio_batch_si_stale(db),\n        "lotes_continuar": listar_lotes_continuar(db),\n    }\n'
    if marker not in text:
        raise SystemExit("get return missing")
    endpoint = '''    return {
        "ultimo": finalizar_envio_batch_si_stale(db),
        "lotes_continuar": listar_lotes_continuar(db),
    }


@router.post("/envio-batch/cancelar")
def post_cancelar_envio_batch(db: Session = Depends(get_db)):
    """Cancela el lote en curso (corta entre correos). Quita limbo de la UI."""
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
                fecha_negocio_inicio=str(
                    det2.get("fecha_negocio_inicio") or hoy_negocio().isoformat()
                ),
                fecha_negocio_pausa=hoy_negocio().isoformat(),
                inicio_utc=str(ultimo.get("inicio_utc") or "") or None,
                motivo="cancelado_por_usuario",
            )
    db.commit()
    return {
        "ok": True,
        "mensaje": (
            "Cancelacion solicitada. El servidor deja de enviar tras el correo en curso. "
            "El pendiente queda en cola para continuar luego."
        ),
        "cancel": flag,
        "tipo_caso": tipo or None,
    }

'''
    path.write_text(text.replace(marker, endpoint, 1), encoding="utf-8")
    print("endpoint ok")
