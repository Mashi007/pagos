# -*- coding: utf-8 -*-
"""
Prueba de envio completo (plantilla + Carta PDF + PDFs fijos).
Una sola implementacion: el router solo delega aqui (evita dobles vias con logica duplicada).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

TIPOS_PRUEBA_PAQUETE = frozenset(
    {
        "PAGO_1_DIA_ATRASADO",
        "PAGO_3_DIAS_ATRASADO",
        "PAGO_5_DIAS_ATRASADO",
        "PAGO_30_DIAS_ATRASADO",
        "PAGO_2_DIAS_ANTES_PENDIENTE",
        "PREJUDICIAL",
    }
)



def parse_destinos_prueba(payload: dict) -> List[str]:
    raw = payload.get("destinos") or payload.get("emails") or []
    if isinstance(raw, str):
        out = [raw]
    elif isinstance(raw, list):
        out = [str(x).strip() for x in raw if x]
    else:
        out = [str(raw).strip()] if raw else []
    return [d for d in out if d and "@" in d]


def ejecutar_enviar_prueba_paquete(db: Session, payload: dict) -> Dict[str, Any]:
    from app.api.v1.endpoints import notificaciones_tabs as nt
    from app.api.v1.endpoints.notificaciones import (
        get_notificaciones_envios_config,
    )
    from app.services.notificacion_service import get_primer_item_ejemplo_paquete_prueba

    tipo = (payload.get("tipo") or "PAGO_1_DIA_ATRASADO").strip()
    if tipo not in TIPOS_PRUEBA_PAQUETE:
        raise HTTPException(
            status_code=422,
            detail=f"tipo debe ser uno de: {', '.join(sorted(TIPOS_PRUEBA_PAQUETE))}",
        )
    destinos = parse_destinos_prueba(payload)
    if not destinos:
        raise HTTPException(
            status_code=422,
            detail="Indique al menos un destino en destinos (lista de emails).",
        )

    item = get_primer_item_ejemplo_paquete_prueba(db, tipo)
    if not item:
        raise HTTPException(
            status_code=404,
            detail="No hay datos de ejemplo en BD para este criterio. Debe existir al menos un cliente en la lista correspondiente.",
        )

    if tipo in (
        "PAGO_1_DIA_ATRASADO",
        "PAGO_3_DIAS_ATRASADO",
        "PAGO_5_DIAS_ATRASADO",
        "PAGO_30_DIAS_ATRASADO",
    ):
        get_tipo = nt._tipo_retrasadas
        asunto = "Cuenta con cuota atrasada - Rapicredit"
        cuerpo = (
            "Estimado/a {nombre} (cedula {cedula}),\n\n"
            "Le recordamos que tiene una cuota en mora.\n"
            "Fecha de vencimiento: {fecha_vencimiento}\n"
            "Numero de cuota: {numero_cuota}\n"
            "Monto: {monto}\n\n"
            "Por favor regularice su pago lo antes posible.\n\n"
            "Saludos,\nRapicredit"
        )
    elif tipo == "PAGO_2_DIAS_ANTES_PENDIENTE":
        get_tipo = nt._tipo_pago_2_dias_antes_pendiente
        asunto = "Recordatorio: cuota por vencer - Rapicredit"
        cuerpo = (
            "Estimado/a {nombre} (cedula {cedula}),\n\n"
            "Le recordamos que tiene una cuota por vencer.\n"
            "Fecha de vencimiento: {fecha_vencimiento}\n"
            "Numero de cuota: {numero_cuota}\n"
            "Monto: {monto}\n\n"
            "Por favor realice el pago a tiempo.\n\n"
            "Saludos,\nRapicredit"
        )
    else:
        get_tipo = nt._tipo_prejudicial
        asunto = "Aviso prejudicial - Rapicredit"
        cuerpo = (
            "Estimado/a {nombre} (cedula {cedula}),\n\n"
            "Le informamos que su cuenta presenta varias cuotas en mora.\n"
            "Fecha de vencimiento de referencia: {fecha_vencimiento}\n"
            "Cuota de referencia: {numero_cuota}\n"
            "Monto de referencia: {monto}\n\n"
            "Por favor contacte a la entidad para regularizar su situacion.\n\n"
            "Saludos,\nRapicredit"
        )

    # Igual que enviar-caso-manual: la prueba debe enviar aunque el toggle Envio este apagado
    # en la fila del criterio que aplica al item (p. ej. PAGO_3 vs PAGO_1 en retrasadas).
    tipo_resuelto = get_tipo(item)
    config_envios = nt._config_envios_forzar_habilitado_caso(
        get_notificaciones_envios_config(db),
        tipo_resuelto,
    )

    try:
        res = nt._enviar_correos_items(
            [item],
            asunto,
            cuerpo,
            config_envios,
            get_tipo,
            db,
            forzar_destinos_prueba=destinos,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    out = dict(res)
    enviados = int(out.get("enviados") or 0)
    if enviados == 0:
        omit_pkg = int(out.get("omitidos_paquete_incompleto") or 0)
        omit_cfg = int(out.get("omitidos_config") or 0)
        if omit_pkg > 0:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Paquete incompleto (NOTIFICACIONES_PAQUETE_ESTRICTO): se exige Carta_Cobranza.pdf "
                    "valido (%PDF) y plantilla de correo activa/completa. "
                    "Alternativa solo prueba forzada: NOTIFICACIONES_PAQUETE_RELAX_SOLO_PRUEBA_DESTINO=true en .env. Emergencia global: NOTIFICACIONES_PAQUETE_ESTRICTO=false."
                ),
            )
        if omit_cfg > 0:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Ningun envio para este criterio: el tipo esta con envio desactivado en "
                    f"Configuracion > Notificaciones (omitidos_config={omit_cfg}). Active Envio en la pestana del caso."
                ),
            )
        raise HTTPException(
            status_code=422,
            detail=(
                "No se envio la prueba de paquete. Revise plantilla activa, SMTP de notificaciones y destinos."
            ),
        )

    out["mensaje"] = "Prueba de paquete completo enviada (plantilla + PDF carta + PDFs fijos)."
    out["tipo"] = tipo
    out["destinos"] = destinos
    return out

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
        get_plantilla_asunto_cuerpo,
        build_contexto_cobranza_para_item,
        contexto_cobranza_aplica_a_prestamo,
        plantilla_usa_variables_cobranza,
    )
    from app.services.notificacion_service import get_primer_item_ejemplo_paquete_prueba
    from app.models.plantilla_notificacion import PlantillaNotificacion
    from app.services.carta_cobranza_pdf import generar_carta_cobranza_pdf
    from app.services.adjunto_fijo_cobranza import get_adjunto_fijo_cobranza_bytes, get_adjuntos_fijos_por_caso

    tipo = (tipo or "PAGO_1_DIA_ATRASADO").strip()
    if tipo not in TIPOS_PRUEBA_PAQUETE:
        raise HTTPException(
            status_code=422,
            detail=f"tipo debe ser uno de: {', '.join(sorted(TIPOS_PRUEBA_PAQUETE))}",
        )

    item = get_primer_item_ejemplo_paquete_prueba(db, tipo)
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

    if tipo in (
        "PAGO_1_DIA_ATRASADO",
        "PAGO_3_DIAS_ATRASADO",
        "PAGO_5_DIAS_ATRASADO",
        "PAGO_30_DIAS_ATRASADO",
    ):
        get_tipo = nt._tipo_retrasadas
        asunto_base = "Cuenta con cuota atrasada - Rapicredit"
        cuerpo_base = "Prueba diagnostico"
    elif tipo == "PAGO_2_DIAS_ANTES_PENDIENTE":
        get_tipo = nt._tipo_pago_2_dias_antes_pendiente
        asunto_base = "Recordatorio: cuota por vencer - Rapicredit"
        cuerpo_base = "Prueba diagnostico"
    else:
        get_tipo = nt._tipo_prejudicial
        asunto_base = "Aviso prejudicial - Rapicredit"
        cuerpo_base = "Prueba diagnostico"

    item = deepcopy(item)
    paquete_estricto = bool(getattr(settings, "NOTIFICACIONES_PAQUETE_ESTRICTO", True))
    tipo_res = get_tipo(item)
    config_envios = nt._config_envios_forzar_habilitado_caso(
        get_notificaciones_envios_config(db),
        tipo_res,
    )
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

    if db and item.get("prestamo_id"):
        ctx_existente = item.get("contexto_cobranza")
        if ctx_existente is not None and not contexto_cobranza_aplica_a_prestamo(
            ctx_existente, item.get("prestamo_id")
        ):
            item.pop("contexto_cobranza", None)
            item.pop("_correlativo_envio", None)

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
