# -*- coding: utf-8 -*-
"""
Plantilla unica y variables del modulo PREJUDICIAL (60 dias o mas).

Siembra idempotente en BD: variables_notificacion + plantillas_notificacion
y vincula plantilla_id en notificaciones_envios.PREJUDICIAL.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.plantilla_notificacion import PlantillaNotificacion
from app.models.variable_notificacion import VariableNotificacion
from app.services.notificaciones_envios_store import (
    get_notificaciones_envios_dict,
    put_notificaciones_envios_dict,
)

logger = logging.getLogger(__name__)

TIPO_PREJUDICIAL = "PREJUDICIAL"
NOMBRE_PLANTILLA_PREJUDICIAL = "URGENTE: Pague a tiempo (60 dias o mas)"

ASUNTO_PREJUDICIAL = "URGENTE: Pague a tiempo"

# Cuerpo con {{nombre}} (sustituido en envio). HTML simple (sin PDF adjunto).
CUERPO_PREJUDICIAL = (
    "Estimado(a) {{nombre}},\n\n"
    "Le solicitamos ponerse al dia con el pago de su cuota de manera inmediata. "
    "Evite seguir sumando dias de retraso y prevenga el inicio de acciones legales.\n\n"
    "Si desea regularizar su situacion, comuniquese hoy mismo por nuestras lineas oficiales:\n\n"
    "Linea 1: 0424-4334846 — https://wa.me/584244334846\n"
    "Linea 2: 0424-4249673 — https://wa.me/584244249673\n"
    "Linea 3: 0424-4530836 — https://wa.me/584244530836\n\n"
    "Si ya realizo su pago, envienos su comprobante a cobranza@rapicreditca.com "
    "de inmediato para detener este proceso de notificaciones.\n\n"
    "Atentamente,\n\n"
    "Departamento de Cobranzas\n"
    "Rapicredit"
)

# Fallback para textos por defecto del pipeline ({nombre} estilo format_map).
ASUNTO_PREJUDICIAL_FALLBACK = ASUNTO_PREJUDICIAL
CUERPO_PREJUDICIAL_FALLBACK = (
    "Estimado(a) {nombre},\n\n"
    "Le solicitamos ponerse al dia con el pago de su cuota de manera inmediata. "
    "Evite seguir sumando dias de retraso y prevenga el inicio de acciones legales.\n\n"
    "Si desea regularizar su situacion, comuniquese hoy mismo por nuestras lineas oficiales:\n\n"
    "Linea 1: 0424-4334846 — https://wa.me/584244334846\n"
    "Linea 2: 0424-4249673 — https://wa.me/584244249673\n"
    "Linea 3: 0424-4530836 — https://wa.me/584244530836\n\n"
    "Si ya realizo su pago, envienos su comprobante a cobranza@rapicreditca.com "
    "de inmediato para detener este proceso de notificaciones.\n\n"
    "Atentamente,\n\n"
    "Departamento de Cobranzas\n"
    "Rapicredit"
)

VARIABLES_DISPONIBLES_PREJUDICIAL = (
    "nombre,cedula,dias_atraso,cuotas_atrasadas,"
    "fecha_vencimiento,fecha_vencimiento_display,numero_cuota,monto"
)

# Variables del modulo (token {{nombre_variable}} en plantillas).
VARIABLES_MODULO_PREJUDICIAL: List[Dict[str, str]] = [
    {
        "nombre_variable": "nombre",
        "tabla": "clientes",
        "campo_bd": "nombres",
        "descripcion": "Nombre del cliente (PREJUDICIAL / plantillas)",
    },
    {
        "nombre_variable": "nombre_cliente",
        "tabla": "clientes",
        "campo_bd": "nombres",
        "descripcion": "Nombres del cliente",
    },
    {
        "nombre_variable": "cedula",
        "tabla": "clientes",
        "campo_bd": "cedula",
        "descripcion": "Cedula de identidad",
    },
    {
        "nombre_variable": "dias_atraso",
        "tabla": "cuotas",
        "campo_bd": "dias_mora",
        "descripcion": "Dias de atraso de la cuota de referencia",
    },
    {
        "nombre_variable": "cuotas_atrasadas",
        "tabla": "prestamos",
        "campo_bd": "conteo",
        "descripcion": "Cantidad de cuotas en atraso del prestamo",
    },
    {
        "nombre_variable": "fecha_vencimiento",
        "tabla": "cuotas",
        "campo_bd": "fecha_vencimiento",
        "descripcion": "Fecha de vencimiento",
    },
    {
        "nombre_variable": "fecha_vencimiento_display",
        "tabla": "cuotas",
        "campo_bd": "fecha_vencimiento",
        "descripcion": "Fecha de vencimiento legible",
    },
    {
        "nombre_variable": "numero_cuota",
        "tabla": "cuotas",
        "campo_bd": "numero_cuota",
        "descripcion": "Numero de cuota",
    },
    {
        "nombre_variable": "monto",
        "tabla": "cuotas",
        "campo_bd": "monto",
        "descripcion": "Monto de la cuota (alias de monto_cuota)",
    },
    {
        "nombre_variable": "monto_cuota",
        "tabla": "cuotas",
        "campo_bd": "monto",
        "descripcion": "Monto de la cuota",
    },
]


def asegurar_variables_prejudicial(db: Session) -> Dict[str, int]:
    """Inserta variables del modulo si no existen. Idempotente (savepoint por fila)."""
    creadas = 0
    existentes = 0
    for item in VARIABLES_MODULO_PREJUDICIAL:
        nombre = item["nombre_variable"]
        existing = db.execute(
            select(VariableNotificacion).where(VariableNotificacion.nombre_variable == nombre)
        ).scalar_one_or_none()
        if existing:
            existentes += 1
            if not existing.activa:
                existing.activa = True
            continue
        try:
            with db.begin_nested():
                db.add(
                    VariableNotificacion(
                        nombre_variable=nombre,
                        tabla=item["tabla"],
                        campo_bd=item["campo_bd"],
                        descripcion=item.get("descripcion"),
                        activa=True,
                    )
                )
                db.flush()
            creadas += 1
        except Exception as e:
            logger.warning("asegurar_variables_prejudicial: %s para %s", e, nombre)
            existentes += 1
    return {"variables_creadas": creadas, "variables_existentes": existentes}


def _buscar_plantilla_prejudicial(db: Session) -> Optional[PlantillaNotificacion]:
    """Preferencia: nombre canonico activo; si no, cualquier PREJUDICIAL activa."""
    p = db.execute(
        select(PlantillaNotificacion).where(
            PlantillaNotificacion.tipo == TIPO_PREJUDICIAL,
            PlantillaNotificacion.nombre == NOMBRE_PLANTILLA_PREJUDICIAL,
        )
    ).scalar_one_or_none()
    if p:
        return p
    return db.execute(
        select(PlantillaNotificacion)
        .where(
            PlantillaNotificacion.tipo == TIPO_PREJUDICIAL,
            PlantillaNotificacion.activa.is_(True),
        )
        .order_by(PlantillaNotificacion.id.asc())
        .limit(1)
    ).scalar_one_or_none()


def asegurar_plantilla_prejudicial(db: Session, *, forzar_contenido: bool = False) -> PlantillaNotificacion:
    """
    Crea o actualiza la plantilla unica PREJUDICIAL.
    Si ya existe otra PREJUDICIAL activa y forzar_contenido=False, solo asegura
    variables_disponibles / activa / nombre canonico cuando es la nuestra.
    """
    p = _buscar_plantilla_prejudicial(db)
    if p is None:
        p = PlantillaNotificacion(
            nombre=NOMBRE_PLANTILLA_PREJUDICIAL,
            descripcion=(
                "Plantilla unica del modulo 60 dias o mas (PREJUDICIAL). "
                "Variable principal: {{nombre}}."
            ),
            tipo=TIPO_PREJUDICIAL,
            asunto=ASUNTO_PREJUDICIAL,
            cuerpo=CUERPO_PREJUDICIAL,
            variables_disponibles=VARIABLES_DISPONIBLES_PREJUDICIAL,
            activa=True,
            zona_horaria="America/Caracas",
        )
        db.add(p)
        db.flush()
        logger.info("Plantilla PREJUDICIAL creada id=%s", p.id)
        return p

    # Actualizar a contenido canonico si es la nuestra o se fuerza
    es_nuestra = (p.nombre or "") == NOMBRE_PLANTILLA_PREJUDICIAL
    if forzar_contenido or es_nuestra:
        p.nombre = NOMBRE_PLANTILLA_PREJUDICIAL
        p.asunto = ASUNTO_PREJUDICIAL
        p.cuerpo = CUERPO_PREJUDICIAL
        p.descripcion = (
            "Plantilla unica del modulo 60 dias o mas (PREJUDICIAL). "
            "Variable principal: {{nombre}}."
        )
    p.tipo = TIPO_PREJUDICIAL
    p.activa = True
    p.variables_disponibles = VARIABLES_DISPONIBLES_PREJUDICIAL
    if not (p.zona_horaria or "").strip():
        p.zona_horaria = "America/Caracas"
    db.flush()
    return p


def vincular_plantilla_en_envios(db: Session, plantilla_id: int) -> bool:
    """
    Asigna plantilla_id en notificaciones_envios.PREJUDICIAL si falta.
    No sobrescribe un plantilla_id ya configurado distinto.
    """
    cfg = get_notificaciones_envios_dict(db)
    row = cfg.get(TIPO_PREJUDICIAL)
    if not isinstance(row, dict):
        row = {
            "habilitado": True,
            "cco": False,
            "plantilla_id": plantilla_id,
        }
        cfg[TIPO_PREJUDICIAL] = row
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
    cfg[TIPO_PREJUDICIAL] = row
    put_notificaciones_envios_dict(db, cfg)
    return True


def asegurar_modulo_prejudicial(
    db: Session, *, forzar_contenido_plantilla: bool = False
) -> Dict[str, Any]:
    """
    Configura variables + plantilla unica + vinculo en envios.
    Commit a cargo del llamador (o se hace aqui si el llamador lo prefiere).
    """
    vars_info = asegurar_variables_prejudicial(db)
    plantilla = asegurar_plantilla_prejudicial(
        db, forzar_contenido=forzar_contenido_plantilla
    )
    vinculado = vincular_plantilla_en_envios(db, plantilla.id)
    return {
        **vars_info,
        "plantilla_id": plantilla.id,
        "plantilla_nombre": plantilla.nombre,
        "plantilla_asunto": plantilla.asunto,
        "envios_vinculado": vinculado,
    }
