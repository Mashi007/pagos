# -*- coding: utf-8 -*-
"""Plantilla unica ESTADO_CUENTA (Notificaciones > Estado de cuenta)."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.plantilla_notificacion import PlantillaNotificacion
from app.services.notificaciones_envios_store import (
    get_notificaciones_envios_dict,
    put_notificaciones_envios_dict,
)

logger = logging.getLogger(__name__)

TIPO_ESTADO_CUENTA = "ESTADO_CUENTA"
NOMBRE_PLANTILLA = "Estado de cuenta"
ASUNTO_ESTADO_CUENTA = "VERIFICA TU ESTADO DE CUENTA"

VARIABLES_DISPONIBLES = "nombre,cedula,logo_url,LOGO_URL"


def _cargar_cuerpo_html() -> str:
    path = Path(__file__).resolve().parent / "templates_email" / "estado_cuenta_notif.html"
    return path.read_text(encoding="utf-8")


CUERPO_ESTADO_CUENTA = _cargar_cuerpo_html()

ASUNTO_ESTADO_CUENTA_FALLBACK = ASUNTO_ESTADO_CUENTA
CUERPO_ESTADO_CUENTA_FALLBACK = (
    "Estimado cliente, le enviamos adjunto su Estado de Cuenta en PDF. "
    "Le solicitamos analizar el detalle de sus cuotas pendientes.\n\n"
    "Para realizar y registrar su pago de forma rápida, ingrese en nuestro enlace oficial:\n"
    "https://rapicredit.onrender.com/pagos/rapicredit-cobros\n\n"
    "Si tiene dudas sobre su saldo, escriba a nuestras líneas de atención:\n"
    "Línea 1: https://wa.me/584244334846\n"
    "Línea 2: https://wa.me/584244249673\n"
    "Línea 3: https://wa.me/584244530836\n\n"
    "¡Estamos a su disposición!\n"
)


def _buscar_plantilla(db: Session) -> Optional[PlantillaNotificacion]:
    p = db.execute(
        select(PlantillaNotificacion)
        .where(
            PlantillaNotificacion.tipo == TIPO_ESTADO_CUENTA,
            PlantillaNotificacion.nombre == NOMBRE_PLANTILLA,
        )
        .order_by(PlantillaNotificacion.id.asc())
        .limit(1)
    ).scalar_one_or_none()
    if p:
        return p
    return db.execute(
        select(PlantillaNotificacion)
        .where(
            PlantillaNotificacion.tipo == TIPO_ESTADO_CUENTA,
            PlantillaNotificacion.activa.is_(True),
        )
        .order_by(PlantillaNotificacion.id.asc())
        .limit(1)
    ).scalar_one_or_none()


def asegurar_plantilla_estado_cuenta(
    db: Session, *, forzar_contenido: bool = False
) -> PlantillaNotificacion:
    p = _buscar_plantilla(db)
    if p is None:
        p = PlantillaNotificacion(
            nombre=NOMBRE_PLANTILLA,
            descripcion="Notificacion masiva Estado de cuenta (PDF adjunto). HTML: estado_cuenta_notif.html.",
            tipo=TIPO_ESTADO_CUENTA,
            asunto=ASUNTO_ESTADO_CUENTA,
            cuerpo=CUERPO_ESTADO_CUENTA,
            variables_disponibles=VARIABLES_DISPONIBLES,
            activa=True,
            zona_horaria="America/Caracas",
        )
        db.add(p)
        db.flush()
        logger.info("Plantilla ESTADO_CUENTA creada id=%s", p.id)
        return p

    es_nuestra = (p.nombre or "") == NOMBRE_PLANTILLA
    if forzar_contenido or es_nuestra:
        p.nombre = NOMBRE_PLANTILLA
        p.asunto = ASUNTO_ESTADO_CUENTA
        p.cuerpo = _cargar_cuerpo_html()
        p.descripcion = (
            "Notificacion masiva Estado de cuenta (PDF adjunto). "
            "HTML: estado_cuenta_notif.html."
        )
    p.tipo = TIPO_ESTADO_CUENTA
    p.activa = True
    p.variables_disponibles = VARIABLES_DISPONIBLES
    if not (p.zona_horaria or "").strip():
        p.zona_horaria = "America/Caracas"
    db.flush()
    return p


def vincular_plantilla_en_envios(db: Session, plantilla_id: int) -> bool:
    cfg = get_notificaciones_envios_dict(db)
    row = cfg.get(TIPO_ESTADO_CUENTA)
    if not isinstance(row, dict):
        row = {
            "habilitado": True,
            "cco": [],
            "plantilla_id": plantilla_id,
            "incluir_pdf_anexo": False,
            "incluir_adjuntos_fijos": False,
        }
        cfg[TIPO_ESTADO_CUENTA] = row
        put_notificaciones_envios_dict(db, cfg)
        return True

    raw = row.get("plantilla_id")
    tiene = False
    try:
        if raw is not None and str(raw).strip() != "":
            tiene = int(raw) > 0
    except (TypeError, ValueError):
        tiene = False
    if tiene:
        return False

    row = dict(row)
    row["plantilla_id"] = plantilla_id
    cfg[TIPO_ESTADO_CUENTA] = row
    put_notificaciones_envios_dict(db, cfg)
    return True


def asegurar_modulo_estado_cuenta(
    db: Session, *, forzar_contenido_plantilla: bool = False
) -> Dict[str, Any]:
    plantilla = asegurar_plantilla_estado_cuenta(
        db, forzar_contenido=forzar_contenido_plantilla
    )
    vinculado = vincular_plantilla_en_envios(db, int(plantilla.id))
    return {
        "plantilla_id": int(plantilla.id),
        "vinculado_envios": vinculado,
    }
