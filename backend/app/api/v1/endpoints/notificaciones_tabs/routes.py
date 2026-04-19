"""
Endpoints para notificaciones por cuota (retrasadas 1 dia de atraso, prejudicial).
Routers: solo rol admin (Depends(require_admin)).

Politica: sin envios "previos" ni el dia del vencimiento; previas/dia-pago devuelven listas vacias.
Datos reales desde BD. get_db en todos los procesos.

Paquete de correo al cliente (NOTIFICACIONES_PAQUETE_ESTRICTO=True por defecto):
1) Plantilla de correo: HTML/texto con variables sustituidas por datos del cliente/cuota.
2) PDF variable Carta_Cobranza.pdf: generado con variables de cobranza (plantilla PDF / contexto).
3) Al menos un PDF fijo adicional: documentos de pestaña "Documentos PDF anexos" y/o adjunto global;
   siempre se envia junto al PDF variable cuando el paquete es estricto.

Excepcion PAGO_2_DIAS_ANTES_PENDIENTE («2 dias antes»): no se exige plantilla guardada en BD
(textos por defecto del modulo si falta plantilla_id) ni Carta_Cobranza / adjuntos obligatorios;
los PDFs de pestañas 2 y 3 son opcionales segun la fila de configuracion.
"""
import logging
from datetime import date
from typing import Callable, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_admin
from app.core.email import cuerpo_parece_html, send_email
from app.core.email_config_holder import sync_from_db as sync_email_config_from_db
from app.core.whatsapp_send import send_whatsapp_text
from app.api.v1.endpoints.notificaciones import (
    build_prejudicial_items,
    get_notificaciones_tabs_data,
    get_notificaciones_envios_config,
    get_plantilla_asunto_cuerpo,
    build_contexto_cobranza_para_item,
    contexto_cobranza_aplica_a_prestamo,
    plantilla_usa_variables_cobranza,
)
from app.models.cliente import Cliente
from app.models.plantilla_notificacion import PlantillaNotificacion
from app.models.envio_notificacion import EnvioNotificacion
from app.services.envio_notificacion_snapshot import persistir_snapshot_envio_notificacion
from app.services.notificaciones_envios_store import coerce_modo_pruebas_notificaciones
from app.services.notificaciones_exclusion_desistimiento import (
    cliente_tiene_prestamo_desistimiento,
)
from app.services.carta_cobranza_pdf import generar_carta_cobranza_pdf
from app.services.adjunto_fijo_cobranza import get_adjunto_fijo_cobranza_bytes, get_adjuntos_fijos_por_caso
from app.services.notificacion_service import (
    alinear_items_contacto_titular_prestamo,
    build_cuotas_pendiente_2_dias_antes_items,
)
from app.utils.cliente_emails import (
    lista_correo_principal_para_notificaciones,
    lista_correo_principal_notificaciones_desde_objeto,
    secundario_distinto_del_principal,
    unir_destinatarios_log,
)
from app.services.notificacion_logging import (
    log_envio_inicio,
    log_envio_config,
    log_envio_contexto_cobranza,
    log_envio_adjuntos,
    log_envio_paquete_incompleto,
    log_envio_email,
    log_envio_persistencia,
    log_envio_resumen,
    log_envio_fallo,
)

from app.services.notificaciones_envio_pipeline import (
    ASUNTO_DEFAULT_PAGO_2_DIAS_ANTES_PENDIENTE,
    CUERPO_DEFAULT_PAGO_2_DIAS_ANTES_PENDIENTE,
    NOMBRE_PDF_CARTA_VARIABLE,
    _CONFIG_TIPO_TO_TAB,
    _adjuntos_cumplen_paquete_completo,
    _bytes_son_pdf_valido,
    _cfg_incluir_pdf_anexo,
    _enviar_correos_items,
    _parse_plantilla_id_desde_config,
    _tipo_dos_dias_antes_solo_correo,
    _tipo_tab_para_persistencia,
    _validar_plantilla_email_estricta,
)


def _fecha_referencia_desde_query(fecha_caracas: Optional[str]) -> Optional[date]:
    from app.services.cuota_estado import parse_fecha_referencia_negocio

    try:
        return parse_fecha_referencia_negocio(fecha_caracas)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


router_previas = APIRouter(dependencies=[Depends(require_admin)])
router_dia_pago = APIRouter(dependencies=[Depends(require_admin)])
router_retrasadas = APIRouter(dependencies=[Depends(require_admin)])
router_prejudicial = APIRouter(dependencies=[Depends(require_admin)])
router_masivos = APIRouter(dependencies=[Depends(require_admin)])

logger = logging.getLogger(__name__)

# --- Notificaciones previas (5, 3, 1 d�as antes) ---

_FC_Q = Query(
    None,
    description=(
        "Fecha de referencia America/Caracas (YYYY-MM-DD). Listado/envio como si fuera ese dia. "
        "Omitir = hoy en Caracas."
    ),
)


