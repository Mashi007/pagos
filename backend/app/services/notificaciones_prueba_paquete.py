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
        "PREJUDICIAL",
    }
)


def primer_item_ejemplo_por_tipo(data: dict, tipo: str) -> Optional[dict]:
    """Primer registro real por criterio (misma fuente que listados de envio)."""
    if tipo == "PAGO_1_DIA_ATRASADO":
        return data["dias_1_retraso"][0] if data.get("dias_1_retraso") else None
    if tipo == "PAGO_3_DIAS_ATRASADO":
        return data["dias_3_retraso"][0] if data.get("dias_3_retraso") else None
    if tipo == "PAGO_5_DIAS_ATRASADO":
        return data["dias_5_retraso"][0] if data.get("dias_5_retraso") else None
    if tipo == "PREJUDICIAL":
        return data["prejudicial"][0] if data.get("prejudicial") else None
    return None


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
        get_notificaciones_tabs_data,
    )

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

    data = get_notificaciones_tabs_data(db)
    item = primer_item_ejemplo_por_tipo(data, tipo)
    if not item:
        raise HTTPException(
            status_code=404,
            detail="No hay datos de ejemplo en BD para este criterio. Debe existir al menos un cliente en la lista correspondiente.",
        )

    config_envios = get_notificaciones_envios_config(db)

    if tipo in ("PAGO_1_DIA_ATRASADO", "PAGO_3_DIAS_ATRASADO", "PAGO_5_DIAS_ATRASADO"):
        get_tipo = nt._tipo_retrasadas
        asunto = "Cuenta con cuota atrasada - Rapicredit"
        cuerpo = (
            "Estimado/a {nombre} (cédula {cedula}),\n\n"
            "Le recordamos que tiene una cuota en mora.\n"
            "Fecha de vencimiento: {fecha_vencimiento}\n"
            "Número de cuota: {numero_cuota}\n"
            "Monto: {monto}\n\n"
            "Por favor regularice su pago lo antes posible.\n\n"
            "Saludos,\nRapicredit"
        )
    else:
        get_tipo = nt._tipo_prejudicial
        asunto = "Aviso prejudicial - Rapicredit"
        cuerpo = (
            "Estimado/a {nombre} (cédula {cedula}),\n\n"
            "Le informamos que su cuenta presenta varias cuotas en mora.\n"
            "Fecha de vencimiento de referencia: {fecha_vencimiento}\n"
            "Cuota de referencia: {numero_cuota}\n"
            "Monto de referencia: {monto}\n\n"
            "Por favor contacte a la entidad para regularizar su situación.\n\n"
            "Saludos,\nRapicredit"
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
    out["mensaje"] = "Prueba de paquete completo enviada (plantilla + PDF carta + PDFs fijos)."
    out["tipo"] = tipo
    out["destinos"] = destinos
    return out
