# -*- coding: utf-8 -*-
"""
Plantilla unica y variables del modulo CUOTAS_4_MAS (4 cuotas y mas / Excel universo).

INDEPENDIENTE de PREJUDICIAL, COBRANZAS_EXCEL, 1 Cuota, dia siguiente, 3 dias antes y masivos:
- tipo de plantilla y clave envios propios (CUOTAS_4_MAS)
- HTML propio (templates_email/cuotas_4_mas.html; cuerpo identico a cobranzas)
- no se incluye en cron ni en enviar-todas

Siembra idempotente en BD: variables_notificacion + plantillas_notificacion
y vincula plantilla_id en notificaciones_envios.CUOTAS_4_MAS.

HTML canonico: templates_email/cuotas_4_mas.html
"""
from __future__ import annotations

import logging
from pathlib import Path
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

TIPO_CUOTAS_4_MAS = "CUOTAS_4_MAS"
NOMBRE_PLANTILLA_CUOTAS_4_MAS = "4 cuotas y mas - Aviso legal"
NOMBRES_CANONICOS_CUOTAS_4_MAS = (
    NOMBRE_PLANTILLA_CUOTAS_4_MAS,
)

ASUNTO_CUOTAS_4_MAS = "Aviso legal importante - 4 o mas cuotas vencidas | RapiCredit"


def _cargar_cuerpo_html_cuotas_4_mas() -> str:
    path = Path(__file__).resolve().parent / "templates_email" / "cuotas_4_mas.html"
    return path.read_text(encoding="utf-8")


CUERPO_CUOTAS_4_MAS = _cargar_cuerpo_html_cuotas_4_mas()

# Fallback texto plano (si no hay plantilla HTML en BD / pipeline format_map).
ASUNTO_CUOTAS_4_MAS_FALLBACK = ASUNTO_CUOTAS_4_MAS
CUERPO_CUOTAS_4_MAS_FALLBACK = (
    "Estimado(a) {nombre} (cedula {cedula}),\n\n"
    "Aviso legal: su contrato con RapiCredit registra 4 o mas cuotas vencidas "
    "(atraso {dias_atraso} dias; cuota N. {numero_cuota}; vence {fecha_vencimiento_display}; "
    "monto {monto}; total pendiente {total_pendiente_pagar}).\n\n"
    "Conforme a la Clausula Decima Segunda, la falta de pago de dos o mas cuotas "
    "faculta a exigir el saldo total y declarar resuelto el contrato.\n\n"
    "WhatsApp: +58 424-4579934 — https://wa.me/584244579934\n\n"
    "Si ya pago, envie su comprobante de inmediato.\n\n"
    "Departamento de Cobranza\n"
    "RapiCredit, C.A."
)

VARIABLES_DISPONIBLES_CUOTAS_4_MAS = (
    "nombre,nombre_cliente,cedula,dias_atraso,cuotas_atrasadas,"
    "fecha_vencimiento,fecha_vencimiento_display,numero_cuota,monto,"
    "monto_cuota,total_pendiente_pagar,logo_url,LOGO_URL"
)