@router_previas.get("")
def get_notificaciones_previas(
    estado: str = None,
    fecha_caracas: Optional[str] = _FC_Q,
    db: Session = Depends(get_db),
):
    """Lista de notificaciones previas: cuotas que vencen en 5, 3 o 1 d�a. Verifica c�dula y email en tabla clientes."""
    fecha_ref = _fecha_referencia_desde_query(fecha_caracas)
    data = get_notificaciones_tabs_data(db, fecha_referencia=fecha_ref)
    items = data["dias_5"] + data["dias_3"] + data["dias_1"]
    return {
        "items": items,
        "total": len(items),
        "dias_5": len(data["dias_5"]),
        "dias_3": len(data["dias_3"]),
        "dias_1": len(data["dias_1"]),
    }


def _tipo_previas(item: dict) -> str:
    d = item.get("dias_antes_vencimiento")
    return {5: "PAGO_5_DIAS_ANTES", 3: "PAGO_3_DIAS_ANTES", 1: "PAGO_1_DIA_ANTES"}.get(d, "PAGO_5_DIAS_ANTES")


@router_previas.post("/enviar")
def enviar_notificaciones_previas(
    fecha_caracas: Optional[str] = _FC_Q,
    db: Session = Depends(get_db),
):
    """Env�a correo a cada cliente en notificaciones previas. Respeta config env�os (habilitado/CCO) desde BD."""
    fecha_ref = _fecha_referencia_desde_query(fecha_caracas)
    config_envios = get_notificaciones_envios_config(db)
    data = get_notificaciones_tabs_data(db, fecha_referencia=fecha_ref)
    items = data["dias_5"] + data["dias_3"] + data["dias_1"]
    asunto = "Recordatorio: cuota por vencer - Rapicredit"
    cuerpo = (
        "Estimado/a {nombre} (c�dula {cedula}),\n\n"
        "Le recordamos que tiene una cuota por vencer.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "N�mero de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor realice el pago a tiempo.\n\n"
        "Saludos,\nRapicredit"
    )
    res = _enviar_correos_items(
        items,
        asunto,
        cuerpo,
        config_envios,
        _tipo_previas,
        db,
        fecha_referencia=fecha_ref,
    )
    return {"mensaje": "Env�o de notificaciones previas finalizado.", **res}


# --- D�a de pago (vence hoy) ---

@router_dia_pago.get("")
def get_notificaciones_dia_pago(
    estado: str = None,
    fecha_caracas: Optional[str] = _FC_Q,
    db: Session = Depends(get_db),
):
    """Lista de notificaciones del d�a de pago: cuotas que vencen hoy. Email desde tabla clientes."""
    fecha_ref = _fecha_referencia_desde_query(fecha_caracas)
    data = get_notificaciones_tabs_data(db, fecha_referencia=fecha_ref)
    items = data["hoy"]
    return {"items": items, "total": len(items)}


def _tipo_dia_pago(_item: dict) -> str:
    return "PAGO_DIA_0"


def _tipo_pago_2_dias_antes_pendiente(_item: dict) -> str:
    return "PAGO_2_DIAS_ANTES_PENDIENTE"


@router_dia_pago.post("/enviar")
def enviar_notificaciones_dia_pago(
    fecha_caracas: Optional[str] = _FC_Q,
    db: Session = Depends(get_db),
):
    """Env�a correo a cada cliente con cuota que vence hoy. Respeta config env�os (habilitado/CCO) desde BD."""
    fecha_ref = _fecha_referencia_desde_query(fecha_caracas)
    config_envios = get_notificaciones_envios_config(db)
    data = get_notificaciones_tabs_data(db, fecha_referencia=fecha_ref)
    items = data["hoy"]
    asunto = "Vencimiento hoy: cuota de pago - Rapicredit"
    cuerpo = (
        "Estimado/a {nombre} (c�dula {cedula}),\n\n"
        "Le informamos que su cuota vence HOY.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "N�mero de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor realice el pago hoy.\n\n"
        "Saludos,\nRapicredit"
    )
    res = _enviar_correos_items(
        items,
        asunto,
        cuerpo,
        config_envios,
        _tipo_dia_pago,
        db,
        fecha_referencia=fecha_ref,
    )
    return {"mensaje": "Env�o de notificaciones d�a de pago finalizado.", **res}


# --- Notificaciones retrasadas (1 dia de atraso; listado agregado legacy) ---

@router_retrasadas.get("")
def get_notificaciones_retrasadas(
    estado: str = None,
    fecha_caracas: Optional[str] = _FC_Q,
    db: Session = Depends(get_db),
):
    """Lista de notificaciones retrasadas: cuotas con 1 dia de atraso calendario. Email desde tabla clientes."""
    fecha_ref = _fecha_referencia_desde_query(fecha_caracas)
    data = get_notificaciones_tabs_data(db, fecha_referencia=fecha_ref)
    # PAGO_10_DIAS_ATRASADO: no forma parte de este listado agregado; solo submodulo + enviar-caso-manual.
    items = list(data["dias_1_retraso"])
    return {
        "items": items,
        "total": len(items),
        "dias_1": len(data["dias_1_retraso"]),
    }


