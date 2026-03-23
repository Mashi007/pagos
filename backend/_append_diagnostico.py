# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parent / "app" / "services" / "notificaciones_prueba_paquete.py"
t = p.read_text(encoding="utf-8")
if "def ejecutar_diagnostico_paquete_prueba" in t:
    print("diagnostico already present")
    raise SystemExit(0)

append = '''

def ejecutar_diagnostico_paquete_prueba(db: Session, tipo: str) -> Dict[str, Any]:
    """
    Sin enviar correo: resume si un envio de prueba de paquete cumpliria reglas estrictas
    y lista adjuntos que se generarian para el primer item real del criterio.
    """
    from copy import deepcopy

    from app.core.config import settings
    from app.api.v1.endpoints import notificaciones_tabs as nt
    from app.api.v1.endpoints.notificaciones import (
        get_notificaciones_envios_config,
        get_notificaciones_tabs_data,
        get_plantilla_asunto_cuerpo,
        build_contexto_cobranza_para_item,
        plantilla_usa_variables_cobranza,
    )
    from app.models.plantilla_notificacion import PlantillaNotificacion
    from app.services.carta_cobranza_pdf import generar_carta_cobranza_pdf
    from app.services.adjunto_fijo_cobranza import get_adjunto_fijo_cobranza_bytes, get_adjuntos_fijos_por_caso

    tipo = (tipo or "PAGO_1_DIA_ATRASADO").strip()
    if tipo not in TIPOS_PRUEBA_PAQUETE:
        raise HTTPException(
            status_code=422,
            detail=f"tipo debe ser uno de: {', '.join(sorted(TIPOS_PRUEBA_PAQUETE))}",
        )

    data = get_notificaciones_tabs_data(db)
    item = primer_item_ejemplo_por_tipo(data, tipo)
    if not item:
        return {
            "ok": False,
            "motivo": "sin_item_ejemplo_en_bd",
            "tipo": tipo,
            "paquete_estricto": bool(getattr(settings, "NOTIFICACIONES_PAQUETE_ESTRICTO", True)),
            "relax_solo_prueba_destino": bool(
                getattr(settings, "NOTIFICACIONES_PAQUETE_RELAX_SOLO_PRUEBA_DESTINO", False)
            ),
        }

    config_envios = get_notificaciones_envios_config(db)
    if tipo in ("PAGO_1_DIA_ATRASADO", "PAGO_3_DIAS_ATRASADO", "PAGO_5_DIAS_ATRASADO"):
        get_tipo = nt._tipo_retrasadas
        asunto_base = "Cuenta con cuota atrasada - Rapicredit"
        cuerpo_base = "Prueba diagnostico"
    else:
        get_tipo = nt._tipo_prejudicial
        asunto_base = "Aviso prejudicial - Rapicredit"
        cuerpo_base = "Prueba diagnostico"

    item = deepcopy(item)
    paquete_estricto = bool(getattr(settings, "NOTIFICACIONES_PAQUETE_ESTRICTO", True))
    tipo_res = get_tipo(item)
    tipo_cfg = config_envios.get(tipo_res) or {}
    habilitado = tipo_cfg.get("habilitado", True) is not False
    plantilla_id = nt._parse_plantilla_id_desde_config(tipo_cfg.get("plantilla_id"))

    out: Dict[str, Any] = {
        "tipo_solicitado": tipo,
        "tipo_config": tipo_res,
        "habilitado_envio": habilitado,
        "plantilla_id": plantilla_id,
        "paquete_estricto": paquete_estricto,
        "relax_solo_prueba_destino": bool(
            getattr(settings, "NOTIFICACIONES_PAQUETE_RELAX_SOLO_PRUEBA_DESTINO", False)
        ),
    }

    if not habilitado:
        out["ok"] = False
        out["motivo"] = "envio_desactivado_para_este_tipo"
        return out

    if paquete_estricto:
        ok_plant, mot_plant = nt._validar_plantilla_email_estricta(db, plantilla_id)
        out["plantilla_ok"] = ok_plant
        out["plantilla_motivo"] = mot_plant or None
        if not ok_plant:
            out["ok"] = False
            out["motivo"] = mot_plant
            return out
        if not nt._cfg_incluir_pdf_anexo(tipo_cfg):
            out["ok"] = False
            out["motivo"] = "incluir_pdf_anexo_desactivado_en_config"
            return out
        if tipo_cfg.get("incluir_adjuntos_fijos", True) is False:
            out["ok"] = False
            out["motivo"] = "incluir_adjuntos_fijos_desactivado"
            return out
        if not item.get("prestamo_id"):
            out["ok"] = False
            out["motivo"] = "sin_prestamo_id_para_pdf_carta"
            return out

    correlativos_en_batch: dict = {}
    if db and item.get("prestamo_id") and not item.get("contexto_cobranza"):
        plantilla = db.get(PlantillaNotificacion, plantilla_id) if plantilla_id else None
        need_ctx = paquete_estricto or (
            (plantilla and getattr(plantilla, "tipo", None) == "COBRANZA")
            or nt._cfg_incluir_pdf_anexo(tipo_cfg)
            or (plantilla and plantilla_usa_variables_cobranza(plantilla))
        )
        if need_ctx:
            ctx, corr = build_contexto_cobranza_para_item(db, item, correlativos_en_batch)
            if ctx is not None:
                item["contexto_cobranza"] = ctx
                item["_correlativo_envio"] = corr

    get_plantilla_asunto_cuerpo(db, plantilla_id, item, asunto_base, cuerpo_base, modo_pruebas=False)

    attachments = None
    if paquete_estricto:
        incluir_pdf_anexo = True
        incluir_adjuntos_fijos = True
    else:
        incluir_pdf_anexo = nt._cfg_incluir_pdf_anexo(tipo_cfg)
        incluir_adjuntos_fijos = tipo_cfg.get("incluir_adjuntos_fijos", True) is not False

    detalles_adj: list = []
    if incluir_pdf_anexo or incluir_adjuntos_fijos:
        attachments = []
        try:
            if incluir_pdf_anexo:
                ctx_pdf = item.get("contexto_cobranza")
                if ctx_pdf:
                    pdf_bytes = generar_carta_cobranza_pdf(ctx_pdf, db=db)
                    attachments.append((nt.NOMBRE_PDF_CARTA_VARIABLE, pdf_bytes))
                    detalles_adj.append(
                        {
                            "nombre": nt.NOMBRE_PDF_CARTA_VARIABLE,
                            "bytes": len(pdf_bytes) if pdf_bytes else 0,
                            "cabecera_pdf": pdf_bytes[:4] == b"%PDF" if pdf_bytes else False,
                        }
                    )
            if incluir_adjuntos_fijos and db:
                adjunto_fijo = get_adjunto_fijo_cobranza_bytes(db)
                if adjunto_fijo:
                    nombre, data = adjunto_fijo[0], adjunto_fijo[1]
                    attachments.append(adjunto_fijo)
                    detalles_adj.append(
                        {
                            "nombre": nombre,
                            "bytes": len(data) if data else 0,
                            "cabecera_pdf": data[:4] == b"%PDF" if data else False,
                        }
                    )
                tipo_caso = nt._CONFIG_TIPO_TO_TAB.get(tipo_res)
                if tipo_caso:
                    for nombre, contenido in get_adjuntos_fijos_por_caso(db, tipo_caso):
                        attachments.append((nombre, contenido))
                        detalles_adj.append(
                            {
                                "nombre": nombre,
                                "bytes": len(contenido) if contenido else 0,
                                "cabecera_pdf": contenido[:4] == b"%PDF" if contenido else False,
                            }
                        )
        except Exception as e:
            out["ok"] = False
            out["motivo"] = "error_generando_adjuntos"
            out["error_adjuntos"] = str(e)[:500]
            out["adjuntos_previstos"] = detalles_adj
            return out

    ok_pkg, mot_pkg = nt._adjuntos_cumplen_paquete_completo(attachments)
    out["adjuntos_previstos"] = detalles_adj
    out["paquete_completo"] = ok_pkg
    out["paquete_motivo"] = mot_pkg or None
    out["ok"] = bool(ok_pkg)
    if not ok_pkg:
        out["motivo"] = mot_pkg
    else:
        out["motivo"] = "listo_para_envio_estricto"
    return out
'''

p.write_text(t.rstrip() + append, encoding="utf-8")
print("appended diagnostico")
