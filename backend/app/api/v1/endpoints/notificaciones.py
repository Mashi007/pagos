"""
Endpoints de notificaciones a clientes retrasados.
Todo el router exige rol admin (Depends(require_admin) a nivel de APIRouter).
Datos reales desde BD: cuotas (fecha_vencimiento, pagado) y clientes.
Reglas: 5 pestañas por días hasta vencimiento y mora 61+.
Configuración de envíos (habilitado/CCO por tipo) desde tabla configuracion (notificaciones_envios).
CRUD de plantillas en plantillas_notificacion; envío puede usar plantilla por tipo vía plantilla_id en config.
"""
import json
import os
import uuid
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Body, Query, File, UploadFile, BackgroundTasks
from fastapi.responses import Response, JSONResponse, RedirectResponse
from starlette.requests import Request

from app.core.deps import require_admin
from app.schemas.auth import UserResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.serializers import to_finite_float_or_zero
from app.services.cuota_estado import hoy_negocio, parse_fecha_referencia_negocio
from app.services.notificacion_service import (
    CUOTA_ESTADO_NO_PAGADA_PARA_NOTIF,
    ESTADOS_CUOTA_VENCIDO_Y_MORA,
    PREJUDICIAL_MIN_CUOTAS_VENCIDO_MORA,
    SALDO_PENDIENTE_CUOTA,
    TOL_SALDO_CUOTA_NOTIFICACION,
    build_cuotas_pendiente_2_dias_antes_items,
    contar_cuotas_atraso_por_prestamos,
    enriquecer_items_notificacion_revision_manual,
    format_cuota_item,
    get_cuotas_pendientes_por_vencimientos,
    sum_saldo_pendiente_total_por_prestamos,
    _item,
    _item_tab,
)
from app.models.cuota import Cuota
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.configuracion import Configuracion
from app.models.plantilla_notificacion import PlantillaNotificacion
from app.models.variable_notificacion import VariableNotificacion
from app.models.envio_notificacion import EnvioNotificacion
from app.models.envio_notificacion_adjunto import EnvioNotificacionAdjunto
from app.models.adjunto_fijo_cobranza_documento import AdjuntoFijoCobranzaDocumento
from app.services.notificacion_logging import (
    log_historial_consulta,
    log_historial_excel,
    log_historial_comprobante,
    log_historial_fallo,
)

logger = logging.getLogger(__name__)

from app.services.notificaciones_envios_store import (
    coerce_modo_pruebas_notificaciones,
    get_notificaciones_envios_dict,
)
from app.services.notificaciones_exclusion_desistimiento import (
    cliente_bloqueado_por_desistimiento,
)

router = APIRouter(dependencies=[Depends(require_admin)])


def get_notificaciones_envios_config(db: Session) -> dict:
    """Carga la configuracion de envios por tipo (habilitado, cco, plantilla_id, programador) desde BD."""
    return get_notificaciones_envios_dict(db)


# Las funciones _item e _item_tab están ahora en app.services.notificacion_service
# para evitar duplicación y facilitar mantenimiento. Se importan desde allí.


# --- Helpers plantillas ---

def _plantilla_to_dict(p: PlantillaNotificacion) -> dict:
    """Serializa PlantillaNotificacion al formato esperado por el frontend."""
    return {
        "id": p.id,
        "nombre": p.nombre or "",
        "descripcion": getattr(p, "descripcion", None),
        "tipo": p.tipo or "",
        "asunto": p.asunto or "",
        "cuerpo": p.cuerpo or "",
        "variables_disponibles": getattr(p, "variables_disponibles", None),
        "activa": bool(p.activa),
        "zona_horaria": p.zona_horaria or "America/Caracas",
        "fecha_creacion": p.fecha_creacion.isoformat() if p.fecha_creacion else "",
        "fecha_actualizacion": p.fecha_actualizacion.isoformat() if p.fecha_actualizacion else "",
    }


# Variables que indican que la plantilla es de cobranza y necesita contexto_cobranza para renderizar
_VARS_COBRANZA = (
    "{{FECHA_CARTA}}",
    "{{PRESTAMOS.ID}}",
    "{{IDPRESTAMO}}",
    "{{NUMEROCORRELATIVO}}",
    "{{CLIENTES.NOMBRE_COMPLETO}}",
    "{{CLIENTES.CEDULA}}",
    "{{TABLA_CUOTAS_PENDIENTES}}",
    "{{#CUOTAS.VENCIMIENTOS}}",
    "{{CUOTAS_VENCIDAS}}",
    "{{FECHAS_CUOTAS_PENDIENTES}}",
)


def plantilla_usa_variables_cobranza(plantilla) -> bool:
    """True si asunto o cuerpo contienen variables de plantilla COBRANZA (necesitan contexto_cobranza)."""
    if not plantilla:
        return False
    texto = (getattr(plantilla, "asunto", None) or "") + " " + (getattr(plantilla, "cuerpo", None) or "")
    return any(v in texto for v in _VARS_COBRANZA)


def _format_item_texto_plantilla_por_defecto(texto: str, item: dict) -> str:
    """
    Sustituye {nombre}, {fecha_vencimiento}, {fecha_vencimiento_display}, etc. en textos por defecto
    (sin plantilla en BD). format_map con claves faltantes -> cadena vacia (no TypeError por kwargs extra).
    """
    if not texto:
        return ""
    nombre = item.get("nombre") or "Cliente"
    cedula = item.get("cedula") or ""
    fecha_v = item.get("fecha_vencimiento") or ""
    fecha_disp = (item.get("fecha_vencimiento_display") or "").strip() or str(fecha_v)
    numero_cuota = item.get("numero_cuota")
    monto = item.get("monto_cuota")
    if monto is None and item.get("monto") is not None:
        monto = item.get("monto")

    class _Map(dict):
        def __missing__(self, key):
            return ""

    m = _Map(
        nombre=nombre,
        cedula=cedula,
        fecha_vencimiento=str(fecha_v),
        fecha_vencimiento_display=str(fecha_disp),
        numero_cuota=str(numero_cuota) if numero_cuota is not None else "",
        monto=str(monto) if monto is not None else "",
        dias_atraso=str(item.get("dias_atraso"))
        if item.get("dias_atraso") is not None
        else "",
        cuotas_atrasadas=str(item.get("cuotas_atrasadas"))
        if item.get("cuotas_atrasadas") is not None
        else "",
    )
    return texto.format_map(m)


def _sustituir_variables(texto: str, item: dict) -> str:
    """
    Reemplaza variables {{variable}} en texto.
    Fijas: nombre, cedula, fecha_vencimiento, fecha_vencimiento_display (texto legible),
    numero_cuota, monto (desde monto_cuota), dias_atraso, cuotas_atrasadas.
    Cualquier otra clave presente en item (ej. telefono, correo) se sustituye tambien para variables personalizadas.
    """
    if not texto:
        return ""
    nombre = item.get("nombre") or "Cliente"
    cedula = item.get("cedula") or ""
    tratamiento = item.get("tratamiento") or "Sr/Sra."
    fecha_v = item.get("fecha_vencimiento") or ""
    numero_cuota = item.get("numero_cuota")
    monto = item.get("monto_cuota")
    if monto is None and item.get("monto") is not None:
        monto = item.get("monto")
    dias_atraso = item.get("dias_atraso")
    cuotas_atrasadas = item.get("cuotas_atrasadas")
    fecha_disp = (item.get("fecha_vencimiento_display") or "").strip() or str(fecha_v)
    replacements = {
        "{{nombre}}": str(nombre),
        "{{cedula}}": str(cedula),
        "{{fecha_vencimiento}}": str(fecha_v),
        "{{fecha_vencimiento_display}}": str(fecha_disp),
        "{{numero_cuota}}": str(numero_cuota) if numero_cuota is not None else "",
        "{{monto}}": str(monto) if monto is not None else "",
        "{{dias_atraso}}": str(dias_atraso) if dias_atraso is not None else "",
        "{{cuotas_atrasadas}}": str(cuotas_atrasadas)
        if cuotas_atrasadas is not None
        else "",
    }
    result = texto
    for key, val in replacements.items():
        result = result.replace(key, val)
    # Variables personalizadas: cualquier clave del item (telefono, correo, etc.)
    for k, v in item.items():
        if k in (
            "nombre",
            "cedula",
            "fecha_vencimiento",
            "fecha_vencimiento_display",
            "numero_cuota",
            "monto_cuota",
            "dias_atraso",
            "cuotas_atrasadas",
        ):
            continue
        token = "{{" + str(k) + "}}"
        if token in result:
            result = result.replace(token, str(v) if v is not None else "")
    return result



def _item_placeholder_pruebas() -> dict:
    """Item con valores placeholder para modo pruebas: las variables se mantienen como {{nombre}}, etc."""
    return {
        "nombre": "{{nombre}}",
        "cedula": "{{cedula}}",
        "fecha_vencimiento": "{{fecha_vencimiento}}",
        "fecha_vencimiento_display": "{{fecha_vencimiento_display}}",
        "numero_cuota": "{{numero_cuota}}",
        "monto_cuota": "{{monto}}",
        "dias_atraso": "{{dias_atraso}}",
        "cuotas_atrasadas": "{{cuotas_atrasadas}}",
    }


def _contexto_cobranza_placeholder() -> dict:
    """Contexto de cobranza con placeholders para modo pruebas (variables visibles, sin datos reales)."""
    return {
        "CLIENTES.TRATAMIENTO": "{{CLIENTES.TRATAMIENTO}}",
        "CLIENTES.NOMBRE_COMPLETO": "{{CLIENTES.NOMBRE_COMPLETO}}",
        "CLIENTES.CEDULA": "{{CLIENTES.CEDULA}}",
        "PRESTAMOS.ID": "{{PRESTAMOS.ID}}",
        "IDPRESTAMO": "{{IDPRESTAMO}}",
        "NUMEROCORRELATIVO": "{{NUMEROCORRELATIVO}}",
        "TOTAL_ADEUDADO": "{{TOTAL_ADEUDADO}}",
        "FECHA_CARTA": "{{FECHA_CARTA}}",
        "LOGO_URL": "{{LOGO_URL}}",
        "CUOTAS.VENCIMIENTOS": [
            {"numero_cuota": "{{CUOTA.NUMERO}}", "fecha_vencimiento": "{{CUOTA.FECHA_VENCIMIENTO}}", "monto": "{{CUOTA.MONTO}}"}
        ],
        "cuotas_vencidas": [
            {"numero": "{{CUOTA.NUMERO}}", "fecha_vencimiento": "{{CUOTA.FECHA_VENCIMIENTO}}", "monto": "{{CUOTA.MONTO}}"}
        ],
        "CUOTAS_VENCIDAS": "{{CUOTAS_VENCIDAS}}",
        "FECHAS_CUOTAS_PENDIENTES": "{{FECHAS_CUOTAS_PENDIENTES}}",
    }


def get_plantilla_asunto_cuerpo(db: Session, plantilla_id: Optional[int], item: dict, asunto_default: str, cuerpo_default: str, modo_pruebas: bool = False) -> tuple:
    """
    Si plantilla_id es vÃƒÂ¡lido y la plantilla existe, devuelve (asunto, cuerpo) con variables sustituidas.
    Para plantillas tipo COBRANZA, si item tiene 'contexto_cobranza', se usa el motor de cobranza
    ({{TABLA.CAMPO}} y bloque {{#CUOTAS.VENCIMIENTOS}}). Si no, se usa _sustituir_variables.
    Si modo_pruebas=True, se usan placeholders para que las variables se vean (no datos reales).
    """
    if modo_pruebas:
        item = {**_item_placeholder_pruebas(), **{k: "{{" + str(k) + "}}" for k, v in item.items() if k != "contexto_cobranza"}}
    if plantilla_id:
        plantilla = db.get(PlantillaNotificacion, plantilla_id)
        if plantilla and plantilla.activa:
            contexto_cobranza = item.get("contexto_cobranza")
            usa_cobranza = getattr(plantilla, "tipo", None) == "COBRANZA" or plantilla_usa_variables_cobranza(plantilla)
            if usa_cobranza:
                if modo_pruebas:
                    contexto_cobranza = _contexto_cobranza_placeholder()
                elif not isinstance(contexto_cobranza, dict):
                    contexto_cobranza = None
            if usa_cobranza and isinstance(contexto_cobranza, dict):
                from app.services.plantilla_cobranza import render_plantilla_cobranza
                if "LOGO_URL" not in contexto_cobranza:
                    try:
                        from app.core.config import settings
                        base = (getattr(settings, "FRONTEND_PUBLIC_URL", None) or "https://rapicredit.onrender.com/pagos").rstrip("/")
                    except Exception:
                        base = "https://rapicredit.onrender.com/pagos"
                    contexto_cobranza["LOGO_URL"] = f"{base}/logos/rapicredit-public.png"
                asunto = render_plantilla_cobranza(plantilla.asunto, contexto_cobranza)
                cuerpo = render_plantilla_cobranza(plantilla.cuerpo, contexto_cobranza)
                # Variables simples ({{fecha_vencimiento}}, {{monto}}, etc.) no forman parte del contexto
                # de cobranza; FECHA_CARTA es la fecha del documento (hoy). Sin este paso, mezclas
                # COBRANZA + {{fecha_vencimiento}} dejaban la variable sin reemplazar o inducen a usar
                # FECHA_CARTA creyendo que es el vencimiento.
                asunto = _sustituir_variables(asunto, item)
                cuerpo = _sustituir_variables(cuerpo, item)
                return (asunto, cuerpo)
            asunto = _sustituir_variables(plantilla.asunto, item)
            cuerpo = _sustituir_variables(plantilla.cuerpo, item)
            return (asunto, cuerpo)
    asunto = _format_item_texto_plantilla_por_defecto(asunto_default, item)
    cuerpo = _format_item_texto_plantilla_por_defecto(cuerpo_default, item)
    return (asunto, cuerpo)