def _tipo_retrasadas(item: dict) -> str:
    d = item.get("dias_atraso")
    return {
        1: "PAGO_1_DIA_ATRASADO",
        10: "PAGO_10_DIAS_ATRASADO",
    }.get(d, "PAGO_1_DIA_ATRASADO")


@router_retrasadas.post("/enviar")
def enviar_notificaciones_retrasadas(
    fecha_caracas: Optional[str] = _FC_Q,
    db: Session = Depends(get_db),
):
    """Env�a correo a cada cliente con cuota retrasada. Respeta config env�os (habilitado/CCO) desde BD."""
    fecha_ref = _fecha_referencia_desde_query(fecha_caracas)
    config_envios = get_notificaciones_envios_config(db)
    data = get_notificaciones_tabs_data(db, fecha_referencia=fecha_ref)
    # Sin dias_10_retraso en este POST agregado: PAGO_10_DIAS_ATRASADO solo por enviar-caso-manual (submodulo dedicado).
    items = list(data["dias_1_retraso"])
    asunto = "Cuenta con cuota atrasada - Rapicredit"
    cuerpo = (
        "Estimado/a {nombre} (c�dula {cedula}),\n\n"
        "Le recordamos que tiene una cuota en mora.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "N�mero de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor regularice su pago lo antes posible.\n\n"
        "Saludos,\nRapicredit"
    )
    res = _enviar_correos_items(
        items,
        asunto,
        cuerpo,
        config_envios,
        _tipo_retrasadas,
        db,
        fecha_referencia=fecha_ref,
    )
    return {"mensaje": "Env�o de notificaciones retrasadas finalizado.", **res}


# --- Notificaciones prejudiciales (5+ cuotas en VENCIDO o MORA) ---

@router_prejudicial.get("")
def get_notificaciones_prejudicial(
    estado: str = None,
    fecha_caracas: Optional[str] = _FC_Q,
    db: Session = Depends(get_db),
):
    """Lista de clientes con 5+ cuotas en estado VENCIDO o MORA (prejudicial). Email desde tabla clientes."""
    fecha_ref = _fecha_referencia_desde_query(fecha_caracas)
    items = build_prejudicial_items(db, fecha_referencia=fecha_ref)
    return {"items": items, "total": len(items)}


def _tipo_prejudicial(_item: dict) -> str:
    return "PREJUDICIAL"


@router_prejudicial.post("/enviar")
def enviar_notificaciones_prejudicial(
    fecha_caracas: Optional[str] = _FC_Q,
    db: Session = Depends(get_db),
):
    """Env�a correo a cada cliente en situaci�n prejudicial. Respeta config env�os (habilitado/CCO) desde BD."""
    fecha_ref = _fecha_referencia_desde_query(fecha_caracas)
    config_envios = get_notificaciones_envios_config(db)
    items = build_prejudicial_items(db, fecha_referencia=fecha_ref)
    asunto = "Aviso prejudicial - Rapicredit"
    cuerpo = (
        "Estimado/a {nombre} (c�dula {cedula}),\n\n"
        "Le informamos que su cuenta presenta varias cuotas en mora.\n"
        "Fecha de vencimiento de referencia: {fecha_vencimiento}\n"
        "Cuota de referencia: {numero_cuota}\n"
        "Monto de referencia: {monto}\n\n"
        "Por favor contacte a la entidad para regularizar su situaci�n.\n\n"
        "Saludos,\nRapicredit"
    )
    res = _enviar_correos_items(
        items,
        asunto,
        cuerpo,
        config_envios,
        _tipo_prejudicial,
        db,
        fecha_referencia=fecha_ref,
    )
    return {"mensaje": "Env�o de notificaciones prejudiciales finalizado.", **res}