VARIABLES_MODULO_CUOTAS_4_MAS: List[Dict[str, str]] = [
    {
        "nombre_variable": "nombre",
        "tabla": "clientes",
        "campo_bd": "nombres",
        "descripcion": "Nombre del cliente (CUOTAS_4_MAS / plantillas)",
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
    {
        "nombre_variable": "total_pendiente_pagar",
        "tabla": "prestamos",
        "campo_bd": "saldo",
        "descripcion": "Total pendiente del prestamo",
    },
    {
        "nombre_variable": "logo_url",
        "tabla": "sistema",
        "campo_bd": "FRONTEND_PUBLIC_URL",
        "descripcion": "URL publica del logo Rapicredit (correo)",
    },
    {
        "nombre_variable": "LOGO_URL",
        "tabla": "sistema",
        "campo_bd": "FRONTEND_PUBLIC_URL",
        "descripcion": "Alias de logo_url",
    },
]


def asegurar_variables_cuotas_4_mas(db: Session) -> Dict[str, int]:
    """Inserta variables del modulo si no existen. Idempotente (savepoint por fila)."""
    creadas = 0
    existentes = 0
    for item in VARIABLES_MODULO_CUOTAS_4_MAS:
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
            logger.warning("asegurar_variables_cuotas_4_mas: %s para %s", e, nombre)
            existentes += 1
    return {"variables_creadas": creadas, "variables_existentes": existentes}


def _buscar_plantilla_cuotas_4_mas(db: Session) -> Optional[PlantillaNotificacion]:
    """Preferencia: nombre canonico activo; si no, cualquier CUOTAS_4_MAS activa."""
    p = db.execute(
        select(PlantillaNotificacion).where(
            PlantillaNotificacion.tipo == TIPO_CUOTAS_4_MAS,
            PlantillaNotificacion.nombre.in_(NOMBRES_CANONICOS_CUOTAS_4_MAS),
        )
        .order_by(PlantillaNotificacion.id.asc())
        .limit(1)
    ).scalar_one_or_none()
    if p:
        return p
    return db.execute(
        select(PlantillaNotificacion)
        .where(
            PlantillaNotificacion.tipo == TIPO_CUOTAS_4_MAS,
            PlantillaNotificacion.activa.is_(True),
        )
        .order_by(PlantillaNotificacion.id.asc())
        .limit(1)
    ).scalar_one_or_none()


def asegurar_plantilla_cuotas_4_mas(db: Session, *, forzar_contenido: bool = False) -> PlantillaNotificacion:
    """
    Crea o actualiza la plantilla unica CUOTAS_4_MAS.
    Si ya existe otra CUOTAS_4_MAS activa y forzar_contenido=False, solo asegura
    variables_disponibles / activa / nombre canonico cuando es la nuestra.
    """
    p = _buscar_plantilla_cuotas_4_mas(db)
    if p is None:
        p = PlantillaNotificacion(
            nombre=NOMBRE_PLANTILLA_CUOTAS_4_MAS,
            descripcion=(
                "Plantilla unica del modulo 4 cuotas y mas (CUOTAS_4_MAS). "
                "HTML: cuotas_4_mas.html."
            ),
            tipo=TIPO_CUOTAS_4_MAS,
            asunto=ASUNTO_CUOTAS_4_MAS,
            cuerpo=CUERPO_CUOTAS_4_MAS,
            variables_disponibles=VARIABLES_DISPONIBLES_CUOTAS_4_MAS,
            activa=True,
            zona_horaria="America/Caracas",
        )
        db.add(p)
        db.flush()
        logger.info("Plantilla CUOTAS_4_MAS creada id=%s", p.id)
        return p

    # Actualizar a contenido canonico si es la nuestra o se fuerza
    es_nuestra = (p.nombre or "") in NOMBRES_CANONICOS_CUOTAS_4_MAS
    if forzar_contenido or es_nuestra:
        p.nombre = NOMBRE_PLANTILLA_CUOTAS_4_MAS
        p.asunto = ASUNTO_CUOTAS_4_MAS
        # Recargar HTML desde archivo por si cambio en deploy
        p.cuerpo = _cargar_cuerpo_html_cuotas_4_mas()
        p.descripcion = (
            "Plantilla unica del modulo 4 cuotas y mas (CUOTAS_4_MAS). "
            "HTML: cuotas_4_mas.html. Variables: {{nombre}}, {{cedula}}, "
            "{{cuotas_atrasadas}}, {{dias_atraso}}, {{logo_url}}, etc."
        )
    p.tipo = TIPO_CUOTAS_4_MAS
    p.activa = True
    p.variables_disponibles = VARIABLES_DISPONIBLES_CUOTAS_4_MAS
    if not (p.zona_horaria or "").strip():
        p.zona_horaria = "America/Caracas"
    db.flush()
    return p


def vincular_plantilla_en_envios(db: Session, plantilla_id: int) -> bool:
    """
    Asigna plantilla_id en notificaciones_envios.CUOTAS_4_MAS si falta.
    No sobrescribe un plantilla_id ya configurado distinto.
    """
    cfg = get_notificaciones_envios_dict(db)
    row = cfg.get(TIPO_CUOTAS_4_MAS)
    if not isinstance(row, dict):
        row = {
            "habilitado": True,
            "cco": [],
            "plantilla_id": plantilla_id,
        }
        cfg[TIPO_CUOTAS_4_MAS] = row
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
    cfg[TIPO_CUOTAS_4_MAS] = row
    put_notificaciones_envios_dict(db, cfg)
    return True


def asegurar_modulo_cuotas_4_mas(
    db: Session, *, forzar_contenido_plantilla: bool = False
) -> Dict[str, Any]:
    """
    Configura variables + plantilla unica + vinculo en envios.
    Commit a cargo del llamador (o se hace aqui si el llamador lo prefiere).
    """
    vars_info = asegurar_variables_cuotas_4_mas(db)
    plantilla = asegurar_plantilla_cuotas_4_mas(
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