def contexto_cobranza_aplica_a_prestamo(contexto: object, prestamo_id: object) -> bool:
    """
    True si el contexto (produccion o stub de tests) corresponde al prestamo_id del item.
    Asi no se reutiliza Carta/PDF de otro credito cuando el dict se comparte en un batch
    o llega con datos obsoletos.
    """
    if not isinstance(contexto, dict) or prestamo_id is None:
        return False
    pid_ctx = contexto.get("PRESTAMOS.ID")
    if pid_ctx is None:
        pid_ctx = contexto.get("IDPRESTAMO")
    if pid_ctx is None:
        pid_ctx = contexto.get("prestamo_id")
    try:
        return int(pid_ctx) == int(prestamo_id)
    except (TypeError, ValueError):
        return False


def build_contexto_cobranza_para_item(
    db: Session,
    item: dict,
    correlativos_en_batch: dict,
    fecha_referencia: Optional[date] = None,
) -> tuple:
    """
    Construye contexto_cobranza para un item (plantilla COBRANZA).
    Carga cuotas pendientes de pago (no pagadas) con fecha_vencimiento <= hoy (vencidas o vencen hoy),
    para que en "DÃ­a de pago" (pestaÃ±a 2) tambiÃ©n se incluyan las cuotas que vencen hoy y se reemplacen
    {{CUOTAS_VENCIDAS}} y {{FECHAS_CUOTAS_PENDIENTES}}. Calcula siguiente numero correlativo.
    hoy = fecha calendario America/Caracas (misma regla que mora en cuotas).
    Si no hay prestamo_id devuelve (None, None).
    correlativos_en_batch: dict prestamo_id -> ultimo correlativo usado en este batch.
    fecha_referencia: si se indica, corte de cuotas vencidas y FECHA_CARTA alineados a ese día (Caracas).
    """
    prestamo_id = item.get("prestamo_id")
    if not prestamo_id:
        return None, None
    from app.services.plantilla_cobranza import construir_contexto_cobranza
    ref = fecha_referencia or hoy_negocio()
    cuotas = (
        db.execute(
            select(Cuota)
            .where(
                Cuota.prestamo_id == prestamo_id,
                Cuota.fecha_pago.is_(None),
                CUOTA_ESTADO_NO_PAGADA_PARA_NOTIF,
                Cuota.fecha_vencimiento <= ref,
                SALDO_PENDIENTE_CUOTA > TOL_SALDO_CUOTA_NOTIFICACION,
            )
            .order_by(Cuota.numero_cuota)
        )
        .scalars().all()
    )
    cuotas_list = [c for c in cuotas]
    db_max = db.execute(
        select(func.coalesce(func.max(EnvioNotificacion.correlativo), 0)).where(
            EnvioNotificacion.prestamo_id == prestamo_id
        )
    ).scalar() or 0
    try:
        db_max = int(db_max)
    except (TypeError, ValueError):
        db_max = 0
    next_correlativo = max(db_max, correlativos_en_batch.get(prestamo_id, 0)) + 1
    correlativos_en_batch[prestamo_id] = next_correlativo
    nombre = item.get("nombre") or ""
    cedula = item.get("cedula") or ""
    tratamiento = item.get("tratamiento") or "Sr/Sra."
    ctx = construir_contexto_cobranza(
        cliente_nombres=nombre,
        prestamo_id=prestamo_id,
        cuotas_vencidas=cuotas_list,
        tratamiento=tratamiento,
        cedula=cedula,
        numero_correlativo=next_correlativo,
        fecha_carta=ref,
    )
    # Cuota concreta del envío (pestaña 1 día después, etc.): no confundir con FECHA_CARTA (hoy).
    fv_item = item.get("fecha_vencimiento")
    if fv_item:
        ctx["fecha_vencimiento"] = fv_item
        ctx["FECHA_VENCIMIENTO"] = fv_item
    nc_item = item.get("numero_cuota")
    if nc_item is not None:
        ctx["numero_cuota"] = nc_item
    m_item = item.get("monto_cuota")
    if m_item is None and item.get("monto") is not None:
        m_item = item.get("monto")
    if m_item is not None:
        ctx["monto_cuota"] = m_item
        ctx["monto"] = m_item
    if item.get("dias_atraso") is not None:
        ctx["dias_atraso"] = item.get("dias_atraso")
    if item.get("cuotas_atrasadas") is not None:
        ctx["cuotas_atrasadas"] = item.get("cuotas_atrasadas")
    return ctx, next_correlativo

@router.get("/plantillas")
def get_plantillas(
    tipo: str = None,
    solo_activas: bool = True,
    db: Session = Depends(get_db),
):
    """Lista de plantillas de notificaciÃƒÂ³n. Filtro por tipo y solo activas."""
    try:
        q = select(PlantillaNotificacion)
        if solo_activas:
            q = q.where(PlantillaNotificacion.activa.is_(True))
        if tipo:
            q = q.where(PlantillaNotificacion.tipo == tipo)
        q = q.order_by(PlantillaNotificacion.tipo, PlantillaNotificacion.nombre)
        rows = db.execute(q).scalars().all()
        return [_plantilla_to_dict(p) for p in rows]
    except Exception as e:
        logger.exception("get_plantillas: %s", e)
        return []


@router.get("/plantillas/{plantilla_id}")
def get_plantilla(plantilla_id: int, db: Session = Depends(get_db)):
    """Obtiene una plantilla por id."""
    p = db.get(PlantillaNotificacion, plantilla_id)
    if not p:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    return _plantilla_to_dict(p)


TIPOS_PLANTILLA_PERMITIDOS = frozenset([
    "PAGO_5_DIAS_ANTES", "PAGO_3_DIAS_ANTES", "PAGO_1_DIA_ANTES",
    "PAGO_2_DIAS_ANTES_PENDIENTE",
    "PAGO_DIA_0",
    "PAGO_1_DIA_ATRASADO", "PAGO_3_DIAS_ATRASADO", "PAGO_5_DIAS_ATRASADO",
    "PAGO_30_DIAS_ATRASADO",
    "PREJUDICIAL", "MASIVOS", "MORA_61", "MORA_90",  # MORA_61/MORA_90 legacy (ya no se ofrece en UI ni envíos)
    "COBRANZA",  # Carta de cobranza con {{TABLA.CAMPO}} y bloque {{#CUOTAS.VENCIMIENTOS}}
])