def get_items_masivos(db: Session) -> List[dict]:
    """
    Contactos para comunicaciones masivas.

    Fuente principal: vista vw_notificaciones_masivos_contactos (sincronizada en 2 vias).
    Fallback de compatibilidad: tabla clientes si la vista aun no existe.
    """
    items: List[dict] = []

    try:
        rows = db.execute(
            text(
                """
                SELECT id, cliente_id, cedula, nombre, email, email_secundario, telefono, updated_at
                FROM vw_notificaciones_masivos_contactos
                ORDER BY nombre ASC, id ASC
                """
            )
        ).mappings().all()
        for r in rows:
            em = str(r.get("email") or "").strip() or None
            correos = lista_correo_principal_para_notificaciones(em)
            if not correos:
                continue
            _, correo_sec = secundario_distinto_del_principal(em, str(r.get("email_secundario") or "").strip() or None)
            items.append(
                {
                    "cliente_id": r.get("cliente_id"),
                    "nombre": r.get("nombre") or "",
                    "cedula": r.get("cedula") or "",
                    "correo_1": correos[0],
                    "correo_2": correo_sec if correo_sec and "@" in correo_sec else None,
                    "correo": correos[0],
                    "correos": correos,
                    "telefono": str(r.get("telefono") or "").strip(),
                    "estado": "COMUNICACION_GENERAL",
                }
            )
        return [
            it
            for it in items
            if not cliente_tiene_prestamo_desistimiento(db, it.get("cliente_id"))
        ]
    except Exception:
        logger.warning(
            "get_items_masivos: vista vw_notificaciones_masivos_contactos no disponible; usando fallback clientes",
            exc_info=True,
        )

    rows = (
        db.execute(
            select(Cliente)
            .where(Cliente.email.isnot(None), func.length(func.trim(Cliente.email)) > 0)
            .order_by(Cliente.nombres.asc(), Cliente.id.asc())
        )
        .scalars().all()
    )
    for c in rows:
        correos = lista_correo_principal_notificaciones_desde_objeto(c)
        if not correos:
            continue
        _, correo_sec = secundario_distinto_del_principal(
            getattr(c, "email", None),
            getattr(c, "email_secundario", None),
        )
        items.append(
            {
                "cliente_id": c.id,
                "nombre": c.nombres or "",
                "cedula": c.cedula or "",
                "correo_1": correos[0],
                "correo_2": correo_sec if correo_sec and "@" in correo_sec else None,
                "correo": correos[0],
                "correos": correos,
                "telefono": (getattr(c, "telefono", None) or "").strip(),
                "estado": "COMUNICACION_GENERAL",
            }
        )
    return [
        it
        for it in items
        if not cliente_tiene_prestamo_desistimiento(db, it.get("cliente_id"))
    ]


def _tipo_masivos(_item: dict) -> str:
    return "MASIVOS"


def _normalizar_campana_masiva(raw: dict, idx: int) -> dict:
    if not isinstance(raw, dict):
        raw = {}
    camp_id = str(raw.get("id") or f"campana-{idx}").strip() or f"campana-{idx}"
    nombre = str(raw.get("nombre") or f"Campana {idx}").strip() or f"Campana {idx}"
    cco_raw = raw.get("cco")
    cco = [str(e).strip() for e in cco_raw] if isinstance(cco_raw, list) else []
    cco = [e for e in cco if e]
    dias_raw = raw.get("dias_semana")
    dias = []
    if isinstance(dias_raw, list):
        for d in dias_raw:
            try:
                v = int(d)
            except (TypeError, ValueError):
                continue
            if 0 <= v <= 6:
                dias.append(v)
    dias = sorted(set(dias))
    return {
        "id": camp_id,
        "nombre": nombre,
        "habilitado": raw.get("habilitado", True) is not False,
        "plantilla_id": raw.get("plantilla_id"),
        "programador": str(raw.get("programador") or "03:00"),
        "cco": cco,
        "dias_semana": dias,
    }


def get_campanas_masivos_config(config_envios: dict) -> List[dict]:
    raw = config_envios.get("masivos_campanas") if isinstance(config_envios, dict) else None
    if not isinstance(raw, list):
        return []
    return [_normalizar_campana_masiva(c, i + 1) for i, c in enumerate(raw)]


def _norm_cco_list(raw) -> List[str]:
    if not isinstance(raw, list):
        return []
    return [
        str(e).strip()
        for e in raw
        if e and isinstance(e, str) and "@" in str(e).strip()
    ]


def _tipo_cfg_masivos_por_campana(camp: dict, config_envios: dict) -> dict:
    """
    Combina la fila global MASIVOS (tabla de envios) con cada campaña en masivos_campanas.

    La UI guarda plantilla/CCO en la fila «Comunicaciones masivas» y puede repetirlos
    por campaña; si la campaña no tiene plantilla_id, debe usarse el de la fila MASIVOS
    (antes solo se leía camp.plantilla_id y se ignoraba la selección principal).
    """
    base_m = (
        config_envios.get("MASIVOS")
        if isinstance(config_envios.get("MASIVOS"), dict)
        else {}
    )
    cid = _parse_plantilla_id_desde_config(camp.get("plantilla_id"))
    bid = _parse_plantilla_id_desde_config(base_m.get("plantilla_id"))
    plantilla_efectiva = cid if cid else bid

    cco_c = _norm_cco_list(camp.get("cco"))
    cco_b = _norm_cco_list(base_m.get("cco"))
    cco = cco_c if len(cco_c) > 0 else cco_b

    incluir_adj = base_m.get("incluir_adjuntos_fijos", True) is not False

    return {
        "habilitado": True,
        "cco": cco,
        "plantilla_id": plantilla_efectiva,
        "programador": camp.get("programador") or base_m.get("programador") or "03:00",
        "incluir_pdf_anexo": False,
        "incluir_adjuntos_fijos": incluir_adj,
    }


