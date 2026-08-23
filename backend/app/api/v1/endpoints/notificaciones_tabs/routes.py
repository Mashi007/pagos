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
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from fastapi import APIRouter, Depends, HTTPException, HTTPException, Query
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
    cliente_ids_bloqueados_para_notificacion,
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
    _flags_adjuntos_envio,
    _parse_plantilla_id_desde_config,
    _tipo_dos_dias_antes_solo_correo,
    _tipo_menor_60_solo_pdf_fijo,
    _tipo_prejudicial_solo_html,
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
router_cobranzas = APIRouter(dependencies=[Depends(require_admin)])
router_cuotas_4_mas = APIRouter(dependencies=[Depends(require_admin)])
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
    # Solo 1 dia de atraso en este lote agregado. PAGO_10_DIAS_ATRASADO (menor a 60)
    # es exclusivamente manual via enviar-caso-manual; no mapear por dias_atraso aqui.
    return "PAGO_1_DIA_ATRASADO"


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


# --- Notificaciones prejudiciales (2 Cuotas: >=2 atrasadas, atraso >=1) ---

@router_prejudicial.get("")
def get_notificaciones_prejudicial(
    estado: str = None,
    fecha_caracas: Optional[str] = _FC_Q,
    db: Session = Depends(get_db),
):
    """Lista PREJUDICIAL: >=2 cuotas atrasadas (atraso >=1). Puede solapar con dia siguiente."""
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
    """Envio MANUAL PREJUDICIAL (2 Cuotas). Sin cron ni enviar-todas; solo este POST o enviar-caso-manual."""
    fecha_ref = _fecha_referencia_desde_query(fecha_caracas)
    from app.services.notificacion_plantilla_prejudicial import (
        ASUNTO_PREJUDICIAL_FALLBACK,
        CUERPO_PREJUDICIAL_FALLBACK,
        asegurar_modulo_prejudicial,
    )
    try:
        asegurar_modulo_prejudicial(db, forzar_contenido_plantilla=False)
        db.commit()
    except Exception:
        db.rollback()
    config_envios = get_notificaciones_envios_config(db)
    items = build_prejudicial_items(db, fecha_referencia=fecha_ref)
    # Defensa: no enviar nada fuera de regla aunque venga de caché/UI.
    from app.services.notificacion_service import item_cumple_regla_prejudicial_estricta as _ok_prej
    items = [it for it in items if _ok_prej(it, fecha_ref)]
    asunto = ASUNTO_PREJUDICIAL_FALLBACK
    cuerpo = CUERPO_PREJUDICIAL_FALLBACK
    res = _enviar_correos_items(
        items,
        asunto,
        cuerpo,
        config_envios,
        _tipo_prejudicial,
        db,
        fecha_referencia=fecha_ref,
    )
    return {"mensaje": "Envio de notificaciones prejudiciales finalizado.", **res}


# --- Notificaciones Cobranzas Excel (universo + >=2 atrasadas; independiente de PREJUDICIAL) ---

@router_cobranzas.get("")
def get_notificaciones_cobranzas(
    estado: str = None,
    fecha_caracas: Optional[str] = _FC_Q,
    db: Session = Depends(get_db),
):
    """Lista COBRANZAS_EXCEL: cartera con >=2 cuotas vencidas (atraso >=1 dia); sin Excel."""
    from app.services.notificaciones_cobranzas_excel import build_cobranzas_excel_items

    fecha_ref = _fecha_referencia_desde_query(fecha_caracas)
    items = build_cobranzas_excel_items(db, fecha_referencia=fecha_ref)
    return {"items": items, "total": len(items)}


def _tipo_cobranzas_excel(_item: dict) -> str:
    return "COBRANZAS_EXCEL"


@router_cobranzas.post("/enviar")
def enviar_notificaciones_cobranzas(
    fecha_caracas: Optional[str] = _FC_Q,
    db: Session = Depends(get_db),
):
    """Modulo retirado: usar PREJUDICIAL / a-2-cuotas."""
    raise HTTPException(
        status_code=410,
        detail="COBRANZAS_EXCEL retirado; use PREJUDICIAL / a-2-cuotas.",
    )


# --- Notificaciones 4 cuotas y mas (universo + >=4 atrasadas; independiente) ---