@router.post("/plantillas")
def create_plantilla(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Crea una plantilla. Campos: nombre, tipo, asunto, cuerpo; opcionales: descripcion, variables_disponibles, activa, zona_horaria. tipo debe ser uno de los tipos de notificaciÃƒÂ³n permitidos."""
    from app.utils.texto_utf8 import normalizar_texto_plantilla

    nombre = normalizar_texto_plantilla(payload.get("nombre"))
    tipo = (payload.get("tipo") or "").strip()
    asunto = normalizar_texto_plantilla(payload.get("asunto"))
    cuerpo = payload.get("cuerpo") or ""
    if not nombre or not tipo or not asunto:
        raise HTTPException(status_code=422, detail="nombre, tipo y asunto son obligatorios")
    if tipo not in TIPOS_PLANTILLA_PERMITIDOS:
        raise HTTPException(
            status_code=422,
            detail=f"tipo debe ser uno de: {', '.join(sorted(TIPOS_PLANTILLA_PERMITIDOS))}",
        )
    try:
        p = PlantillaNotificacion(
            nombre=nombre,
            descripcion=payload.get("descripcion"),
            tipo=tipo,
            asunto=asunto,
            cuerpo=cuerpo,
            variables_disponibles=payload.get("variables_disponibles"),
            activa=payload.get("activa", True),
            zona_horaria=(payload.get("zona_horaria") or "America/Caracas").strip(),
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        return _plantilla_to_dict(p)
    except Exception as e:
        db.rollback()
        logger.exception("create_plantilla: %s", e)
        raise HTTPException(status_code=500, detail="Error al crear la plantilla")


@router.put("/plantillas/{plantilla_id}")
def update_plantilla(plantilla_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    """Actualiza una plantilla."""
    p = db.get(PlantillaNotificacion, plantilla_id)
    if not p:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    if "nombre" in payload and payload["nombre"] is not None:
        from app.utils.texto_utf8 import normalizar_texto_plantilla

        p.nombre = normalizar_texto_plantilla(payload.get("nombre"))
    if "descripcion" in payload:
        p.descripcion = payload.get("descripcion")
    if "tipo" in payload and payload["tipo"] is not None:
        nuevo_tipo = (payload["tipo"] or "").strip()
        if nuevo_tipo and nuevo_tipo not in TIPOS_PLANTILLA_PERMITIDOS:
            raise HTTPException(
                status_code=422,
                detail=f"tipo debe ser uno de: {', '.join(sorted(TIPOS_PLANTILLA_PERMITIDOS))}",
            )
        p.tipo = nuevo_tipo
    if "asunto" in payload and payload["asunto"] is not None:
        from app.utils.texto_utf8 import normalizar_texto_plantilla

        p.asunto = normalizar_texto_plantilla(payload.get("asunto"))
    if "cuerpo" in payload:
        p.cuerpo = payload.get("cuerpo") or ""
    if "variables_disponibles" in payload:
        p.variables_disponibles = payload.get("variables_disponibles")
    if "activa" in payload:
        p.activa = bool(payload["activa"])
    if "zona_horaria" in payload and payload["zona_horaria"] is not None:
        p.zona_horaria = (payload["zona_horaria"] or "America/Caracas").strip()
    try:
        db.commit()
        db.refresh(p)
        return _plantilla_to_dict(p)
    except Exception as e:
        db.rollback()
        logger.exception("update_plantilla: %s", e)
        raise HTTPException(status_code=500, detail="Error al actualizar la plantilla")


@router.delete("/plantillas/{plantilla_id}")
def delete_plantilla(plantilla_id: int, db: Session = Depends(get_db)):
    """Elimina una plantilla."""
    p = db.get(PlantillaNotificacion, plantilla_id)
    if not p:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    try:
        db.delete(p)
        db.commit()
        return {"message": "Plantilla eliminada"}
    except Exception as e:
        db.rollback()
        logger.exception("delete_plantilla: %s", e)
        raise HTTPException(status_code=500, detail="Error al eliminar la plantilla")


@router.get("/plantilla-pdf-cobranza")
def get_plantilla_pdf_cobranza(db: Session = Depends(get_db)):
    """
    Obtiene la plantilla editable del PDF de carta de cobranza (adjunto al email).
    Almacenada en configuracion con clave 'plantilla_pdf_cobranza'. JSON: ciudad_default, cuerpo_principal, clausula_septima.
    """
    row = db.get(Configuracion, "plantilla_pdf_cobranza")
    if not row or not row.valor:
        return {
            "ciudad_default": "Guacara",
            "cuerpo_principal": None,
            "clausula_septima": None,
            "firma": None,
        }
    try:
        data = json.loads(row.valor)
        if "firma" not in data:
            data["firma"] = None
        return data
    except json.JSONDecodeError:
        return {"ciudad_default": "Guacara", "cuerpo_principal": None, "clausula_septima": None, "firma": None}


def _contexto_preview_cobranza() -> dict:
    """Contexto de ejemplo para vista previa del PDF (fecha en America/Caracas)."""
    return {
        "CLIENTES.TRATAMIENTO": "Sr.",
        "CLIENTES.NOMBRE_COMPLETO": "Juan Pérez (ejemplo)",
        "CLIENTES.CEDULA": "V-12345678",
        "PRESTAMOS.ID": "1001",
        "NUMEROCORRELATIVO": "2025-001",
        "TOTAL_ADEUDADO": "300,00",
        "FECHA_CARTA": hoy_negocio().isoformat(),
        "CUOTAS.VENCIMIENTOS": [
            {"fecha_vencimiento": "2025-01-15", "monto": 150.00, "numero_cuota": 1},
            {"fecha_vencimiento": "2025-02-15", "monto": 150.00, "numero_cuota": 2},
        ],
    }


@router.get("/plantilla-pdf-cobranza/preview")
def preview_plantilla_pdf_cobranza(db: Session = Depends(get_db)):
    """
    Genera una vista previa del PDF de carta de cobranza con datos de ejemplo.
    ÃƒÂštil para verificar la plantilla sin enviar un correo real.
    """
    from app.services.carta_cobranza_pdf import generar_carta_cobranza_pdf
    try:
        pdf_bytes = generar_carta_cobranza_pdf(_contexto_preview_cobranza(), db=db)
        return Response(content=pdf_bytes, media_type="application/pdf")
    except Exception as e:
        logger.exception("preview_plantilla_pdf_cobranza: %s", e)
        detail = "Error al generar la vista previa del PDF"
        if getattr(e, "args", None):
            detail = f"{detail}: {str(e.args[0])[:200]}"
        raise HTTPException(status_code=500, detail=detail)


# LÃƒÂ­mites de longitud para plantilla PDF cobranza (evitar payloads excesivos)
_PLANTILLA_PDF_CUERPO_MAX = 100_000
_PLANTILLA_PDF_CLAUSULA_MAX = 100_000
_PLANTILLA_PDF_FIRMA_MAX = 50_000


@router.put("/plantilla-pdf-cobranza")
def update_plantilla_pdf_cobranza(payload: dict = Body(...), db: Session = Depends(get_db)):
    """
    Actualiza la plantilla editable del PDF de carta de cobranza.
    Campos opcionales: ciudad_default, cuerpo_principal, clausula_septima (texto legal), firma (bloque final: Atentamente, sello, etc.).
    LÃƒÂ­mites: cuerpo_principal y clausula_septima 100.000 caracteres; firma 50.000.
    """
    cuerpo = payload.get("cuerpo_principal")
    if cuerpo is not None and len(cuerpo) > _PLANTILLA_PDF_CUERPO_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"El cuerpo principal no puede superar {_PLANTILLA_PDF_CUERPO_MAX} caracteres (actual: {len(cuerpo)}).",
        )
    clausula = payload.get("clausula_septima")
    if clausula is not None and len(clausula) > _PLANTILLA_PDF_CLAUSULA_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"La cláusula séptima no puede superar {_PLANTILLA_PDF_CLAUSULA_MAX} caracteres (actual: {len(clausula)}).",
        )
    firma = payload.get("firma")
    if firma is not None and len(firma) > _PLANTILLA_PDF_FIRMA_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"La firma no puede superar {_PLANTILLA_PDF_FIRMA_MAX} caracteres (actual: {len(firma)}).",
        )
    try:
        row = db.get(Configuracion, "plantilla_pdf_cobranza")
        data = {}
        if row and row.valor:
            try:
                data = json.loads(row.valor)
            except json.JSONDecodeError:
                pass
        data["ciudad_default"] = payload.get("ciudad_default", data.get("ciudad_default", "Guacara"))
        if "cuerpo_principal" in payload:
            data["cuerpo_principal"] = payload["cuerpo_principal"]
        if "clausula_septima" in payload:
            data["clausula_septima"] = payload["clausula_septima"]
        if "firma" in payload:
            data["firma"] = payload["firma"]
        if not row:
            row = Configuracion(clave="plantilla_pdf_cobranza", valor=json.dumps(data))
            db.add(row)
        else:
            row.valor = json.dumps(data)
        db.commit()
        db.refresh(row)
        return json.loads(row.valor)
    except Exception as e:
        db.rollback()
        logger.exception("update_plantilla_pdf_cobranza: %s", e)
        raise HTTPException(status_code=500, detail="Error al guardar la plantilla PDF de cobranza")


CLAVE_ESTADO_CUENTA_EMAIL = "estado_cuenta_codigo_email"
_DEFAULT_ESTADO_CUENTA_ASUNTO = "Codigo para estado de cuenta - RapiCredit"
_DEFAULT_ESTADO_CUENTA_CUERPO = (
    "Estimado(a) {{nombre}},\n\n"
    "Tu codigo de verificacion es: {{codigo}}\n\n"
    "Valido por {{minutos_valido}} horas. No lo compartas.\n\n"
    "Saludos,\nRapiCredit"
)


@router.get("/plantilla-estado-cuenta-codigo-email")
def get_plantilla_estado_cuenta_codigo_email(db: Session = Depends(get_db)):
    """
    Obtiene la plantilla del email de cÃƒÂ³digo para consulta pÃƒÂºblica de estado de cuenta.
    Almacenada en configuracion con clave 'estado_cuenta_codigo_email'.
    JSON: asunto, cuerpo. Variables: {{nombre}}, {{codigo}}, {{minutos_valido}}.
    """
    row = db.get(Configuracion, CLAVE_ESTADO_CUENTA_EMAIL)
    if not row or not row.valor:
        return {"asunto": _DEFAULT_ESTADO_CUENTA_ASUNTO, "cuerpo": _DEFAULT_ESTADO_CUENTA_CUERPO}
    try:
        return json.loads(row.valor)
    except json.JSONDecodeError:
        return {"asunto": _DEFAULT_ESTADO_CUENTA_ASUNTO, "cuerpo": _DEFAULT_ESTADO_CUENTA_CUERPO}


@router.put("/plantilla-estado-cuenta-codigo-email")
def update_plantilla_estado_cuenta_codigo_email(payload: dict = Body(...), db: Session = Depends(get_db)):
    """
    Actualiza la plantilla del email de cÃƒÂ³digo (consulta pÃƒÂºblica estado de cuenta).
    Campos: asunto, cuerpo (opcionales). Variables en cuerpo: {{nombre}}, {{codigo}}, {{minutos_valido}}.
    """
    try:
        row = db.get(Configuracion, CLAVE_ESTADO_CUENTA_EMAIL)
        data = {}
        if row and row.valor:
            try:
                data = json.loads(row.valor)
            except json.JSONDecodeError:
                pass
        data["asunto"] = payload.get("asunto", data.get("asunto", _DEFAULT_ESTADO_CUENTA_ASUNTO))
        data["cuerpo"] = payload.get("cuerpo", data.get("cuerpo", _DEFAULT_ESTADO_CUENTA_CUERPO))
        if not row:
            row = Configuracion(clave=CLAVE_ESTADO_CUENTA_EMAIL, valor=json.dumps(data))
            db.add(row)
        else:
            row.valor = json.dumps(data)
        db.commit()
        db.refresh(row)
        return json.loads(row.valor)
    except Exception as e:
        db.rollback()
        logger.exception("update_plantilla_estado_cuenta_codigo_email: %s", e)
        raise HTTPException(status_code=500, detail="Error al guardar la plantilla de email de estado de cuenta")


@router.get("/adjunto-fijo-cobranza")
def get_adjunto_fijo_cobranza(db: Session = Depends(get_db)):
    """
    Obtiene la configuraciÃƒÂ³n del PDF fijo que se anexa siempre al email de cobranza (sin cambios).
    Almacenada en configuracion con clave 'adjunto_fijo_cobranza'. JSON: nombre_archivo, ruta.
    """
    row = db.get(Configuracion, "adjunto_fijo_cobranza")
    if not row or not row.valor:
        return {"nombre_archivo": "", "ruta": ""}
    try:
        return json.loads(row.valor)
    except json.JSONDecodeError:
        return {"nombre_archivo": "", "ruta": ""}


@router.get("/adjunto-fijo-cobranza/verificar")
def verificar_adjunto_fijo_cobranza(db: Session = Depends(get_db)):
    """
    Comprueba si la ruta configurada del adjunto fijo existe en el servidor y es legible.
    Retorna existe (bool) y mensaje (str) para mostrar en la UI.
    """
    from app.services.adjunto_fijo_cobranza import verificar_ruta_adjunto_fijo
    existe, mensaje = verificar_ruta_adjunto_fijo(db)
    return {"existe": existe, "mensaje": mensaje or ("Archivo encontrado" if existe else "No configurado")}


# LÃƒÂ­mites para adjunto fijo cobranza (evitar abusos)
_ADJUNTO_FIJO_NOMBRE_MAX = 255
_ADJUNTO_FIJO_RUTA_MAX = 2048


@router.put("/adjunto-fijo-cobranza")
def update_adjunto_fijo_cobranza(payload: dict = Body(...), db: Session = Depends(get_db)):
    """
    Actualiza la configuraciÃƒÂ³n del PDF fijo para cobranza.
    Campos: nombre_archivo (ej. Documento.pdf), ruta (ruta absoluta o relativa al proceso al archivo PDF).
    Si ruta estÃƒÂ¡ vacÃƒÂ­a, no se anexa ningÃƒÂºn PDF fijo.
    """
    try:
        nombre = (payload.get("nombre_archivo") or "").strip() or "Adjunto_Cobranza.pdf"
        ruta = (payload.get("ruta") or "").strip()
        if len(nombre) > _ADJUNTO_FIJO_NOMBRE_MAX:
            raise HTTPException(
                status_code=400,
                detail=f"El nombre del archivo no puede superar {_ADJUNTO_FIJO_NOMBRE_MAX} caracteres.",
            )
        if len(ruta) > _ADJUNTO_FIJO_RUTA_MAX:
            raise HTTPException(
                status_code=400,
                detail=f"La ruta no puede superar {_ADJUNTO_FIJO_RUTA_MAX} caracteres.",
            )
        # Evitar path traversal en nombre (solo nombre de archivo, sin barras)
        if "/" in nombre or "\\" in nombre:
            raise HTTPException(status_code=400, detail="El nombre del archivo no debe contener rutas (use solo el nombre del PDF).")
        # Si estÃƒÂ¡ configurado directorio base, la ruta debe ser relativa (sin .. ni absoluta)
        from app.core.config import settings
        base_dir = getattr(settings, "ADJUNTO_FIJO_COBRANZA_BASE_DIR", None)
        if base_dir and (base_dir or "").strip():
            if ".." in ruta or ruta.startswith("/") or (len(ruta) >= 2 and ruta[1] == ":"):
                raise HTTPException(
                    status_code=400,
                    detail="Con directorio base configurado use solo ruta relativa (ej: documento.pdf o carpeta/documento.pdf).",
                )
        row = db.get(Configuracion, "adjunto_fijo_cobranza")
        data = {
            "nombre_archivo": nombre,
            "ruta": ruta,
        }
        if not row:
            row = Configuracion(clave="adjunto_fijo_cobranza", valor=json.dumps(data))
            db.add(row)
        else:
            row.valor = json.dumps(data)
        db.commit()
        db.refresh(row)
        return json.loads(row.valor)
    except Exception as e:
        db.rollback()
        logger.exception("update_adjunto_fijo_cobranza: %s", e)
        raise HTTPException(status_code=500, detail="Error al guardar la configuración del adjunto fijo")


@router.get("/adjuntos-fijos-cobranza")
def get_adjuntos_fijos_cobranza(db: Session = Depends(get_db)):
    """Lista de documentos PDF anexos por caso (previas, dÃƒÂ­a pago, retrasadas, prejudicial)."""
    from app.services.adjunto_fijo_cobranza import _get_adjuntos_por_caso_raw
    return _get_adjuntos_por_caso_raw(db)


@router.post("/adjuntos-fijos-cobranza/upload")
def upload_adjunto_fijo_cobranza(
    tipo_caso: str = Query(
        ...,
        description="Caso: dias_1_retraso, dias_3_retraso, dias_5_retraso, dias_30_retraso, d_2_antes_vencimiento, prejudicial, masivos",
    ),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Sube un PDF y lo asocia al caso indicado. Solo se aceptan archivos PDF. Puede asignarse a cualquier pestaÃƒÂ±a."""
    from app.services.adjunto_fijo_cobranza import (
        TIPOS_CASO_VALIDOS,
        CLAVE_ADJUNTOS_FIJOS_POR_CASO,
        _get_adjuntos_por_caso_raw,
    )
    if tipo_caso not in TIPOS_CASO_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail="tipo_caso debe ser uno de: dias_1_retraso, dias_3_retraso, dias_5_retraso, dias_30_retraso, d_2_antes_vencimiento, prejudicial, masivos",
        )
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se permiten documentos PDF")
    # Muchos navegadores envían application/octet-stream; la validez real es la cabecera %PDF- tras leer bytes.
    try:
        data = file.file.read()
    except Exception as e:
        logger.exception("Error leyendo archivo subido: %s", e)
        raise HTTPException(status_code=500, detail="Error al leer el archivo")
    if not data[:5] == b"%PDF-":
        raise HTTPException(status_code=400, detail="El archivo no parece ser un PDF valido")
    max_pdf = 12 * 1024 * 1024
    if len(data) > max_pdf:
        raise HTTPException(
            status_code=400,
            detail=f"El PDF supera el tamaño máximo permitido ({max_pdf // (1024 * 1024)} MB)",
        )
    doc_id = str(uuid.uuid4())
    safe_name = "".join(c for c in file.filename if c.isalnum() or c in "._- ") or "documento"
    ext = ".pdf"
    nombre_archivo = (safe_name + ext) if not safe_name.endswith(".pdf") else safe_name
    entry = {"id": doc_id, "nombre_archivo": nombre_archivo, "ruta": "", "en_bd": True}
    row_doc = AdjuntoFijoCobranzaDocumento(
        id=doc_id,
        tipo_caso=tipo_caso,
        nombre_archivo=nombre_archivo,
        pdf_data=data,
    )
    db.add(row_doc)
    config = _get_adjuntos_por_caso_raw(db)
    config.setdefault(tipo_caso, [])
    config[tipo_caso].append(entry)
    row = db.get(Configuracion, CLAVE_ADJUNTOS_FIJOS_POR_CASO)
    if not row:
        row = Configuracion(clave=CLAVE_ADJUNTOS_FIJOS_POR_CASO, valor=json.dumps(config))
        db.add(row)
    else:
        row.valor = json.dumps(config)
    try:
        db.commit()
        db.refresh(row)
    except Exception as e:
        db.rollback()
        logger.exception("Error guardando config: %s", e)
        raise HTTPException(status_code=500, detail="Error al guardar la configuracion")
    return {"id": doc_id, "nombre_archivo": nombre_archivo, "tipo_caso": tipo_caso, "tipo_casos": [tipo_caso]}