def ejecutar_envio_masivos_por_campanas(
    db: Session,
    config_envios: dict,
    *,
    forzar_habilitado: bool = False,
) -> dict:
    campanas = get_campanas_masivos_config(config_envios)
    base_m_row = (
        config_envios.get("MASIVOS")
        if isinstance(config_envios.get("MASIVOS"), dict)
        else {}
    )
    if not campanas and (
        forzar_habilitado or base_m_row.get("habilitado", True) is not False
    ):
        campanas = [
            _normalizar_campana_masiva(
                {
                    "id": "fila-principal-masivos",
                    "nombre": "Masivos (fila principal)",
                    "habilitado": True,
                    "plantilla_id": base_m_row.get("plantilla_id"),
                    "programador": base_m_row.get("programador") or "03:00",
                    "cco": base_m_row.get("cco")
                    if isinstance(base_m_row.get("cco"), list)
                    else [],
                    "dias_semana": [],
                },
                0,
            )
        ]
    items = get_items_masivos(db)
    base_asunto = "Comunicado oficial - Rapicredit"
    base_cuerpo = (
        "Estimado/a {nombre} (cedula {cedula}),\n\n"
        "Le compartimos este comunicado oficial de Rapicredit.\n"
        "Revise el contenido completo en este correo.\n\n"
        "Saludos,\nRapicredit"
    )

    total_enviados = total_fallidos = total_sin_email = 0
    total_omitidos_config = total_omitidos_paquete = 0
    total_wok = total_wf = 0
    detalles: Dict[str, dict] = {}

    for camp in campanas:
        if not camp.get("habilitado", True) and not forzar_habilitado:
            continue

        tipo_cfg = _tipo_cfg_masivos_por_campana(camp, config_envios)
        cfg_tmp = dict(config_envios)
        cfg_tmp["MASIVOS"] = tipo_cfg

        r = _enviar_correos_items(items, base_asunto, base_cuerpo, cfg_tmp, _tipo_masivos, db)
        detalles[str(camp.get("id") or camp.get("nombre") or "campana")] = {
            "campana": camp,
            **r,
        }
        total_enviados += int(r.get("enviados", 0) or 0)
        total_fallidos += int(r.get("fallidos", 0) or 0)
        total_sin_email += int(r.get("sin_email", 0) or 0)
        total_omitidos_config += int(r.get("omitidos_config", 0) or 0)
        total_omitidos_paquete += int(r.get("omitidos_paquete_incompleto", 0) or 0)
        total_wok += int(r.get("enviados_whatsapp", 0) or 0)
        total_wf += int(r.get("fallidos_whatsapp", 0) or 0)

    return {
        "enviados": total_enviados,
        "fallidos": total_fallidos,
        "sin_email": total_sin_email,
        "omitidos_config": total_omitidos_config,
        "omitidos_paquete_incompleto": total_omitidos_paquete,
        "enviados_whatsapp": total_wok,
        "fallidos_whatsapp": total_wf,
        "total_en_lista": len(items),
        "campanas": detalles,
    }


@router_masivos.get("")
def get_notificaciones_masivos(db: Session = Depends(get_db)):
    """Lista de clientes para comunicaciones masivas (sin relacion con mora/pagos)."""
    items = get_items_masivos(db)
    return {"items": items, "total": len(items)}


@router_masivos.post("/enviar")
def enviar_notificaciones_masivos(db: Session = Depends(get_db)):
    """Envia comunicaciones masivas segun campanas configuradas para MASIVOS."""
    config_envios = get_notificaciones_envios_config(db)
    res = ejecutar_envio_masivos_por_campanas(db, config_envios, forzar_habilitado=True)
    return {"mensaje": "Envio de notificaciones masivas finalizado.", **res}


# Tipos alineados con CRITERIOS_ENVIO_TABLA (frontend) y _CONFIG_TIPO_TO_TAB
TIPOS_CASO_MANUAL = frozenset(
    {
        "PAGO_5_DIAS_ANTES",
        "PAGO_3_DIAS_ANTES",
        "PAGO_1_DIA_ANTES",
        "PAGO_2_DIAS_ANTES_PENDIENTE",
        "PAGO_DIA_0",
        "PAGO_1_DIA_ATRASADO",
        "PAGO_10_DIAS_ATRASADO",
        "PREJUDICIAL",
        "MASIVOS",
    }
)


def _config_envios_forzar_habilitado_caso(config_envios: dict, tipo: str) -> dict:
    """
    Copia superficial de la config de envios con habilitado=True solo para el tipo indicado.
    El envio manual y la prueba de paquete deben ejecutarse aunque el toggle Envio este apagado.
    """
    out = dict(config_envios)
    cur = out.get(tipo)
    merged = dict(cur) if isinstance(cur, dict) else {}
    merged["habilitado"] = True
    out[tipo] = merged
    return out


def _resolver_tipo_envio_manual_fijo(tipo_caso: str) -> Callable[[dict], str]:
    """
    POST /notificaciones/enviar-caso-manual debe usar siempre la misma clave de configuracion
    (plantilla, CCO, PDFs, tipo_tab) para todos los destinatarios del lote, la del caso elegido.

    No usar _tipo_previas / _tipo_retrasadas aqui: infieren por dias_antes_vencimiento / dias_atraso
    de cada fila y pueden mezclar PAGO_1_DIA_ANTES con otro tipo si se usara inferencia por fila.
    """

    def _inner(_item: dict) -> str:
        return tipo_caso

    return _inner