@router_cuotas_4_mas.get("")
def get_notificaciones_cuotas_4_mas(
    estado: str = None,
    fecha_caracas: Optional[str] = _FC_Q,
    db: Session = Depends(get_db),
):
    """Lista CUOTAS_4_MAS: cedulas universo Excel con >=4 cuotas vencidas (atraso >=1 dia)."""
    from app.services.notificaciones_cuotas_4_mas import build_cuotas_4_mas_items

    fecha_ref = _fecha_referencia_desde_query(fecha_caracas)
    items = build_cuotas_4_mas_items(db, fecha_referencia=fecha_ref)
    return {"items": items, "total": len(items)}


def _tipo_cuotas_4_mas(_item: dict) -> str:
    return "CUOTAS_4_MAS"


@router_cuotas_4_mas.post("/enviar")
def enviar_notificaciones_cuotas_4_mas(
    fecha_caracas: Optional[str] = _FC_Q,
    db: Session = Depends(get_db),
):
    """Modulo retirado: usar PREJUDICIAL / a-2-cuotas."""
    raise HTTPException(
        status_code=410,
        detail="CUOTAS_4_MAS retirado; use PREJUDICIAL / a-2-cuotas.",
    )


def get_items_masivos(db: Session) -> List[dict]:
    """
    Contactos para comunicaciones masivas.

    Fuente principal: vista vw_notificaciones_masivos_contactos (sincronizada en 2 vias).
    Fallback de compatibilidad: tabla clientes si la vista aun no existe.
    Excluye clientes con DESISTIMIENTO o sin cartera activa (solo LIQUIDADO).
    """
    items: List[dict] = []

    try:
        rows = db.execute(
            text(
                """
                SELECT id, cliente_id, cedula, nombre, email, telefono, updated_at
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
            # La vista puede no exponer email_secundario; no fallar por eso.
            _, correo_sec = secundario_distinto_del_principal(
                em, str(r.get("email_secundario") or "").strip() or None
            )
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
        bloq = cliente_ids_bloqueados_para_notificacion(
            db,
            {it.get("cliente_id") for it in items if it.get("cliente_id") is not None},
        )
        return [it for it in items if it.get("cliente_id") not in bloq]
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
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
    bloq = cliente_ids_bloqueados_para_notificacion(
        db,
        {it.get("cliente_id") for it in items if it.get("cliente_id") is not None},
    )
    return [it for it in items if it.get("cliente_id") not in bloq]


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
        "COBRANZAS_EXCEL",
        "CUOTAS_4_MAS",
        "MASIVOS",
    }
)

# Politica producto: cobranza por segmento SOLO manual (POST /enviar-caso-manual
# o POST dedicado de la pestana). Nunca cron ni POST /enviar-todas.
TIPOS_NOTIFICACION_SOLO_ENVIO_MANUAL = frozenset(
    {
        "PAGO_2_DIAS_ANTES_PENDIENTE",
        "PAGO_1_DIA_ATRASADO",
        "PAGO_10_DIAS_ATRASADO",
        "PREJUDICIAL",
        "COBRANZAS_EXCEL",
        "CUOTAS_4_MAS",
    }
)


def tipo_permite_envio_automatico_o_lote(tipo: str) -> bool:
    """False si el tipo solo admite disparo manual (sin cron ni enviar-todas)."""
    return (tipo or "").strip() not in TIPOS_NOTIFICACION_SOLO_ENVIO_MANUAL


def _config_envios_forzar_habilitado_casos(config_envios: dict, tipos: Sequence[str]) -> dict:
    """Copia superficial con habilitado=True para cada tipo indicado."""
    out = dict(config_envios) if isinstance(config_envios, dict) else {}
    for tipo in tipos:
        t = (tipo or "").strip()
        if not t:
            continue
        cur = out.get(t)
        merged = dict(cur) if isinstance(cur, dict) else {}
        merged["habilitado"] = True
        out[t] = merged
    return out


def _config_envios_forzar_habilitado_caso(config_envios: dict, tipo: str) -> dict:
    """
    Copia superficial de la config de envios con habilitado=True solo para el tipo indicado.
    El envio manual y la prueba de paquete deben ejecutarse aunque el toggle Envio este apagado.
    """
    return _config_envios_forzar_habilitado_casos(config_envios, (tipo,))


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


_RES_ENVIO_KEYS = (
    "enviados",
    "sin_email",
    "fallidos",
    "omitidos_config",
    "omitidos_desistimiento",
    "omitidos_paquete_incompleto",
    "omitidos_ya_enviado",
    "enviados_whatsapp",
    "fallidos_whatsapp",
    "procesados",
)


def _res_envio_vacio() -> dict:
    return {k: 0 for k in _RES_ENVIO_KEYS} | {
        "pausado_limite_gmail": False,
        "cancelado_usuario": False,
        "motivo_pausa": None,
    }


def _acumular_res_envio(acc: dict, nxt: dict) -> dict:
    out = dict(acc)
    for k in _RES_ENVIO_KEYS:
        out[k] = int(out.get(k) or 0) + int(nxt.get(k) or 0)
    if nxt.get("pausado_limite_gmail"):
        out["pausado_limite_gmail"] = True
        if nxt.get("motivo_pausa"):
            out["motivo_pausa"] = nxt.get("motivo_pausa")
    if nxt.get("cancelado_usuario"):
        out["cancelado_usuario"] = True
        if nxt.get("motivo_pausa"):
            out["motivo_pausa"] = nxt.get("motivo_pausa")
    return out


def _progress_con_offset(on_progress, offset: int, total: int, prev: dict):
    if not on_progress:
        return None

    def _inner(p: dict) -> None:
        try:
            on_progress(
                {
                    "procesados": offset + int(p.get("procesados") or 0),
                    "total_en_lista": total,
                    "enviados": int(prev.get("enviados") or 0) + int(p.get("enviados") or 0),
                    "fallidos": int(prev.get("fallidos") or 0) + int(p.get("fallidos") or 0),
                    "sin_email": int(prev.get("sin_email") or 0) + int(p.get("sin_email") or 0),
                    "omitidos_config": int(prev.get("omitidos_config") or 0)
                    + int(p.get("omitidos_config") or 0),
                    "omitidos_paquete_incompleto": int(
                        prev.get("omitidos_paquete_incompleto") or 0
                    )
                    + int(p.get("omitidos_paquete_incompleto") or 0),
                    "omitidos_desistimiento": int(prev.get("omitidos_desistimiento") or 0)
                    + int(p.get("omitidos_desistimiento") or 0),
                    "omitidos_ya_enviado": int(prev.get("omitidos_ya_enviado") or 0)
                    + int(p.get("omitidos_ya_enviado") or 0),
                }
            )
        except Exception:
            logger.debug("[notif] on_progress offset fallo", exc_info=True)

    return _inner


def _enviar_dia_siguiente_y_otras_reglas(
    db: Session,
    *,
    items_dia_siguiente: List[dict],
    items_10_retraso: List[dict],
    fecha_referencia: Optional[date],
    config_raw: dict,
    respetar_toggle_envio: bool,
    on_progress,
    omitir_exitos_desde: Optional[date],
    asunto_ret: str,
    cuerpo_ret: str,
    asunto_prej: str,
    cuerpo_prej: str,
) -> dict:
    """
    Envia dia siguiente y, a los mismos titulares, 2 Cuotas / 1 Cuota / 3 dias antes
    si esas reglas aplican. Cuentas SMTP distintas pueden seguir si una se pausa.
    """
    from app.services.notificacion_service import (
        build_cuotas_pendiente_2_dias_antes_items,
        item_cumple_regla_menor_60_estricta,
        item_cumple_regla_prejudicial_estricta,
    )
    from app.services.notificaciones_dedup_segmentos import (
        filtrar_items_de_titulares,
        filtrar_items_menor_60_sin_prejudicial,
        titulares_desde_items,
    )

    items_d1 = list(items_dia_siguiente or [])
    cids, ceds = titulares_desde_items(items_d1)

    prej_all = build_prejudicial_items(db, fecha_referencia=fecha_referencia)
    items_prej = [
        it
        for it in filtrar_items_de_titulares(prej_all, cids, ceds)
        if item_cumple_regla_prejudicial_estricta(it, fecha_referencia)
    ]

    items_m60 = [
        it
        for it in (items_10_retraso or [])
        if item_cumple_regla_menor_60_estricta(it, fecha_referencia)
    ]
    items_m60 = filtrar_items_de_titulares(items_m60, cids, ceds)
    items_m60 = filtrar_items_menor_60_sin_prejudicial(db, items_m60, fecha_referencia)

    items_3d = filtrar_items_de_titulares(
        build_cuotas_pendiente_2_dias_antes_items(db, fecha_referencia=fecha_referencia),
        cids,
        ceds,
    )

    lotes: List[Tuple[str, List[dict], str, str]] = [
        ("PAGO_1_DIA_ATRASADO", items_d1, asunto_ret, cuerpo_ret),
        ("PREJUDICIAL", items_prej, asunto_prej, cuerpo_prej),
        ("PAGO_10_DIAS_ATRASADO", items_m60, asunto_ret, cuerpo_ret),
        (
            "PAGO_2_DIAS_ANTES_PENDIENTE",
            items_3d,
            ASUNTO_DEFAULT_PAGO_2_DIAS_ANTES_PENDIENTE,
            CUERPO_DEFAULT_PAGO_2_DIAS_ANTES_PENDIENTE,
        ),
    ]
    total = sum(len(its) for _t, its, _a, _c in lotes)
    acc = _res_envio_vacio()
    offset = 0
    if on_progress:
        try:
            on_progress(
                {
                    "procesados": 0,
                    "total_en_lista": total,
                    "enviados": 0,
                    "fallidos": 0,
                    "sin_email": 0,
                }
            )
        except Exception:
            pass

    for tipo_lote, its, asunto, cuerpo in lotes:
        if not its:
            continue
        if respetar_toggle_envio:
            cfg = dict(config_raw) if isinstance(config_raw, dict) else {}
        else:
            cfg = _config_envios_forzar_habilitado_caso(config_raw, tipo_lote)
        nxt = _enviar_correos_items(
            its,
            asunto,
            cuerpo,
            cfg,
            _resolver_tipo_envio_manual_fijo(tipo_lote),
            db,
            fecha_referencia=fecha_referencia,
            on_progress=_progress_con_offset(on_progress, offset, total, acc),
            omitir_exitos_desde=omitir_exitos_desde,
        )
        acc = _acumular_res_envio(acc, nxt)
        offset += len(its)
        if acc.get("cancelado_usuario"):
            break
        # Si se pauso Gmail en este buzon, los lotes de otra cuenta SMTP siguen.

    acc["detalles_casos_adicionales"] = {
        "dia_siguiente": len(items_d1),
        "prejudicial": len(items_prej),
        "una_cuota": len(items_m60),
        "tres_dias_antes": len(items_3d),
    }
    acc["total_en_lista"] = total
    return acc


def ejecutar_envio_caso_manual(
    db: Session,
    tipo: str,
    fecha_referencia: Optional[date] = None,
    *,
    respetar_toggle_envio: bool = False,
    on_progress=None,
    omitir_exitos_desde: Optional[date] = None,
) -> dict:
    """
    Envio sincrono de un criterio (una fila de configuracion: PAGO_1_DIA_ANTES, etc.).
    Excepcion PAGO_1_DIA_ATRASADO: ademas envia 2 Cuotas, 1 Cuota y 3 dias antes
    a los mismos titulares si esas reglas tambien aplican.

    Lista de destinatarios = la misma regla que la pestaña correspondiente; cada correo usa
    la config de ese tipo (plantilla/CCO/PDF del caso), sin inferir otro tipo por fila.

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
    from app.services.notificacion_plantilla_prejudicial import (
        ASUNTO_PREJUDICIAL_FALLBACK as asunto_prej,
        CUERPO_PREJUDICIAL_FALLBACK as cuerpo_prej,
    )
    asunto_mas = "Comunicado oficial - Rapicredit"
    cuerpo_mas = (
        "Estimado/a {nombre} (cedula {cedula}),\n\n"
        "Le compartimos este comunicado oficial de Rapicredit.\n"
        "Revise el contenido completo en este correo.\n\n"
        "Saludos,\nRapicredit"
    )

    ref = fecha_referencia
    if tipo == "PREJUDICIAL":
        items = build_prejudicial_items(db, fecha_referencia=ref)
        from app.services.notificacion_service import (
            item_cumple_regla_prejudicial_estricta as _ok_prej,
        )
        items = [it for it in items if _ok_prej(it, ref)]
        from app.services.notificaciones_dedup_segmentos import (
            filtrar_items_sin_cobranzas_excel as _sin_cobex,
            filtrar_items_sin_cuotas_4_mas as _sin_c4,
        )
        res = _enviar_correos_items(
            items,
            asunto_prej,
            cuerpo_prej,
            config_envios,
            _resolver_tipo_envio_manual_fijo("PREJUDICIAL"),
            db,
            fecha_referencia=ref,
            on_progress=on_progress,
            omitir_exitos_desde=omitir_exitos_desde,
        )
    elif tipo == "COBRANZAS_EXCEL":
        from app.services.notificacion_plantilla_cobranzas import (
            ASUNTO_COBRANZAS_EXCEL_FALLBACK as asunto_cobex,
            CUERPO_COBRANZAS_EXCEL_FALLBACK as cuerpo_cobex,
            asegurar_modulo_cobranzas_excel,
        )
        from app.services.notificaciones_cobranzas_excel import (
            build_cobranzas_excel_items,
            item_cumple_regla_cobranzas_excel as _ok_cobex,
        )
        try:
            asegurar_modulo_cobranzas_excel(db, forzar_contenido_plantilla=False)
            db.commit()
        except Exception:
            db.rollback()
        items = build_cobranzas_excel_items(db, fecha_referencia=ref)
        items = [it for it in items if _ok_cobex(it, ref)]
        if on_progress:
            try:
                on_progress(
                    {
                        "procesados": 0,
                        "total_en_lista": len(items),
                        "enviados": 0,
                        "fallidos": 0,
                        "sin_email": 0,
                    }
                )
            except Exception:
                pass
        res = _enviar_correos_items(
            items,
            asunto_cobex,
            cuerpo_cobex,
            config_envios,
            _resolver_tipo_envio_manual_fijo("COBRANZAS_EXCEL"),
            db,
            fecha_referencia=ref,
            on_progress=on_progress,
            omitir_exitos_desde=omitir_exitos_desde,
        )
    elif tipo == "CUOTAS_4_MAS":
        from app.services.notificacion_plantilla_cuotas_4_mas import (
            ASUNTO_CUOTAS_4_MAS_FALLBACK as asunto_c4,
            CUERPO_CUOTAS_4_MAS_FALLBACK as cuerpo_c4,
            asegurar_modulo_cuotas_4_mas,
        )
        from app.services.notificaciones_cuotas_4_mas import (
            build_cuotas_4_mas_items,
            item_cumple_regla_cuotas_4_mas as _ok_c4,
        )
        try:
            asegurar_modulo_cuotas_4_mas(db, forzar_contenido_plantilla=False)
            db.commit()
        except Exception:
            db.rollback()
        items = build_cuotas_4_mas_items(db, fecha_referencia=ref)
        items = [it for it in items if _ok_c4(it, ref)]
        if on_progress:
            try:
                on_progress(
                    {
                        "procesados": 0,
                        "total_en_lista": len(items),
                        "enviados": 0,
                        "fallidos": 0,
                        "sin_email": 0,
                    }
                )
            except Exception:
                pass
        res = _enviar_correos_items(
            items,
            asunto_c4,
            cuerpo_c4,
            config_envios,
            _resolver_tipo_envio_manual_fijo("CUOTAS_4_MAS"),
            db,
            fecha_referencia=ref,
            on_progress=on_progress,
            omitir_exitos_desde=omitir_exitos_desde,
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
                on_progress=on_progress,
            omitir_exitos_desde=omitir_exitos_desde,
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
                on_progress=on_progress,
            omitir_exitos_desde=omitir_exitos_desde,
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
                on_progress=on_progress,
            omitir_exitos_desde=omitir_exitos_desde,
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
                on_progress=on_progress,
            omitir_exitos_desde=omitir_exitos_desde,
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
                on_progress=on_progress,
            omitir_exitos_desde=omitir_exitos_desde,
            )
        elif tipo == "PAGO_1_DIA_ATRASADO":
            items = list(data["dias_1_retraso"])
            res = _enviar_dia_siguiente_y_otras_reglas(
                db,
                items_dia_siguiente=items,
                items_10_retraso=list(data.get("dias_10_retraso") or []),
                fecha_referencia=ref,
                config_raw=config_raw,
                respetar_toggle_envio=respetar_toggle_envio,
                on_progress=on_progress,
                omitir_exitos_desde=omitir_exitos_desde,
                asunto_ret=asunto_ret,
                cuerpo_ret=cuerpo_ret,
                asunto_prej=asunto_prej,
                cuerpo_prej=cuerpo_prej,
            )
        elif tipo == "PAGO_10_DIAS_ATRASADO":
            items = data["dias_10_retraso"]
            from app.services.notificacion_service import (
                item_cumple_regla_menor_60_estricta as _ok_m60,
            )
            items = [it for it in items if _ok_m60(it, ref)]
            from app.services.notificaciones_dedup_segmentos import (
                filtrar_items_menor_60_sin_prejudicial as _sin_prej,
            )

            # «2 Cuotas» recorta «1 Cuota»; dia siguiente ya no recorta.
            items = _sin_prej(db, items, ref)
            res = _enviar_correos_items(
                items,
                asunto_ret,
                cuerpo_ret,
                config_envios,
                _resolver_tipo_envio_manual_fijo("PAGO_10_DIAS_ATRASADO"),
                db,
                fecha_referencia=ref,
                on_progress=on_progress,
            omitir_exitos_desde=omitir_exitos_desde,
            )
        else:
            raise ValueError("tipo_caso_manual_invalido")

    pausado = bool(res.get("pausado_limite_gmail"))
    mensaje = (
        f"Envio manual del caso {tipo} pausado por limite diario Gmail. "
        f"Quedaron pendientes; se reanuda al siguiente dia de negocio "
        f"(los ya enviados con exito hoy se omiten)."
        if pausado
        else f"Envio manual del caso {tipo} finalizado."
    )
    return {
        "mensaje": mensaje,
        "tipo_caso": tipo,
        **res,
        # Dia siguiente acumula 2 Cuotas / 1 Cuota / 3d en res.total_en_lista.
        "total_en_lista": int(res.get("total_en_lista") or len(items)),
    }


def ejecutar_envio_todas_notificaciones(db: Session) -> dict:
    """
    Ejecuta en un solo batch varias familias de notificacion: previas, dia de pago, retrasadas
    (1 dia) y masivos. Sin PREJUDICIAL, COBRANZAS_EXCEL ni PAGO_10_DIAS_ATRASADO (solo manual). Cada tipo usa su propia configuracion en notificaciones_envios (habilitado,
    CCO, modo pruebas, etc.); no se mezclan entre si.

    No incluye PAGO_2_DIAS_ANTES_PENDIENTE (2 dias antes del vencimiento), que tiene envio propio.
    No incluye tipos en TIPOS_NOTIFICACION_SOLO_ENVIO_MANUAL (3 dias antes, dia siguiente, 1 Cuota, 2 Cuotas): solo POST /enviar-caso-manual
    (o POST notificaciones-prejudicial/enviar) desde el submodulo dedicado.
    Sin cron ni programador de servidor para esos tipos.

    Solo desde POST /notificaciones/enviar-todas (BackgroundTasks); sin envio automatico por hora.
    """
    # Defensa: TIPOS_NOTIFICACION_SOLO_ENVIO_MANUAL (PAGO_10_DIAS_ATRASADO, PREJUDICIAL,
    # COBRANZAS_EXCEL, etc.) no se incluyen abajo; el lote usa dias_1_retraso + previas/hoy/masivos.

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

    # Retrasadas (1 dia): PAGO_1_DIA_ATRASADO esta en TIPOS_NOTIFICACION_SOLO_ENVIO_MANUAL.
    # No se envia en este lote; solo POST /enviar-caso-manual (o pestana retrasadas dedicada).
    detalles["retrasadas"] = {
        "enviados": 0,
        "fallidos": 0,
        "sin_email": 0,
        "omitidos_config": 0,
        "omitidos_paquete_incompleto": 0,
        "omitido_solo_manual": True,
        "motivo": "PAGO_1_DIA_ATRASADO solo envio manual",
    }

    # Sin prejudicial en enviar-todas: PREJUDICIAL (2 Cuotas) solo por
    # enviar-caso-manual / POST notificaciones-prejudicial/enviar (submodulo dedicado).
    # Esta en TIPOS_NOTIFICACION_SOLO_ENVIO_MANUAL: sin cron ni lote automatico.

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