@router.delete("/adjuntos-fijos-cobranza/{doc_id}")
def delete_adjunto_fijo_cobranza(doc_id: str, db: Session = Depends(get_db)):
    """Elimina un documento anexo por su id."""
    from app.services.adjunto_fijo_cobranza import (
        CLAVE_ADJUNTOS_FIJOS_POR_CASO,
        _get_adjuntos_por_caso_raw,
        _get_base_dir_adjuntos,
    )
    config = _get_adjuntos_por_caso_raw(db)
    found = False
    for caso, lista in list(config.items()):
        for i, item in enumerate(lista):
            if isinstance(item, dict) and item.get("id") == doc_id:
                ruta_rel = (item.get("ruta") or "").strip()
                lista.pop(i)
                found = True
                if item.get("en_bd") is True:
                    row_doc = db.get(AdjuntoFijoCobranzaDocumento, doc_id)
                    if row_doc:
                        db.delete(row_doc)
                else:
                    from app.services.adjunto_fijo_cobranza import _get_base_dir_adjuntos

                    base_dir = _get_base_dir_adjuntos()
                    path = os.path.normpath(os.path.join(base_dir, ruta_rel))
                    if path.startswith(base_dir) and os.path.isfile(path):
                        try:
                            os.remove(path)
                        except Exception as e:
                            logger.warning("Error eliminando archivo %s: %s", path, e)
                break
        if found:
            break
    if not found:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    row = db.get(Configuracion, CLAVE_ADJUNTOS_FIJOS_POR_CASO)
    if not row:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    row.valor = json.dumps(config)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("delete_adjunto_fijo_cobranza: %s", e)
        raise HTTPException(status_code=500, detail="Error al eliminar")
    return {"message": "Eliminado"}




@router.get("/plantillas/{plantilla_id}/export")
def export_plantilla(plantilla_id: int, db: Session = Depends(get_db)):
    """Exporta una plantilla (mismo formato que GET por id)."""
    p = db.get(PlantillaNotificacion, plantilla_id)
    if not p:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    return _plantilla_to_dict(p)


@router.post("/plantillas/{plantilla_id}/enviar")
def enviar_con_plantilla(
    plantilla_id: int,
    cliente_id: int = Query(..., description="ID del cliente destinatario"),
    db: Session = Depends(get_db),
    variables: dict = Body(default=None),
):
    """
    EnvÃƒÂ­a un correo de prueba al cliente usando la plantilla. variables (body) sustituyen en asunto/cuerpo.
    Query: cliente_id. Body: dict opcional con nombre, cedula, fecha_vencimiento, numero_cuota, monto, dias_atraso.
    """
    from app.core.email import send_email
    from app.core.email_config_holder import get_email_activo_servicio
    from app.utils.cliente_emails import (
        lista_correo_principal_notificaciones_desde_objeto,
        unir_destinatarios_log,
    )
    p = db.get(PlantillaNotificacion, plantilla_id)
    if not p or not p.activa:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada o inactiva")
    cliente = db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    item = {
        "nombre": (variables or {}).get("nombre") or cliente.nombres or "Cliente",
        "cedula": (variables or {}).get("cedula") or cliente.cedula or "",
        "fecha_vencimiento": (variables or {}).get("fecha_vencimiento") or "",
        "numero_cuota": (variables or {}).get("numero_cuota"),
        "monto_cuota": (variables or {}).get("monto"),
        "dias_atraso": (variables or {}).get("dias_atraso"),
    }
    asunto = _sustituir_variables(p.asunto, item)
    cuerpo = _sustituir_variables(p.cuerpo, item)
    destinos = lista_correo_principal_notificaciones_desde_objeto(cliente)
    if not destinos:
        raise HTTPException(status_code=400, detail="El cliente no tiene email valido")
    if cliente_bloqueado_por_desistimiento(
        db, cliente_id=cliente.id, cedula=cliente.cedula, email=destinos[0]
    ):
        raise HTTPException(
            status_code=400,
            detail="Envio bloqueado: cliente con prestamo en estado DESISTIMIENTO.",
        )
    if not get_email_activo_servicio("notificaciones"):
        raise HTTPException(status_code=400, detail="El envio de email para notificaciones esta desactivado. Activalo en Configuracion > Email.")
    tipo_tab = (getattr(p, "tipo", None) or "").strip() or None
    ok, msg = send_email(destinos, asunto, cuerpo, servicio="notificaciones", tipo_tab=tipo_tab)
    if not ok:
        raise HTTPException(status_code=502, detail=msg or "Error al enviar el correo")
    return {"message": "Correo enviado", "destinatario": unir_destinatarios_log(destinos), "destinatarios": destinos}


# --- Variables personalizadas (CRUD + inicializar precargadas) ---

def _variable_to_dict(v: VariableNotificacion) -> dict:
    """Serializa VariableNotificacion al formato esperado por el frontend."""
    return {
        "id": v.id,
        "nombre_variable": v.nombre_variable or "",
        "tabla": v.tabla or "",
        "campo_bd": v.campo_bd or "",
        "descripcion": getattr(v, "descripcion", None),
        "activa": bool(v.activa),
        "fecha_creacion": v.fecha_creacion.isoformat() if v.fecha_creacion else None,
        "fecha_actualizacion": v.fecha_actualizacion.isoformat() if v.fecha_actualizacion else None,
    }


@router.get("/variables")
def get_variables(
    activa: Optional[bool] = Query(None, description="Filtrar por activa (true/false)"),
    db: Session = Depends(get_db),
):
    """Lista variables personalizadas de notificaciones. Opcional: ?activa=true|false."""
    q = select(VariableNotificacion).order_by(VariableNotificacion.nombre_variable)
    if activa is not None:
        q = q.where(VariableNotificacion.activa == activa)
    try:
        rows = db.execute(q).scalars().all()
        return [_variable_to_dict(r) for r in rows]
    except Exception as e:
        logger.exception("get_variables: %s", e)
        return []


@router.get("/variables/{variable_id}")
def get_variable(variable_id: int, db: Session = Depends(get_db)):
    """Obtiene una variable personalizada por id."""
    v = db.get(VariableNotificacion, variable_id)
    if not v:
        raise HTTPException(status_code=404, detail="Variable no encontrada")
    return _variable_to_dict(v)