def ejecutar_envio_caso_manual(
    db: Session,
    tipo: str,
    fecha_referencia: Optional[date] = None,
    *,
    respetar_toggle_envio: bool = False,
) -> dict:
    """
    Envio sincrono solo para un criterio (una fila de configuracion: PAGO_1_DIA_ANTES, etc.).
    No programa tareas en segundo plano ni dispara otros casos: un solo tipo por peticion.

    Lista de destinatarios = la misma regla que la pestaña correspondiente; cada correo usa
    unicamente la config de ese tipo (plantilla/CCO/PDF del caso), sin inferir otro tipo por fila.

    fecha_referencia: mismo criterio que ?fecha_caracas= en GET listados (America/Caracas).

    respetar_toggle_envio: si True, respeta habilitado=False de la fila en BD (omitidos_config).
        Reservado para integraciones internas; la API POST /enviar-caso-manual usa False (fuerza habilitado).
    """
    tipo = (tipo or "").strip()
    if tipo not in TIPOS_CASO_MANUAL:
        raise ValueError("tipo_caso_manual_invalido")

    config_raw = get_notificaciones_envios_config(db)
    if respetar_toggle_envio:
        config_envios = dict(config_raw) if isinstance(config_raw, dict) else {}
    else:
        config_envios = _config_envios_forzar_habilitado_caso(config_raw, tipo)

    asunto_prev = "Recordatorio: cuota por vencer - Rapicredit"
    cuerpo_prev = (
        "Estimado/a {nombre} (c\u00e9dula {cedula}),\n\n"
        "Le recordamos que tiene una cuota por vencer.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "N\u00famero de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor realice el pago a tiempo.\n\n"
        "Saludos,\nRapicredit"
    )
    asunto_hoy = "Vencimiento hoy: cuota de pago - Rapicredit"
    cuerpo_hoy = (
        "Estimado/a {nombre} (c\u00e9dula {cedula}),\n\n"
        "Le informamos que su cuota vence HOY.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "N\u00famero de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor realice el pago hoy.\n\n"
        "Saludos,\nRapicredit"
    )
    asunto_ret = "Cuenta con cuota atrasada - Rapicredit"
    cuerpo_ret = (
        "Estimado/a {nombre} (c\u00e9dula {cedula}),\n\n"
        "Le recordamos que tiene una cuota en mora.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "N\u00famero de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor regularice su pago lo antes posible.\n\n"
        "Saludos,\nRapicredit"
    )
    asunto_prej = "Aviso prejudicial - Rapicredit"
    asunto_mas = "Comunicado oficial - Rapicredit"
    cuerpo_prej = (
        "Estimado/a {nombre} (c\u00e9dula {cedula}),\n\n"
        "Le informamos que su cuenta presenta varias cuotas en mora.\n"
        "Fecha de vencimiento de referencia: {fecha_vencimiento}\n"
        "Cuota de referencia: {numero_cuota}\n"
        "Monto de referencia: {monto}\n\n"
        "Por favor contacte a la entidad para regularizar su situaci\u00f3n.\n\n"
        "Saludos,\nRapicredit"
    )
    cuerpo_mas = (
        "Estimado/a {nombre} (cedula {cedula}),\n\n"
        "Le compartimos este comunicado oficial de Rapicredit.\n"
        "Revise el contenido completo en este correo.\n\n"
        "Saludos,\nRapicredit"
    )

    ref = fecha_referencia
    if tipo == "PREJUDICIAL":
        items = build_prejudicial_items(db, fecha_referencia=ref)
        res = _enviar_correos_items(
            items,
            asunto_prej,
            cuerpo_prej,
            config_envios,
            _resolver_tipo_envio_manual_fijo("PREJUDICIAL"),
            db,
            fecha_referencia=ref,
        )
    elif tipo == "MASIVOS":
        items = get_items_masivos(db)
        res = ejecutar_envio_masivos_por_campanas(db, config_envios, forzar_habilitado=True)
    else:
        data = get_notificaciones_tabs_data(db, fecha_referencia=ref)
        if tipo == "PAGO_5_DIAS_ANTES":
            items = data["dias_5"]
            res = _enviar_correos_items(
                items,
                asunto_prev,
                cuerpo_prev,
                config_envios,
                _resolver_tipo_envio_manual_fijo("PAGO_5_DIAS_ANTES"),
                db,
                fecha_referencia=ref,
            )
        elif tipo == "PAGO_3_DIAS_ANTES":
            items = data["dias_3"]
            res = _enviar_correos_items(
                items,
                asunto_prev,
                cuerpo_prev,
                config_envios,
                _resolver_tipo_envio_manual_fijo("PAGO_3_DIAS_ANTES"),
                db,
                fecha_referencia=ref,
            )
        elif tipo == "PAGO_1_DIA_ANTES":
            items = data["dias_1"]
            res = _enviar_correos_items(
                items,
                asunto_prev,
                cuerpo_prev,
                config_envios,
                _resolver_tipo_envio_manual_fijo("PAGO_1_DIA_ANTES"),
                db,
                fecha_referencia=ref,
            )
        elif tipo == "PAGO_2_DIAS_ANTES_PENDIENTE":
            items = build_cuotas_pendiente_2_dias_antes_items(db, fecha_referencia=ref)
            res = _enviar_correos_items(
                items,
                ASUNTO_DEFAULT_PAGO_2_DIAS_ANTES_PENDIENTE,
                CUERPO_DEFAULT_PAGO_2_DIAS_ANTES_PENDIENTE,
                config_envios,
                _resolver_tipo_envio_manual_fijo("PAGO_2_DIAS_ANTES_PENDIENTE"),
                db,
                fecha_referencia=ref,
            )
        elif tipo == "PAGO_DIA_0":
            items = data["hoy"]
            res = _enviar_correos_items(
                items,
                asunto_hoy,
                cuerpo_hoy,
                config_envios,
                _resolver_tipo_envio_manual_fijo("PAGO_DIA_0"),
                db,
                fecha_referencia=ref,
            )
        elif tipo == "PAGO_1_DIA_ATRASADO":
            items = data["dias_1_retraso"]
            res = _enviar_correos_items(
                items,
                asunto_ret,
                cuerpo_ret,
                config_envios,
                _resolver_tipo_envio_manual_fijo("PAGO_1_DIA_ATRASADO"),
                db,
                fecha_referencia=ref,
            )
        elif tipo == "PAGO_10_DIAS_ATRASADO":
            items = data["dias_10_retraso"]
            res = _enviar_correos_items(
                items,
                asunto_ret,
                cuerpo_ret,
                config_envios,
                _resolver_tipo_envio_manual_fijo("PAGO_10_DIAS_ATRASADO"),
                db,
                fecha_referencia=ref,
            )
        else:
            raise ValueError("tipo_caso_manual_invalido")

    return {
        "mensaje": f"Envio manual del caso {tipo} finalizado.",
        "tipo_caso": tipo,
        "total_en_lista": len(items),
        **res,
    }