@router.post("/variables")
def create_variable(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Crea una variable personalizada. Campos: nombre_variable, tabla, campo_bd; opcionales: descripcion, activa."""
    nombre = (payload.get("nombre_variable") or "").strip().lower()
    if not nombre:
        raise HTTPException(status_code=400, detail="nombre_variable es obligatorio")
    tabla = (payload.get("tabla") or "").strip()
    campo_bd = (payload.get("campo_bd") or "").strip()
    if not tabla or not campo_bd:
        raise HTTPException(status_code=400, detail="tabla y campo_bd son obligatorios")
    existing = db.execute(select(VariableNotificacion).where(VariableNotificacion.nombre_variable == nombre)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe una variable con ese nombre_variable")
    try:
        v = VariableNotificacion(
            nombre_variable=nombre,
            tabla=tabla,
            campo_bd=campo_bd,
            descripcion=(payload.get("descripcion") or "").strip() or None,
            activa=payload.get("activa", True),
        )
        db.add(v)
        db.commit()
        db.refresh(v)
        return _variable_to_dict(v)
    except Exception as e:
        db.rollback()
        logger.exception("create_variable: %s", e)
        raise HTTPException(status_code=500, detail="Error al crear la variable")


@router.put("/variables/{variable_id}")
def update_variable(variable_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    """Actualiza una variable personalizada (descripcion, activa, tabla, campo_bd). nombre_variable no se modifica."""
    v = db.get(VariableNotificacion, variable_id)
    if not v:
        raise HTTPException(status_code=404, detail="Variable no encontrada")
    if "descripcion" in payload:
        v.descripcion = (payload.get("descripcion") or "").strip() or None
    if "activa" in payload:
        v.activa = bool(payload.get("activa"))
    if "tabla" in payload and payload.get("tabla"):
        v.tabla = (payload["tabla"] or "").strip()
    if "campo_bd" in payload and payload.get("campo_bd"):
        v.campo_bd = (payload["campo_bd"] or "").strip()
    try:
        db.commit()
        db.refresh(v)
        return _variable_to_dict(v)
    except Exception as e:
        db.rollback()
        logger.exception("update_variable: %s", e)
        raise HTTPException(status_code=500, detail="Error al actualizar la variable")


@router.delete("/variables/{variable_id}")
def delete_variable(variable_id: int, db: Session = Depends(get_db)):
    """Elimina una variable personalizada."""
    v = db.get(VariableNotificacion, variable_id)
    if not v:
        raise HTTPException(status_code=404, detail="Variable no encontrada")
    try:
        db.delete(v)
        db.commit()
        return {"message": "Variable eliminada"}
    except Exception as e:
        db.rollback()
        logger.exception("delete_variable: %s", e)
        raise HTTPException(status_code=500, detail="Error al eliminar la variable")


VARIABLES_PRECARGADAS = [
    {"nombre_variable": "nombre_cliente", "tabla": "clientes", "campo_bd": "nombres", "descripcion": "Nombres del cliente"},
    {"nombre_variable": "cedula", "tabla": "clientes", "campo_bd": "cedula", "descripcion": "Cédula de identidad"},
    {"nombre_variable": "telefono", "tabla": "clientes", "campo_bd": "telefono", "descripcion": "Teléfono de contacto"},
    {"nombre_variable": "email", "tabla": "clientes", "campo_bd": "email", "descripcion": "Correo electrónico"},
    {"nombre_variable": "numero_cuota", "tabla": "cuotas", "campo_bd": "numero_cuota", "descripcion": "Número de cuota"},
    {"nombre_variable": "fecha_vencimiento", "tabla": "cuotas", "campo_bd": "fecha_vencimiento", "descripcion": "Fecha de vencimiento"},
    {"nombre_variable": "monto_cuota", "tabla": "cuotas", "campo_bd": "monto", "descripcion": "Monto de la cuota"},
    {
        "nombre_variable": "dias_atraso",
        "tabla": "cuotas",
        "campo_bd": "dias_mora",
        "descripcion": "Dias desde vencimiento de la cuota de referencia (1/3/5/30; tipo de envio)",
    },
    {
        "nombre_variable": "cuotas_atrasadas",
        "tabla": "prestamos",
        "campo_bd": "conteo",
        "descripcion": "Cantidad de cuotas en atraso del prestamo (misma regla que estado de cuenta)",
    },
]


@router.post("/variables/inicializar-precargadas")
def inicializar_variables_precargadas(db: Session = Depends(get_db)):
    """Inserta variables precargadas si no existen (por nombre_variable). Idempotente."""
    creadas = 0
    existentes = 0
    for item in VARIABLES_PRECARGADAS:
        nombre = item["nombre_variable"]
        existing = db.execute(select(VariableNotificacion).where(VariableNotificacion.nombre_variable == nombre)).scalar_one_or_none()
        if existing:
            existentes += 1
            continue
        try:
            v = VariableNotificacion(
                nombre_variable=nombre,
                tabla=item["tabla"],
                campo_bd=item["campo_bd"],
                descripcion=item.get("descripcion"),
                activa=True,
            )
            db.add(v)
            db.commit()
            creadas += 1
        except Exception as e:
            db.rollback()
            logger.warning("inicializar_variables_precargadas: %s para %s", e, nombre)
    total = creadas + existentes
    return {
        "mensaje": f"Variables precargadas: {creadas} creadas, {existentes} ya existían.",
        "variables_creadas": creadas,
        "variables_existentes": existentes,
        "total": total,
    }


@router.get("")
def get_notificaciones_lista(
    page: int = 1,
    per_page: int = 20,
    estado: str = None,
    canal: str = None,
    db: Session = Depends(get_db),
):
    """
    Listado paginado de notificaciones (envÃƒÂ­os) desde tabla envios_notificacion.
    El frontend ConfiguraciÃƒÂ³n > Email lo usa para 'VerificaciÃƒÂ³n de EnvÃƒÂ­os Reales'.
    """
    per_page = max(1, min(per_page, 100))
    page = max(1, page)
    offset = (page - 1) * per_page

    q_filter = select(EnvioNotificacion)
    if estado:
        if estado.upper() == "ENVIADA":
            q_filter = q_filter.where(EnvioNotificacion.exito == True)
        elif estado.upper() == "FALLIDA":
            q_filter = q_filter.where(EnvioNotificacion.exito == False)
    total = db.scalar(select(func.count()).select_from(q_filter.subquery()))
    total = total or 0
    total_pages = (total + per_page - 1) // per_page if total else 0

    q = q_filter.order_by(EnvioNotificacion.fecha_envio.desc()).offset(offset).limit(per_page)
    rows = db.scalars(q).all()
    items = []
    for r in rows:
        items.append({
            "id": r.id,
            "estado": "ENVIADA" if r.exito else "FALLIDA",
            "asunto": f"Notificación {r.tipo_tab}" if r.tipo_tab else "Envío",
            "fecha_envio": r.fecha_envio.isoformat() if r.fecha_envio else None,
            "fecha_creacion": r.fecha_envio.isoformat() if r.fecha_envio else None,
            "error_mensaje": r.error_mensaje,
        })
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": per_page,
        "total_pages": total_pages,
    }


def _tarea_envio_todas_notificaciones():
    """Ejecuta el envio masivo en segundo plano; persiste resumen en configuracion para GET envio-batch/ultimo."""
    from datetime import datetime, timezone

    from app.core.database import SessionLocal
    from app.api.v1.endpoints import notificaciones_tabs
    from app.services.notificaciones_envio_batch_resumen import persist_ultimo_envio_batch

    inicio = datetime.now(timezone.utc).isoformat()
    db = SessionLocal()
    try:
        result = notificaciones_tabs.ejecutar_envio_todas_notificaciones(db)
        persist_ultimo_envio_batch(db, resultado=result, origen="api_enviar_todas", inicio_utc=inicio)
        db.commit()
    except Exception as e:
        logger.exception("Envio masivo en background: %s", e)
        try:
            db.rollback()
            persist_ultimo_envio_batch(
                db,
                resultado={},
                origen="api_enviar_todas",
                error=str(e)[:5000],
                inicio_utc=inicio,
            )
            db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


@router.get("/envio-batch/ultimo")
def get_ultimo_envio_batch_notificaciones(db: Session = Depends(get_db)):
    """Ultimo resultado de ejecutar envio masivo (POST manual / BackgroundTasks). Null si nunca hubo ejecucion."""
    from app.services.notificaciones_envio_batch_resumen import get_ultimo_envio_batch_dict

    return {"ultimo": get_ultimo_envio_batch_dict(db)}


@router.post("/enviar-todas")
def enviar_todas_notificaciones(background_tasks: BackgroundTasks):
    """
    Inicia el envio de todas las notificaciones en segundo plano.
    Responde 202 de inmediato para evitar timeout (el envio puede tardar muchos minutos).
    Respeta la configuracion guardada (modo_pruebas, email_pruebas, habilitado por tipo).
    No existe cron ni tarea oculta que llame a este endpoint: solo se ejecuta cuando alguien hace POST explicito.
    """
    background_tasks.add_task(_tarea_envio_todas_notificaciones)
    return JSONResponse(
        status_code=202,
        content={
            "mensaje": (
                "Env\u00edo iniciado en segundo plano. Los correos se enviar\u00e1n en los pr\u00f3ximos minutos. "
                "Puedes cerrar esta ventana."
            ),
            "en_proceso": True,
        },
    )


@router.post("/enviar-caso-manual")
def enviar_caso_manual(payload: dict = Body(...), db: Session = Depends(get_db)):
    """
    Envio sincrono para un solo criterio por peticion (una fila: PAGO_1_DIA_ANTES, PAGO_1_DIA_ATRASADO, etc.).

    No encola otros casos ni programa envios: solo el tipo indicado en el JSON. Cada destinatario usa la
    plantilla/CCO/PDF de esa fila (no se infiere otro tipo por fila). En produccion: un correo por cliente
    en la lista de ese caso; en modo pruebas: destinos de prueba. Ignora el toggle Envio apagado en esa fila.

    Opcional en JSON: fecha_caracas (YYYY-MM-DD) = fecha de referencia America/Caracas para armar la lista
    y la carta PDF (mismo criterio que GET listados con ?fecha_caracas=).
    """
    from datetime import timezone

    from app.api.v1.endpoints import notificaciones_tabs
    from app.services.notificaciones_envio_batch_resumen import persist_ultimo_envio_batch

    tipo = (payload.get("tipo") or "").strip()
    if tipo not in notificaciones_tabs.TIPOS_CASO_MANUAL:
        allowed = ", ".join(sorted(notificaciones_tabs.TIPOS_CASO_MANUAL))
        raise HTTPException(
            status_code=422,
            detail=f"tipo invalido. Use uno de: {allowed}",
        )
    raw_fc = payload.get("fecha_caracas")
    if raw_fc is not None and not isinstance(raw_fc, str):
        raw_fc = str(raw_fc)
    try:
        fecha_ref = parse_fecha_referencia_negocio(raw_fc)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    inicio = datetime.now(timezone.utc).isoformat()
    try:
        res = notificaciones_tabs.ejecutar_envio_caso_manual(
            db, tipo, fecha_referencia=fecha_ref
        )
        para_persist = {k: v for k, v in res.items() if k != "mensaje"}
        para_persist["detalles"] = {"tipo_caso": tipo}
        persist_ultimo_envio_batch(
            db,
            resultado=para_persist,
            origen="api_enviar_caso_manual",
            inicio_utc=inicio,
        )
        return res
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("enviar_caso_manual: %s", e)
        try:
            persist_ultimo_envio_batch(
                db,
                resultado={},
                origen="api_enviar_caso_manual",
                error=str(e)[:5000],
                inicio_utc=inicio,
            )
        except Exception:
            logger.warning("enviar_caso_manual: no se pudo persistir resumen de error", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)[:800]) from e


@router.get("/estadisticas/resumen")
def get_notificaciones_resumen(db: Session = Depends(get_db)):
    """
    Resumen para sidebar: total de envios registrados y fallidos en ventana reciente.
    no_leidas = envios con exito=False (atencion / rebotados) en los ultimos 30 dias.
    total = todos los registros de envios_notificacion en los ultimos 30 dias.
    """
    desde = datetime.utcnow() - timedelta(days=30)
    try:
        total = (
            db.scalar(
                select(func.count(EnvioNotificacion.id)).where(
                    EnvioNotificacion.fecha_envio >= desde
                )
            )
            or 0
        )
        fallidos = (
            db.scalar(
                select(func.count(EnvioNotificacion.id)).where(
                    EnvioNotificacion.fecha_envio >= desde,
                    EnvioNotificacion.exito.is_(False),
                )
            )
            or 0
        )
        return {"no_leidas": int(fallidos), "total": int(total)}
    except Exception as e:
        logger.warning("get_notificaciones_resumen: %s", e)
        return {"no_leidas": 0, "total": 0}


@router.get("/estadisticas-por-tab", response_model=dict)
def get_estadisticas_por_tab(db: Session = Depends(get_db)):
    """
    KPIs por pestaña / tipo_tab: correos enviados y rebotados.
    Incluye previas (dias_5, dias_3, dias_1, hoy), retrasadas (dias_*_retraso),
    prejudicial y credito pagado (liquidados). Datos desde envios_notificacion.
    """
    result = {
        "dias_5": {"enviados": 0, "rebotados": 0},
        "dias_3": {"enviados": 0, "rebotados": 0},
        "dias_1": {"enviados": 0, "rebotados": 0},
        "hoy": {"enviados": 0, "rebotados": 0},
        "dias_1_retraso": {"enviados": 0, "rebotados": 0},
        "dias_3_retraso": {"enviados": 0, "rebotados": 0},
        "dias_5_retraso": {"enviados": 0, "rebotados": 0},
        "dias_30_retraso": {"enviados": 0, "rebotados": 0},
        "d_2_antes_vencimiento": {"enviados": 0, "rebotados": 0},
        "prejudicial": {"enviados": 0, "rebotados": 0},
        "masivos": {"enviados": 0, "rebotados": 0},
        "liquidados": {"enviados": 0, "rebotados": 0},
    }
    try:
        for tipo in (
            "dias_5",
            "dias_3",
            "dias_1",
            "hoy",
            "dias_1_retraso",
            "dias_3_retraso",
            "dias_5_retraso",
            "dias_30_retraso",
            "d_2_antes_vencimiento",
            "prejudicial",
            "masivos",
            "liquidados",
        ):
            env = db.scalar(
                select(func.count(EnvioNotificacion.id)).where(
                    EnvioNotificacion.tipo_tab == tipo,
                    EnvioNotificacion.exito.is_(True),
                )
            ) or 0
            reb = db.scalar(
                select(func.count(EnvioNotificacion.id)).where(
                    EnvioNotificacion.tipo_tab == tipo,
                    EnvioNotificacion.exito.is_(False),
                )
            ) or 0
            result[tipo] = {"enviados": int(env), "rebotados": int(reb)}
    except Exception as e:
        logger.warning("get_estadisticas_por_tab: %s", e)
    return result


TIPOS_TAB_NOTIFICACIONES = (
    "dias_5",
    "dias_3",
    "dias_1",
    "hoy",
    "dias_1_retraso",
    "dias_3_retraso",
    "dias_5_retraso",
    "dias_30_retraso",
    "d_2_antes_vencimiento",
    "prejudicial",
    "masivos",
    "liquidados",
)


def _get_rebotados_por_tipo(db: Session, tipo: str) -> List[dict]:
    """
    Lista de correos no entregados (rebotados) para el tipo de pestaÃƒÂ±a.
    Datos desde tabla envios_notificacion (exito=False).
    """
    if tipo not in TIPOS_TAB_NOTIFICACIONES:
        return []
    try:
        rows = (
            db.execute(
                select(EnvioNotificacion)
                .where(
                    EnvioNotificacion.tipo_tab == tipo,
                    EnvioNotificacion.exito.is_(False),
                )
                .order_by(EnvioNotificacion.fecha_envio.desc())
            )
            .scalars().all()
        )
        return [
            {
                "email": r.email or "",
                "nombre": r.nombre or "",
                "cedula": r.cedula or "",
                "fecha_envio": r.fecha_envio.isoformat() if r.fecha_envio else "",
                "error_mensaje": r.error_mensaje or "",
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("_get_rebotados_por_tipo: %s", e)
        return []


@router.get("/rebotados-por-tab", response_model=dict)
def get_rebotados_por_tab(
    tipo: str = Query(
        ...,
        description="tipo_tab: dias_5, dias_3, dias_1, hoy, dias_1_retraso, dias_3_retraso, dias_5_retraso, dias_30_retraso, d_2_antes_vencimiento, prejudicial, masivos, liquidados",
    ),
    db: Session = Depends(get_db),
):
    """Lista de correos no entregados (rebotados) para la pestaÃƒÂ±a. Para generar informe Excel en frontend o descargar Excel."""
    if tipo not in TIPOS_TAB_NOTIFICACIONES:
        raise HTTPException(status_code=400, detail=f"tipo debe ser uno de: {', '.join(TIPOS_TAB_NOTIFICACIONES)}")
    items = _get_rebotados_por_tipo(db, tipo)
    return {"items": items, "total": len(items)}


def _generar_excel_rebotados(items: List[dict], tipo: str) -> bytes:
    """Genera Excel con lista de correos rebotados (no entregados)."""
    import io
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Correos no entregados"
    ws.append(["Email", "Nombre", "Cédula", "Fecha envío", "Motivo rebote"])
    for r in items:
        ws.append([
            r.get("email") or "",
            r.get("nombre") or "",
            r.get("cedula") or "",
            r.get("fecha_envio") or "",
            r.get("error_mensaje") or "",
        ])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@router.get("/rebotados-por-tab/excel")
def get_rebotados_por_tab_excel(
    tipo: str = Query(..., description="Tipo de pestaÃƒÂ±a: dias_5, dias_3, dias_1, hoy, dias_1_retraso"),
    db: Session = Depends(get_db),
):
    """Descarga informe Excel de correos no entregados (rebotados) para la pestaÃƒÂ±a."""
    if tipo not in TIPOS_TAB_NOTIFICACIONES:
        raise HTTPException(status_code=400, detail=f"tipo debe ser uno de: {', '.join(TIPOS_TAB_NOTIFICACIONES)}")
    items = _get_rebotados_por_tipo(db, tipo)
    content = _generar_excel_rebotados(items, tipo)
    filename = f"correos_no_entregados_{tipo}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _normalizar_cedula(cedula: str) -> str:
    """Quita espacios y guiones para comparar cÃƒÂ©dulas."""
    if not cedula:
        return ""
    return (cedula or "").strip().replace(" ", "").replace("-", "").upper()


@router.get("/historial-por-cedula", response_model=dict)
def get_historial_notificaciones_por_cedula(
    cedula: str = Query(..., min_length=1, description="CÃƒÂ©dula del cliente"),
    db: Session = Depends(get_db),
):
    """
    Historial de notificaciones enviadas (o fallidas) para un cliente por cÃƒÂ©dula.
    Para reportes y fines administrativos/legales. Datos desde tabla envios_notificacion.
    """
    import time
    t0 = time.perf_counter()
    norm = _normalizar_cedula(cedula)
    if not norm:
        log_historial_consulta("", 0, None)
        return {"items": [], "total": 0, "cedula": cedula.strip()}
    try:
        q = select(EnvioNotificacion).where(EnvioNotificacion.cedula.isnot(None))
        raw = db.execute(q).scalars().all()
        rows = [r for r in raw if _normalizar_cedula(r.cedula or "") == norm]
        rows = sorted(rows, key=lambda r: (r.fecha_envio or r.id or 0), reverse=True)
    except Exception as e:
        log_historial_fallo("consulta", str(e), exc=e)
        raise
    tiempo_ms = (time.perf_counter() - t0) * 1000
    log_historial_consulta(norm, len(rows), round(tiempo_ms, 2))
    adj_por_envio: dict = defaultdict(list)
    ids_rows = [r.id for r in rows]
    if ids_rows:
        aq = (
            select(EnvioNotificacionAdjunto)
            .where(EnvioNotificacionAdjunto.envio_notificacion_id.in_(ids_rows))
            .order_by(EnvioNotificacionAdjunto.envio_notificacion_id, EnvioNotificacionAdjunto.orden)
        )
        for a in db.execute(aq).scalars().all():
            adj_por_envio[a.envio_notificacion_id].append(
                {"id": a.id, "nombre_archivo": a.nombre_archivo or "", "orden": a.orden}
            )
    items = [
        {
            "id": r.id,
            "fecha_envio": r.fecha_envio.isoformat() if r.fecha_envio else None,
            "tipo_tab": r.tipo_tab or "",
            "asunto": getattr(r, "asunto", None) or (f"Notificación {r.tipo_tab}" if r.tipo_tab else "Envío"),
            "email": r.email or "",
            "nombre": r.nombre or "",
            "cedula": r.cedula or "",
            "exito": bool(r.exito),
            "estado_envio": "entregado" if r.exito else "rebotado",
            "error_mensaje": r.error_mensaje,
            "prestamo_id": r.prestamo_id,
            "correlativo": r.correlativo,
            "adjuntos": adj_por_envio.get(r.id, []),
            "tiene_mensaje_html": bool((getattr(r, "mensaje_html", None) or "").strip()),
            "tiene_mensaje_texto": bool((getattr(r, "mensaje_texto", None) or "").strip()),
            "tiene_mensaje_pdf": bool(
                (getattr(r, "mensaje_html", None) or "").strip()
                or (getattr(r, "mensaje_texto", None) or "").strip()
            ),
            "tiene_comprobante_pdf": bool(getattr(r, "comprobante_pdf", None)),
        }
        for r in rows
    ]
    return {"items": items, "total": len(items), "cedula": cedula.strip()}


def _generar_excel_historial_cedula(items: List[dict], cedula: str) -> bytes:
    """Genera Excel con historial de notificaciones por cÃƒÂ©dula."""
    import io
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Historial notificaciones"
    ws.append(["Fecha envío", "Tipo", "Asunto", "Email", "Nombre", "Cédula", "Estado", "Error", "ID Préstamo", "Correlativo"])
    for r in items:
        ws.append([
            r.get("fecha_envio") or "",
            r.get("tipo_tab") or "",
            r.get("asunto") or "",
            r.get("email") or "",
            r.get("nombre") or "",
            r.get("cedula") or "",
            r.get("estado_envio") == "entregado" and "Entregado" or "Rebotado",
            r.get("error_mensaje") or "",
            r.get("prestamo_id") or "",
            r.get("correlativo") or "",
        ])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@router.get("/historial-por-cedula/excel")
def get_historial_por_cedula_excel(
    cedula: str = Query(..., min_length=1, description="CÃƒÂ©dula del cliente"),
    db: Session = Depends(get_db),
):
    """Descarga Excel con historial de notificaciones para la cÃƒÂ©dula indicada."""
    try:
        data = get_historial_notificaciones_por_cedula(cedula=cedula, db=db)
        items = data.get("items") or []
        content = _generar_excel_historial_cedula(items, data.get("cedula") or cedula)
        log_historial_excel(data.get("cedula") or cedula, len(items), True)
    except Exception as e:
        log_historial_excel(cedula, 0, False, error=str(e))
        raise
    filename = f"historial_notificaciones_{(data.get('cedula') or cedula).replace(' ', '_')[:30]}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/historial-por-cedula/{envio_id}/comprobante")
def get_comprobante_envio_redirect_pdf(
    envio_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Redirige al comprobante en PDF (unico formato oficial). Mantiene la ruta antigua por compatibilidad.
    """
    row = db.get(EnvioNotificacion, envio_id)
    if not row:
        log_historial_comprobante(envio_id, False, error="no_encontrado")
        raise HTTPException(
            status_code=404,
            detail="Registro de env\u00edo no encontrado",
        )
    log_historial_comprobante(envio_id, True)
    base = str(request.url.path).rsplit("/comprobante", 1)[0]
    return RedirectResponse(url=f"{base}/comprobante-pdf", status_code=307)


def _safe_download_filename(name: str, fallback: str) -> str:
    n = (name or "").strip() or fallback
    for ch in ("\\", "/", ":", "*", "?", '"', "<", ">", "|"):
        n = n.replace(ch, "_")
    n = n.strip() or fallback
    return n[:200] if len(n) > 200 else n


@router.get("/historial-por-cedula/{envio_id}/mensaje-html")
def get_historial_envio_mensaje_html_redirect_pdf(
    envio_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Compatibilidad: redirige al PDF del cuerpo (formato oficial para constancia).
    El HTML crudo ya no se expone como descarga separada.
    """
    row = db.get(EnvioNotificacion, envio_id)
    if not row:
        raise HTTPException(status_code=404, detail="Registro de envío no encontrado")
    has_body = bool((row.mensaje_html or "").strip() or (row.mensaje_texto or "").strip())
    if not has_body:
        raise HTTPException(
            status_code=404,
            detail="No hay cuerpo del mensaje almacenado (envíos anteriores a la versión con snapshot).",
        )
    base = str(request.url.path).rsplit("/mensaje-html", 1)[0]
    return RedirectResponse(url=f"{base}/mensaje-pdf", status_code=307)


@router.get("/historial-por-cedula/{envio_id}/mensaje-pdf")
def get_historial_envio_mensaje_pdf(
    envio_id: int,
    db: Session = Depends(get_db),
):
    """Cuerpo del correo en PDF (desde HTML o texto plano guardado al enviar)."""
    from app.services.envio_notificacion_mensaje_pdf import generar_mensaje_envio_pdf_bytes

    row = db.get(EnvioNotificacion, envio_id)
    if not row:
        raise HTTPException(status_code=404, detail="Registro de envío no encontrado")
    pdf = generar_mensaje_envio_pdf_bytes(row)
    if not pdf:
        raise HTTPException(
            status_code=404,
            detail="No hay cuerpo del mensaje almacenado o no se pudo generar el PDF.",
        )
    fn = _safe_download_filename(
        f"mensaje_notificacion_{row.id}.pdf",
        f"mensaje_notificacion_{row.id}.pdf",
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fn}"'},
    )


@router.get("/historial-por-cedula/{envio_id}/mensaje-texto")
def get_historial_envio_mensaje_texto(
    envio_id: int,
    db: Session = Depends(get_db),
):
    """Cuerpo en texto plano del correo guardado al enviar."""
    row = db.get(EnvioNotificacion, envio_id)
    if not row:
        raise HTTPException(status_code=404, detail="Registro de envío no encontrado")
    if not (row.mensaje_texto or "").strip():
        raise HTTPException(
            status_code=404,
            detail="No hay cuerpo de texto almacenado (envíos anteriores a la versión con snapshot).",
        )
    body = row.mensaje_texto.encode("utf-8")
    fn = _safe_download_filename(f"mensaje_notificacion_{row.id}.txt", f"mensaje_notificacion_{row.id}.txt")
    return Response(
        content=body,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fn}"'},
    )


@router.get("/historial-por-cedula/{envio_id}/adjunto/{adjunto_id}")
def get_historial_envio_adjunto(
    envio_id: int,
    adjunto_id: int,
    db: Session = Depends(get_db),
):
    """Un adjunto PDF (u otro binario) tal como se envió."""
    adj = db.get(EnvioNotificacionAdjunto, adjunto_id)
    if not adj or adj.envio_notificacion_id != envio_id:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")
    fn = _safe_download_filename(adj.nombre_archivo, f"adjunto_{adj.id}.pdf")
    media = "application/pdf" if fn.lower().endswith(".pdf") else "application/octet-stream"
    return Response(
        content=bytes(adj.contenido),
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{fn}"'},
    )


@router.get("/historial-por-cedula/{envio_id}/comprobante-pdf")
def get_historial_envio_comprobante_pdf(
    envio_id: int,
    db: Session = Depends(get_db),
):
    """Comprobante de envio en PDF (snapshot al enviar o regenerado al vuelo si falta)."""
    from app.services.envio_notificacion_comprobante_pdf import generar_comprobante_envio_pdf_bytes

    row = db.get(EnvioNotificacion, envio_id)
    if not row:
        raise HTTPException(status_code=404, detail="Registro de envio no encontrado")
    pdf = row.comprobante_pdf
    if not pdf:
        pdf = generar_comprobante_envio_pdf_bytes(row)
    if not pdf:
        raise HTTPException(
            status_code=404,
            detail="No se pudo generar el comprobante PDF.",
        )
    return Response(
        content=bytes(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="comprobante_notificacion_{row.id}.pdf"'},
    )


@router.get("/clientes-retrasados", response_model=dict)
def get_clientes_retrasados(
    db: Session = Depends(get_db),
    fecha_caracas: Optional[str] = Query(
        None,
        description=(
            "Fecha de referencia en America/Caracas (YYYY-MM-DD). "
            "Listado como si fuera ese día (p. ej. envío atrasado). Omitir = hoy."
        ),
    ),
):
    """
    Clientes a notificar por cuotas no pagadas, agrupados por reglas.
    Politica: no se listan avisos antes del vencimiento ni el dia del vencimiento;
    el primer seguimiento es el dia calendario siguiente (ej. vence 22 -> entra el 23).
    1. 1 dia despues del vencimiento (ayer fue la fecha de vencimiento)
    2. 5 dias despues del vencimiento
    3. 30 dias despues del vencimiento
    4. Credito pagado (liquidados): prestamos con estado LIQUIDADO (misma columna estado en BD).
       Se muestran total_financiamiento y suma de abonos en cuotas para referencia.
    Claves dias_5, dias_3, dias_1, hoy se devuelven vacias (compatibilidad API).
    Datos desde BD: cuotas pendientes filtradas por fecha_vencimiento (hoy-1, hoy-5, hoy-30)
    y tabla prestamos/cuotas (liquidados).
    Solo cuotas con fecha_pago nula: si se registra un pago que liquida la cuota,
    deja de listarse en la siguiente lectura (sin depender de un job de refresco).
    """
    try:
        ref_opt = parse_fecha_referencia_negocio(fecha_caracas)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    hoy = ref_opt or hoy_negocio()
    fechas_retraso = (hoy - timedelta(days=1), hoy - timedelta(days=5), hoy - timedelta(days=30))
    try:
        rows = get_cuotas_pendientes_por_vencimientos(db, fechas_retraso)
    except Exception as e:
        logger.exception("clientes-retrasados: error cargando cuotas pendientes: %s", e)
        raise HTTPException(
            status_code=503,
            detail="No se pudieron cargar las cuotas pendientes. Reintente en unos segundos.",
        ) from e

    dias_5: List[dict] = []
    dias_3: List[dict] = []
    dias_1: List[dict] = []
    hoy_list: List[dict] = []
    dias_1_atraso: List[dict] = []   # 1 día atrasado (cuota vencida ayer)
    dias_5_atraso: List[dict] = []   # 5 días atrasado (cuota vencida hace 5 días)
    dias_30_atraso: List[dict] = []  # 30 días atrasado (cuota vencida hace 30 días)

    pids_retraso = [c.prestamo_id for c, _ in rows]
    counts_retraso = contar_cuotas_atraso_por_prestamos(
        db, pids_retraso, fecha_referencia=hoy
    )
    totales_pendiente_retraso = sum_saldo_pendiente_total_por_prestamos(
        db, pids_retraso
    )

    for (cuota, cliente) in rows:
        fv = cuota.fecha_vencimiento
        if not fv:
            continue
        delta = (fv - hoy).days

        # No notificar antes ni el dia del vencimiento; solo desde el dia siguiente.
        if delta < 0:
            dias_atraso = -delta
            ca = counts_retraso.get(cuota.prestamo_id, 0)
            tp = totales_pendiente_retraso.get(cuota.prestamo_id)
            if dias_atraso == 1:
                dias_1_atraso.append(
                    _item(
                        cliente,
                        cuota,
                        dias_atraso=1,
                        cuotas_atrasadas=ca,
                        total_pendiente_pagar=tp,
                    )
                )
            elif dias_atraso == 5:
                dias_5_atraso.append(
                    _item(
                        cliente,
                        cuota,
                        dias_atraso=5,
                        cuotas_atrasadas=ca,
                        total_pendiente_pagar=tp,
                    )
                )
            elif dias_atraso == 30:
                dias_30_atraso.append(
                    _item(
                        cliente,
                        cuota,
                        dias_atraso=30,
                        cuotas_atrasadas=ca,
                        total_pendiente_pagar=tp,
                    )
                )

    enriquecer_items_notificacion_revision_manual(
        db, dias_1_atraso + dias_5_atraso + dias_30_atraso
    )

    # Crédito pagado: préstamos en estado LIQUIDADO (alineado con prestamos.estado).
    subq = (
        select(Cuota.prestamo_id, func.coalesce(func.sum(Cuota.total_pagado), 0).label("total_abonos"))
        .group_by(Cuota.prestamo_id)
    ).subquery()
    # Core tables only: el ORM Prestamo incluye fecha_liquidado en el mapper y SQLAlchemy
    # expande a todas las columnas al unir con Cliente; si la migracion no esta en BD, falla.
    p_t = Prestamo.__table__
    c_t = Cliente.__table__
    q_liq = (
        select(
            p_t.c.id.label("prestamo_id"),
            p_t.c.total_financiamiento,
            c_t.c.id.label("cliente_id"),
            c_t.c.nombres,
            c_t.c.cedula,
            subq.c.total_abonos,
        )
        .select_from(
            p_t.join(c_t, p_t.c.cliente_id == c_t.c.id).join(
                subq, p_t.c.id == subq.c.prestamo_id
            )
        )
        .where(p_t.c.estado == "LIQUIDADO")
    )
    liquidados: List[dict] = []
    try:
        rows_liq = db.execute(q_liq).all()
        for row in rows_liq:
            m = row._mapping
            liquidados.append({
                "cliente_id": m["cliente_id"],
                "nombre": m.get("nombres") or "",
                "cedula": m.get("cedula") or "",
                "prestamo_id": m["prestamo_id"],
                "total_financiamiento": to_finite_float_or_zero(m.get("total_financiamiento")),
                "total_abonos": to_finite_float_or_zero(m.get("total_abonos")),
            })
    except Exception as e:
        logger.exception(
            "clientes-retrasados: error liquidados (respuesta parcial sin lista liquidados): %s",
            e,
        )

    return {
        "actualizado_en": hoy.isoformat(),
        "fecha_referencia_caracas": hoy.isoformat(),
        "fecha_caracas_solicitada": ref_opt.isoformat() if ref_opt else None,
        "dias_5": dias_5,
        "dias_3": dias_3,
        "dias_1": dias_1,
        "hoy": hoy_list,
        "dias_1_atraso": dias_1_atraso,
        "dias_5_atraso": dias_5_atraso,
        "dias_30_atraso": dias_30_atraso,
        "liquidados": liquidados,
    }


@router.get("/cuotas-pendiente-2-dias-antes", response_model=dict)
def get_cuotas_pendiente_2_dias_antes(
    db: Session = Depends(get_db),
    fecha_caracas: Optional[str] = Query(
        None,
        description=(
            "Fecha de referencia en America/Caracas (YYYY-MM-DD). "
            "Listado de cuotas con vencimiento = esta fecha + 2 días. Omitir = hoy."
        ),
    ),
):
    """
    Listado ligero: solo cuotas en estado PENDIENTE con fecha_vencimiento = hoy + 2 (Caracas),
    excluyendo préstamos sin cuotas en atraso (cuotas_atrasadas = 0: al corriente en vencimientos pasados).
    Submenú «2 días antes»; configuración de envíos independiente (PAGO_2_DIAS_ANTES_PENDIENTE).
    """
    try:
        ref_opt = parse_fecha_referencia_negocio(fecha_caracas)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    hoy = ref_opt or hoy_negocio()
    try:
        items = build_cuotas_pendiente_2_dias_antes_items(db, fecha_referencia=hoy)
    except Exception as e:
        logger.exception("cuotas-pendiente-2-dias-antes: %s", e)
        raise HTTPException(
            status_code=503,
            detail="No se pudo cargar el listado. Reintente en unos segundos.",
        ) from e
    return {
        "actualizado_en": hoy.isoformat(),
        "fecha_referencia_caracas": hoy.isoformat(),
        "fecha_caracas_solicitada": ref_opt.isoformat() if ref_opt else None,
        "items": items,
        "total": len(items),
    }


def ejecutar_actualizacion_notificaciones(db: Session) -> dict:
    """
    Punto de entrada para el botón «Actualización manual» del frontend.

    Los listados (clientes-retrasados, cuotas-pendiente-2-dias-antes, etc.) se leen en vivo desde la BD.
    La columna «Diferencia abono» (submódulo General) usa la caché `prestamos.abonos_drive_cuotas_cache`,
    recalculada en servidor una vez al día a las 02:00 America/Caracas (y al aplicar ABONOS desde la UI);
    este botón no fuerza ese recálculo. Este endpoint devuelve 200 para que el cliente invalide React Query
    y vuelva a cargar listados.

    No realiza escrituras en BD ni modifica ningún estado.
    """
    return {"mensaje": "Actualización solicitada. Los listados se recargarán desde la BD.", "clientes_actualizados": 0}


@router.post("/actualizar")
def actualizar_notificaciones(db: Session = Depends(get_db)):
    """
    Dispara el refresco de listados de notificaciones en el cliente.
    No escribe en BD: los datos de mora son en tiempo real (consulta directa a cuotas/préstamos).
    El frontend invalida su caché de React Query tras recibir 200.
    """
    return ejecutar_actualizacion_notificaciones(db)


def _run_refresh_abonos_drive_cache_bg() -> None:
    """Misma lógica que el job domingo 02:00 Caracas; sesión propia para no mezclar con el request HTTP."""
    db = SessionLocal()
    try:
        from app.services.abonos_drive_cuotas_cache_job import (
            ejecutar_refresh_abonos_drive_cuotas_cache_nightly,
        )

        res = ejecutar_refresh_abonos_drive_cuotas_cache_nightly(db)
        logger.info(
            "[notificaciones] refresh_abonos_drive_cache background resultado=%s",
            res,
        )
    except Exception:
        logger.exception("[notificaciones] refresh_abonos_drive_cache background error")
    finally:
        db.close()


@router.post("/refresh-abonos-drive-cache")
def post_refresh_abonos_drive_cache(background_tasks: BackgroundTasks):
    """
    Programa en segundo plano el recálculo de `prestamos.abonos_drive_cuotas_cache`
    (columna «Diferencia abono» en General). Igual criterio que el cron domingo 02:00 Caracas;
    en carteras grandes puede tardar varios minutos. Tras terminar, el cliente debe volver a
    cargar listados (p. ej. «Actualización manual»).
    """
    background_tasks.add_task(_run_refresh_abonos_drive_cache_bg)
    return {
        "ok": True,
        "mensaje": (
            "Recálculo de caché «Diferencia abono» programado en segundo plano. "
            "Cuando termine (varios minutos), use «Actualización manual» o recargue la vista."
        ),
    }


def _run_refresh_fecha_entrega_q_cache_bg() -> None:
    db = SessionLocal()
    try:
        from app.services.fecha_entrega_q_aprobacion_cache_job import (
            ejecutar_refresh_fecha_entrega_q_aprobacion_cache_nightly,
        )

        res = ejecutar_refresh_fecha_entrega_q_aprobacion_cache_nightly(db)
        logger.info(
            "[notificaciones] refresh_fecha_entrega_q_cache background resultado=%s",
            res,
        )
    except Exception:
        logger.exception("[notificaciones] refresh_fecha_entrega_q_cache background error")
    finally:
        db.close()


@router.post("/refresh-fecha-entrega-q-cache")
def post_refresh_fecha_entrega_q_cache(background_tasks: BackgroundTasks):
    """
    Programa en segundo plano el recálculo de `prestamos.fecha_entrega_q_aprobacion_cache`
    (submódulo Notificaciones «Fecha»: columna Q de la hoja vs `fecha_aprobacion` en BD).
    Misma lógica que el job domingo 04:00 Caracas.
    """
    background_tasks.add_task(_run_refresh_fecha_entrega_q_cache_bg)
    return {
        "ok": True,
        "mensaje": (
            "Recálculo de caché «Fecha Q vs aprobación» programado en segundo plano. "
            "Cuando termine (varios minutos), use «Actualización manual» o recargue la vista."
        ),
    }


def build_prejudicial_items(
    db: Session, fecha_referencia: Optional[date] = None
) -> List[dict]:
    """
    Solo la lista prejudicial (5+ cuotas con estado VENCIDO/MORA, vencidas, saldo pendiente).
    No ejecuta la rama de retrasadas 1/3/5/30 ni contar_cuotas_atraso_por_prestamos masivo.

    GET /notificaciones-prejudicial debe usar esto (no get_notificaciones_tabs_data entero) para
    evitar timeouts en carteras grandes / cold start en Render.
    """
    hoy = fecha_referencia or hoy_negocio()
    # Agrupar por titular del préstamo (prestamos.cliente_id). cuotas.cliente_id es denormalizado
    # y si diverge, el listado prejudicial mezclaba contacto de un titular con montos de otro crédito.
    subq = (
        select(Prestamo.cliente_id, func.count(Cuota.id).label("total"))
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .where(
            Cuota.fecha_pago.is_(None),
            Cuota.estado.in_(ESTADOS_CUOTA_VENCIDO_Y_MORA),
            Cuota.fecha_vencimiento < hoy,
            SALDO_PENDIENTE_CUOTA > TOL_SALDO_CUOTA_NOTIFICACION,
            ~Prestamo.estado.in_(("LIQUIDADO", "DESISTIMIENTO")),
        )
        .group_by(Prestamo.cliente_id)
        .having(func.count(Cuota.id) >= PREJUDICIAL_MIN_CUOTAS_VENCIDO_MORA)
    )
    rows = db.execute(subq).all()
    if not rows:
        return []

    cliente_ids = [int(r[0]) for r in rows if r[0] is not None]
    totals_by_cliente = {int(r[0]): int(r[1]) for r in rows if r[0] is not None}

    clientes_map = {
        c.id: c
        for c in db.scalars(select(Cliente).where(Cliente.id.in_(cliente_ids))).all()
    }

    cuotas_rows = db.execute(
        select(Cuota, Prestamo.cliente_id)
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .where(
            Prestamo.cliente_id.in_(cliente_ids),
            Cuota.fecha_pago.is_(None),
            Cuota.estado.in_(ESTADOS_CUOTA_VENCIDO_Y_MORA),
            Cuota.fecha_vencimiento < hoy,
            SALDO_PENDIENTE_CUOTA > TOL_SALDO_CUOTA_NOTIFICACION,
            ~Prestamo.estado.in_(("LIQUIDADO", "DESISTIMIENTO")),
        )
    ).all()

    primera_por_cliente: dict[int, Cuota] = {}
    for c, titular_id in cuotas_rows:
        if titular_id is None:
            continue
        tid = int(titular_id)
        cur = primera_por_cliente.get(tid)
        if cur is None:
            primera_por_cliente[tid] = c
            continue
        cfv = c.fecha_vencimiento
        pfv = cur.fecha_vencimiento
        if pfv is None or (cfv is not None and cfv < pfv):
            primera_por_cliente[tid] = c

    bloques_prej: List[tuple] = []
    pids_prej: List[int] = []
    for cid in cliente_ids:
        cliente = clientes_map.get(cid)
        if not cliente:
            continue
        total_cuotas = totals_by_cliente.get(cid, 0)
        cuota_ref = primera_por_cliente.get(cid)
        if not cuota_ref:
            cuota_ref = type(
                "DummyCuota",
                (),
                {
                    "fecha_vencimiento": hoy,
                    "numero_cuota": 0,
                    "monto": 0,
                    "prestamo_id": None,
                },
            )()
        pid = getattr(cuota_ref, "prestamo_id", None)
        if pid:
            pids_prej.append(int(pid))
        bloques_prej.append((cliente, cuota_ref, total_cuotas, pid))

    totales_prej = sum_saldo_pendiente_total_por_prestamos(db, pids_prej)
    prejudicial: List[dict] = []
    for cliente, cuota_ref, total_cuotas, pid in bloques_prej:
        tp = totales_prej.get(int(pid)) if pid is not None else None
        item = _item_tab(cliente, cuota_ref, total_pendiente_pagar=tp)
        item["total_cuotas_atrasadas"] = total_cuotas
        prejudicial.append(item)
    enriquecer_items_notificacion_revision_manual(db, prejudicial)
    return prejudicial


def get_notificaciones_tabs_data(
    db: Session, fecha_referencia: Optional[date] = None
):
    """
    Datos para envio de notificaciones (retrasadas, prejudicial).
    Politica: sin listas previas ni "hoy vence"; solo cuotas ya vencidas (1/3/5 dias de atraso)
    y prejudicial. Claves dias_5, dias_3, dias_1, hoy van vacias (compat API).
    Fuente: cuotas pendientes con fecha_vencimiento en {hoy-1, hoy-3, hoy-5, hoy-30} (consulta acotada).
    Fecha de corte: America/Caracas.

    Pestaña 1 día de retraso (dias_1_retraso): cuota con vencimiento = ayer (exactamente 1 día
    calendario después de la fecha de vencimiento), sin fecha_pago y con saldo pendiente.

    Prejudicial: por titular del préstamo (prestamos.cliente_id), al menos el mínimo configurado
    de cuotas con cuotas.estado en (VENCIDO, MORA), fecha_vencimiento < hoy, sin fecha_pago y
    saldo pendiente; préstamo no liquidado/desistimiento.
    """
    hoy = fecha_referencia or hoy_negocio()
    fechas_retraso = (
        hoy - timedelta(days=1),
        hoy - timedelta(days=3),
        hoy - timedelta(days=5),
        hoy - timedelta(days=30),
    )
    rows = get_cuotas_pendientes_por_vencimientos(db, fechas_retraso)
    pids_tabs = [c.prestamo_id for c, _ in rows]
    counts_tabs = contar_cuotas_atraso_por_prestamos(
        db, pids_tabs, fecha_referencia=hoy
    )
    totales_pendiente_tabs = sum_saldo_pendiente_total_por_prestamos(db, pids_tabs)

    dias_5: List[dict] = []
    dias_3: List[dict] = []
    dias_1: List[dict] = []
    hoy_list: List[dict] = []
    dias_1_retraso: List[dict] = []
    dias_3_retraso: List[dict] = []
    dias_5_retraso: List[dict] = []
    dias_30_retraso: List[dict] = []

    for (cuota, cliente) in rows:
        fv = cuota.fecha_vencimiento
        if not fv:
            continue
        delta = (fv - hoy).days

        if delta < 0:
            dias_atraso = -delta
            ca = counts_tabs.get(cuota.prestamo_id, 0)
            tp = totales_pendiente_tabs.get(cuota.prestamo_id)
            if dias_atraso == 1:
                dias_1_retraso.append(
                    _item_tab(
                        cliente,
                        cuota,
                        dias_atraso=1,
                        cuotas_atrasadas=ca,
                        total_pendiente_pagar=tp,
                    )
                )
            elif dias_atraso == 3:
                dias_3_retraso.append(
                    _item_tab(
                        cliente,
                        cuota,
                        dias_atraso=3,
                        cuotas_atrasadas=ca,
                        total_pendiente_pagar=tp,
                    )
                )
            elif dias_atraso == 5:
                dias_5_retraso.append(
                    _item_tab(
                        cliente,
                        cuota,
                        dias_atraso=5,
                        cuotas_atrasadas=ca,
                        total_pendiente_pagar=tp,
                    )
                )
            elif dias_atraso == 30:
                dias_30_retraso.append(
                    _item_tab(
                        cliente,
                        cuota,
                        dias_atraso=30,
                        cuotas_atrasadas=ca,
                        total_pendiente_pagar=tp,
                    )
                )

    prejudicial = build_prejudicial_items(db, fecha_referencia=hoy)
    enriquecer_items_notificacion_revision_manual(
        db,
        dias_1_retraso + dias_3_retraso + dias_5_retraso + dias_30_retraso,
    )

    return {
        "dias_5": dias_5,
        "dias_3": dias_3,
        "dias_1": dias_1,
        "hoy": hoy_list,
        "dias_1_retraso": dias_1_retraso,
        "dias_3_retraso": dias_3_retraso,
        "dias_5_retraso": dias_5_retraso,
        "dias_30_retraso": dias_30_retraso,
        "prejudicial": prejudicial,
    }

@router.get("/diagnostico-paquete-prueba")
def get_diagnostico_paquete_prueba(
    tipo: str = Query("PAGO_1_DIA_ATRASADO"),
    db: Session = Depends(get_db),
):
    """Sin enviar correo: revisa plantilla, adjuntos y paquete estricto para el criterio."""
    from app.services.notificaciones_prueba_paquete import ejecutar_diagnostico_paquete_prueba

    return ejecutar_diagnostico_paquete_prueba(db, tipo)


@router.post("/enviar-prueba-paquete")
def post_enviar_prueba_paquete(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Delega en servicio unico (evita duplicar logica con el router)."""
    from app.services.notificaciones_prueba_paquete import ejecutar_enviar_prueba_paquete

    return ejecutar_enviar_prueba_paquete(db, payload)


@router.get("/comparar-abonos-drive-cuotas")
def get_comparar_abonos_drive_cuotas(
    cedula: str = Query(..., min_length=3, description="Cédula del cliente (como en el listado)"),
    prestamo_id: int = Query(..., description="ID del préstamo para sumar cuotas.total_pagado"),
    lote: Optional[str] = Query(
        None,
        description="Lote (columna LOTE en hoja) cuando hay varios créditos por cédula; debe corresponder al préstamo.",
    ),
    db: Session = Depends(get_db),
):
    """
    Compara ABONOS de la hoja CONCILIACIÓN (snapshot en BD) con la suma de total_pagado en cuotas del préstamo.
    Requiere hoja sincronizada y columnas detectables (cédula + ABONOS).
    Solo suma filas de la hoja que corresponden a este préstamo (huella monto/cuotas/modalidad) o al lote elegido.
    """
    from app.services.comparar_abonos_drive_cuotas_service import comparar_abonos_drive_vs_cuotas

    try:
        return comparar_abonos_drive_vs_cuotas(
            db,
            cedula=cedula.strip(),
            prestamo_id=int(prestamo_id),
            lote=(lote.strip() if isinstance(lote, str) and lote.strip() else None),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/comparar-fecha-entrega-q-aprobacion")
def get_comparar_fecha_entrega_q_aprobacion(
    cedula: str = Query(..., min_length=3, description="Cédula del cliente (como en el listado)"),
    prestamo_id: int = Query(..., description="ID del préstamo para leer fecha_aprobacion y alinear fila de la hoja"),
    lote: Optional[str] = Query(
        None,
        description="Lote (columna LOTE en hoja) cuando hay varios créditos por cédula; debe corresponder al préstamo.",
    ),
    db: Session = Depends(get_db),
):
    """
    Compara la columna Q de la hoja CONCILIACIÓN (snapshot en BD) con `prestamos.fecha_aprobacion`.
    Misma alineación de fila que ABONOS (cédula + huella + lote). No persiste caché (lectura en vivo).
    """
    from app.services.comparar_fecha_entrega_q_aprobacion_service import (
        comparar_fecha_entrega_column_q_vs_aprobacion,
    )

    try:
        return comparar_fecha_entrega_column_q_vs_aprobacion(
            db,
            cedula=cedula.strip(),
            prestamo_id=int(prestamo_id),
            lote=(lote.strip() if isinstance(lote, str) and lote.strip() else None),
            persist_cache=False,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/aplicar-fecha-entrega-q-como-fecha-aprobacion")
def post_aplicar_fecha_entrega_q_como_fecha_aprobacion(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    admin: UserResponse = Depends(require_admin),
):
    """
    Persiste en `prestamos.fecha_aprobacion` (y alinea `fecha_base_calculo`) la fecha de entrega
    leída en la columna Q de CONCILIACIÓN para la fila alineada al préstamo, y recalcula fechas de
    vencimiento de cuotas cuando aplica la misma regla que `PUT /prestamos/{id}`.

    Requisitos (misma lectura en vivo que GET comparar-fecha-entrega-q-aprobacion):
    - La fecha Q debe ser estrictamente posterior a la fecha de aprobación actual en BD.
    - La fecha Q debe ser igual o posterior a `fecha_requerimiento` del préstamo.
    - No opera sobre préstamos en desistimiento (bloqueo del PUT estándar).

    Tras el PUT, intenta refrescar `prestamos.fecha_entrega_q_aprobacion_cache` con la comparación
    actualizada (fallo del caché no revierte el préstamo ya confirmado).
    """
    from datetime import time as time_cls

    from app.schemas.prestamo import PrestamoUpdate
    from app.services.comparar_fecha_entrega_q_aprobacion_service import (
        comparar_fecha_entrega_column_q_vs_aprobacion,
    )
    from app.api.v1.endpoints.prestamos import update_prestamo

    cedula = str(payload.get("cedula") or "").strip()
    pid_raw = payload.get("prestamo_id")
    lote_raw = payload.get("lote")
    lote = str(lote_raw).strip() if lote_raw is not None and str(lote_raw).strip() else None
    try:
        prestamo_id = int(pid_raw)
    except (TypeError, ValueError):
        prestamo_id = 0

    if not cedula or prestamo_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="Indique cédula y prestamo_id válidos.",
        )

    try:
        cmp = comparar_fecha_entrega_column_q_vs_aprobacion(
            db,
            cedula=cedula,
            prestamo_id=prestamo_id,
            lote=lote,
            persist_cache=False,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if not bool(cmp.get("puede_aplicar")):
        raise HTTPException(
            status_code=400,
            detail=(
                "Solo se puede confirmar cuando la fecha de la columna Q es estrictamente "
                "posterior a la fecha de aprobación actual en el sistema."
            ),
        )

    fq_iso = cmp.get("fecha_entrega_column_q")
    if not fq_iso:
        raise HTTPException(
            status_code=400,
            detail="No hay fecha interpretable en la columna Q para esta fila y préstamo.",
        )

    try:
        fecha_q = date.fromisoformat(str(fq_iso)[:10])
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail="No se pudo interpretar la fecha Q como calendario (YYYY-MM-DD).",
        ) from e

    row = db.get(Prestamo, prestamo_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado.")

    req = getattr(row, "fecha_requerimiento", None)
    if isinstance(req, datetime):
        req_d = req.date()
    else:
        req_d = req
    if req_d is not None and fecha_q < req_d:
        raise HTTPException(
            status_code=400,
            detail="La fecha Q es anterior a la fecha de requerimiento del préstamo; no se aplica.",
        )

    fa_dt = datetime.combine(fecha_q, time_cls.min)
    try:
        out = update_prestamo(
            prestamo_id,
            PrestamoUpdate(fecha_aprobacion=fa_dt),
            db,
            admin,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "[notificaciones] aplicar-fecha-entrega-q-como-fecha_aprobacion: %s", e
        )
        raise HTTPException(
            status_code=500,
            detail="Error al actualizar la fecha de aprobación del préstamo.",
        ) from e

    try:
        comparar_fecha_entrega_column_q_vs_aprobacion(
            db,
            cedula=cedula,
            prestamo_id=prestamo_id,
            lote=lote,
            persist_cache=True,
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.warning(
            "[notificaciones] aplicar-fecha-q: préstamo actualizado pero falló refresco de caché Q",
            exc_info=True,
        )

    dumped = out.model_dump(mode="json") if hasattr(out, "model_dump") else out
    return {"ok": True, "prestamo": dumped}


@router.post("/aplicar-abonos-drive-a-cuotas")
def post_aplicar_abonos_drive_a_cuotas(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    admin: UserResponse = Depends(require_admin),
):
    """
    Si ABONOS (hoja) > sum(cuotas.total_pagado): elimina todos los pagos del préstamo (flujo existente)
    y crea un pago único por el monto ABONOS aplicado en cascada (_aplicar_pago_a_cuotas_interno).
    Solo préstamos APROBADO (misma regla que eliminar_todos_pagos_prestamo).
    """
    from app.services.aplicar_abonos_drive_cuotas_service import aplicar_abonos_drive_a_cuotas_prestamo

    cedula = str(payload.get("cedula") or "").strip()
    pid = payload.get("prestamo_id")
    lote_raw = payload.get("lote")
    lote = str(lote_raw).strip() if lote_raw is not None and str(lote_raw).strip() else None
    conf_raw = payload.get("confirmacion_montos_altos")
    if conf_raw is None:
        conf_raw = payload.get("confirmacionMontosAltos")
    confirmacion_montos_altos = (
        str(conf_raw).strip() if conf_raw is not None and str(conf_raw).strip() else None
    )
    try:
        prestamo_id = int(pid)
    except (TypeError, ValueError):
        prestamo_id = 0
    usuario = (admin.email or "").strip() or "admin"

    try:
        out = aplicar_abonos_drive_a_cuotas_prestamo(
            db,
            cedula=cedula,
            prestamo_id=prestamo_id,
            usuario_registro=usuario,
            lote=lote,
            confirmacion_montos_altos=confirmacion_montos_altos,
        )
        db.commit()
        return out
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("[notificaciones] aplicar-abonos-drive-a-cuotas: %s", e)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Error al aplicar ABONOS desde la hoja a las cuotas.",
        ) from e