def ejecutar_envio_todas_notificaciones(db: Session) -> dict:
    """
    Ejecuta en un solo batch varias familias de notificacion: previas, dia de pago, retrasadas,
    prejudicial y masivos. Cada tipo usa su propia configuracion en notificaciones_envios (habilitado,
    CCO, modo pruebas, etc.); no se mezclan entre si.

    No incluye PAGO_2_DIAS_ANTES_PENDIENTE (2 dias antes del vencimiento), que tiene envio propio.
    No incluye PAGO_10_DIAS_ATRASADO (10 dias de atraso): solo POST /notificaciones/enviar-caso-manual desde el submodulo dedicado.

    Solo desde POST /notificaciones/enviar-todas (BackgroundTasks); sin envio automatico por hora.
    """
    config_envios = get_notificaciones_envios_config(db)
    data = get_notificaciones_tabs_data(db)
    total_enviados = 0
    total_fallidos = 0
    total_sin_email = 0
    total_omitidos_config = 0
    total_omitidos_paquete = 0
    total_whatsapp_ok = 0
    total_whatsapp_fail = 0
    detalles = {}

    # Previas (5, 3, 1 d�as antes)
    items_previas = data["dias_5"] + data["dias_3"] + data["dias_1"]
    asunto_p = "Recordatorio: cuota por vencer - Rapicredit"
    cuerpo_p = (
        "Estimado/a {nombre} (c�dula {cedula}),\n\n"
        "Le recordamos que tiene una cuota por vencer.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "N�mero de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor realice el pago a tiempo.\n\n"
        "Saludos,\nRapicredit"
    )
    r = _enviar_correos_items(items_previas, asunto_p, cuerpo_p, config_envios, _tipo_previas, db)
    total_enviados += r.get("enviados", 0)
    total_fallidos += r.get("fallidos", 0)
    total_sin_email += r.get("sin_email", 0)
    total_omitidos_config += r.get("omitidos_config", 0)
    total_omitidos_paquete += r.get("omitidos_paquete_incompleto", 0)
    total_whatsapp_ok += r.get("enviados_whatsapp", 0)
    total_whatsapp_fail += r.get("fallidos_whatsapp", 0)
    detalles["previas"] = r

    # D�a de pago (vence hoy)
    items_hoy = data["hoy"]
    asunto_h = "Vencimiento hoy: cuota de pago - Rapicredit"
    cuerpo_h = (
        "Estimado/a {nombre} (c�dula {cedula}),\n\n"
        "Le informamos que su cuota vence HOY.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "N�mero de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor realice el pago hoy.\n\n"
        "Saludos,\nRapicredit"
    )
    r = _enviar_correos_items(items_hoy, asunto_h, cuerpo_h, config_envios, _tipo_dia_pago, db)
    total_enviados += r.get("enviados", 0)
    total_fallidos += r.get("fallidos", 0)
    total_sin_email += r.get("sin_email", 0)
    total_omitidos_config += r.get("omitidos_config", 0)
    total_omitidos_paquete += r.get("omitidos_paquete_incompleto", 0)
    total_whatsapp_ok += r.get("enviados_whatsapp", 0)
    total_whatsapp_fail += r.get("fallidos_whatsapp", 0)
    detalles["dia_pago"] = r

    # Retrasadas (1 dia de atraso)
    # Sin dias_10_retraso en enviar-todas: PAGO_10_DIAS_ATRASADO solo por enviar-caso-manual (submodulo dedicado).
    items_retrasadas = list(data["dias_1_retraso"])
    asunto_r = "Cuenta con cuota atrasada - Rapicredit"
    cuerpo_r = (
        "Estimado/a {nombre} (c�dula {cedula}),\n\n"
        "Le recordamos que tiene una cuota en mora.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "N�mero de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor regularice su pago lo antes posible.\n\n"
        "Saludos,\nRapicredit"
    )
    r = _enviar_correos_items(items_retrasadas, asunto_r, cuerpo_r, config_envios, _tipo_retrasadas, db)
    total_enviados += r.get("enviados", 0)
    total_fallidos += r.get("fallidos", 0)
    total_sin_email += r.get("sin_email", 0)
    total_omitidos_config += r.get("omitidos_config", 0)
    total_omitidos_paquete += r.get("omitidos_paquete_incompleto", 0)
    total_whatsapp_ok += r.get("enviados_whatsapp", 0)
    total_whatsapp_fail += r.get("fallidos_whatsapp", 0)
    detalles["retrasadas"] = r

    # Prejudicial
    items_prejudicial = data["prejudicial"]
    asunto_pre = "Aviso prejudicial - Rapicredit"
    cuerpo_pre = (
        "Estimado/a {nombre} (c�dula {cedula}),\n\n"
        "Le informamos que su cuenta presenta varias cuotas en mora.\n"
        "Fecha de vencimiento de referencia: {fecha_vencimiento}\n"
        "Cuota de referencia: {numero_cuota}\n"
        "Monto de referencia: {monto}\n\n"
        "Por favor contacte a la entidad para regularizar su situaci�n.\n\n"
        "Saludos,\nRapicredit"
    )
    r = _enviar_correos_items(items_prejudicial, asunto_pre, cuerpo_pre, config_envios, _tipo_prejudicial, db)
    total_enviados += r.get("enviados", 0)
    total_fallidos += r.get("fallidos", 0)
    total_sin_email += r.get("sin_email", 0)
    total_omitidos_config += r.get("omitidos_config", 0)
    total_omitidos_paquete += r.get("omitidos_paquete_incompleto", 0)
    total_whatsapp_ok += r.get("enviados_whatsapp", 0)
    total_whatsapp_fail += r.get("fallidos_whatsapp", 0)
    detalles["prejudicial"] = r

    # Masivos (comunicaciones generales): misma plantilla/CCO que campañas + fila MASIVOS.
    # enviar-todas y "Envios masivos prueba" leian solo config["MASIVOS"] e ignoraban
    # plantilla_id en masivos_campanas; se unifica con _tipo_cfg_masivos_por_campana.
    items_masivos = get_items_masivos(db)
    asunto_mas = "Comunicado oficial - Rapicredit"
    cuerpo_mas = (
        "Estimado/a {nombre} (cedula {cedula}),\n\n"
        "Le compartimos este comunicado oficial de Rapicredit.\n"
        "Revise el contenido completo en este correo.\n\n"
        "Saludos,\nRapicredit"
    )
    campanas_m = get_campanas_masivos_config(config_envios)
    hab_m = [c for c in campanas_m if c.get("habilitado", True) is not False]
    if hab_m:
        camp_m_ref = hab_m[0]
    else:
        camp_m_ref = _normalizar_campana_masiva(
            {
                "id": "enviar-todas-masivos",
                "nombre": "Masivos",
                "habilitado": True,
                "plantilla_id": None,
                "programador": "03:00",
                "cco": [],
                "dias_semana": [],
            },
            0,
        )
    tipo_mas_merge = _tipo_cfg_masivos_por_campana(camp_m_ref, config_envios)
    cfg_masivos_envio = dict(config_envios)
    cfg_masivos_envio["MASIVOS"] = tipo_mas_merge
    r = _enviar_correos_items(
        items_masivos, asunto_mas, cuerpo_mas, cfg_masivos_envio, _tipo_masivos, db
    )
    total_enviados += r.get("enviados", 0)
    total_fallidos += r.get("fallidos", 0)
    total_sin_email += r.get("sin_email", 0)
    total_omitidos_config += r.get("omitidos_config", 0)
    total_omitidos_paquete += r.get("omitidos_paquete_incompleto", 0)
    total_whatsapp_ok += r.get("enviados_whatsapp", 0)
    total_whatsapp_fail += r.get("fallidos_whatsapp", 0)
    detalles["masivos"] = r

    return {
        "enviados": total_enviados,
        "fallidos": total_fallidos,
        "sin_email": total_sin_email,
        "omitidos_config": total_omitidos_config,
        "omitidos_paquete_incompleto": total_omitidos_paquete,
        "enviados_whatsapp": total_whatsapp_ok,
        "fallidos_whatsapp": total_whatsapp_fail,
        "detalles": detalles,
    }
