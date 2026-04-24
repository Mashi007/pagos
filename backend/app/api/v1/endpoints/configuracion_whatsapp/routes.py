"""
Endpoints de configuración WhatsApp para Comunicaciones.
GET/PUT /configuracion/whatsapp/configuracion.
Políticas: no exponer access_token en GET (se devuelve ***), no sobrescribir token
cuando el frontend envía valor enmascarado (*** o vacío). Persiste en BD (tabla configuracion).
"""
import json
import logging
import time
from typing import Any, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.whatsapp_config_holder import sync_from_db as whatsapp_sync_from_db
from app.models.configuracion import Configuracion

from app.api.v1.endpoints.estado_cuenta_publico.autoresponder import (
    build_autoresponder_webhook_post_url,
    build_payload_prueba_autoresponder,
    get_autoresponder_webhook_monitor_snapshot,
    url_portal_estado_cuenta_publico,
)

logger = logging.getLogger(__name__)
router = APIRouter()

CLAVE_WHATSAPP_CONFIG = "whatsapp_config"

# Stub en memoria; se sincroniza con BD
_whatsapp_stub: dict[str, Any] = {}


def _default_config() -> dict[str, Any]:
    """Valores por defecto desde settings."""
    return {
        "api_url": getattr(settings, "WHATSAPP_GRAPH_URL", None) or "https://graph.facebook.com/v18.0",
        "access_token": getattr(settings, "WHATSAPP_ACCESS_TOKEN", None) or "",
        "phone_number_id": getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", None) or "",
        "business_account_id": getattr(settings, "WHATSAPP_BUSINESS_ACCOUNT_ID", None) or "",
        "webhook_verify_token": getattr(settings, "WHATSAPP_VERIFY_TOKEN", None) or "",
        "modo_pruebas": "true",
        "telefono_pruebas": "",
    }


def _load_whatsapp_from_db(db: Session) -> None:
    """Carga configuración WhatsApp desde la tabla configuracion."""
    try:
        row = db.get(Configuracion, CLAVE_WHATSAPP_CONFIG)
        if row and row.valor:
            data = json.loads(row.valor)
            if isinstance(data, dict):
                _whatsapp_stub.clear()
                _whatsapp_stub.update(_default_config())
                for k, v in data.items():
                    if k in _whatsapp_stub and v is not None:
                        _whatsapp_stub[k] = v
    except Exception:
        pass


def _save_whatsapp_to_db(db: Session) -> None:
    """Persiste configuración WhatsApp en la tabla configuracion."""
    try:
        payload = json.dumps(_whatsapp_stub)
        row = db.get(Configuracion, CLAVE_WHATSAPP_CONFIG)
        if row:
            row.valor = payload
        else:
            db.add(Configuracion(clave=CLAVE_WHATSAPP_CONFIG, valor=payload))
        db.commit()
    except Exception:
        db.rollback()
        raise


def _is_token_masked(v: Any) -> bool:
    """No sobrescribir el token real con el valor enmascarado que envía el frontend."""
    if v is None:
        return True
    if not isinstance(v, str):
        return True
    s = (v or "").strip()
    return s == "" or s == "***"


@router.get("/configuracion")
def get_whatsapp_configuracion(db: Session = Depends(get_db)):
    """Configuración WhatsApp. NUNCA expone access_token ni webhook_verify_token en texto plano (se devuelve ***)."""
    _load_whatsapp_from_db(db)
    if not _whatsapp_stub:
        _whatsapp_stub.update(_default_config())
    out = _whatsapp_stub.copy()
    if out.get("access_token"):
        out["access_token"] = "***"
    if out.get("webhook_verify_token"):
        out["webhook_verify_token"] = "***"
    return out


class WhatsAppConfigUpdate(BaseModel):
    api_url: Optional[str] = None
    access_token: Optional[str] = None
    phone_number_id: Optional[str] = None
    business_account_id: Optional[str] = None
    webhook_verify_token: Optional[str] = None
    modo_pruebas: Optional[str] = None
    telefono_pruebas: Optional[str] = None


@router.put("/configuracion")
def put_whatsapp_configuracion(payload: WhatsAppConfigUpdate = Body(...), db: Session = Depends(get_db)):
    """Actualizar configuración WhatsApp. No sobrescribe access_token ni webhook_verify_token si el frontend envía *** o vacío. Persiste en BD."""
    _load_whatsapp_from_db(db)
    if not _whatsapp_stub:
        _whatsapp_stub.update(_default_config())
    data = payload.model_dump(exclude_none=True)
    for k, v in data.items():
        if k not in _whatsapp_stub:
            continue
        if k in ("access_token", "webhook_verify_token") and _is_token_masked(v):
            continue
        _whatsapp_stub[k] = v
    _save_whatsapp_to_db(db)
    whatsapp_sync_from_db()
    logger.info("Configuración WhatsApp actualizada y persistida en BD (campos: %s)", list(data.keys()))
    out = _whatsapp_stub.copy()
    if out.get("access_token"):
        out["access_token"] = "***"
    if out.get("webhook_verify_token"):
        out["webhook_verify_token"] = "***"
    return {"message": "Configuración WhatsApp actualizada", "configuracion": out}


class ProbarWhatsAppRequest(BaseModel):
    telefono_destino: Optional[str] = None
    mensaje: Optional[str] = None


@router.post("/probar")
def post_whatsapp_probar(payload: ProbarWhatsAppRequest = Body(...), db: Session = Depends(get_db)):
    """
    Envía un mensaje de prueba por WhatsApp con la configuración guardada.
    En modo pruebas usa telefono_pruebas si no se envía telefono_destino.
    """
    _load_whatsapp_from_db(db)
    if not _whatsapp_stub:
        _whatsapp_stub.update(_default_config())
    cfg = _whatsapp_stub
    modo_pruebas = (cfg.get("modo_pruebas") or "true").lower() == "true"
    telefono_pruebas = (cfg.get("telefono_pruebas") or "").strip()
    destino = (payload.telefono_destino or "").strip() or (telefono_pruebas if modo_pruebas else "")
    mensaje = (payload.mensaje or "").strip() or "Mensaje de prueba desde RapiCredit."
    if not destino or len(destino) < 10:
        raise HTTPException(
            status_code=400,
            detail="Indica un teléfono de destino o configura Teléfono de Pruebas en modo pruebas.",
        )
    from app.core.whatsapp_send import send_whatsapp_text
    ok, error_meta = send_whatsapp_text(destino, mensaje)
    if ok:
        return {
            "success": True,
            "mensaje": "Mensaje de prueba enviado correctamente.",
            "telefono_destino": destino,
        }
    mensaje_fallo = error_meta or "No se pudo enviar. Revisa Access Token, Phone Number ID y formato internacional."
    return {
        "success": False,
        "mensaje": mensaje_fallo,
        "telefono_destino": destino,
        "error": error_meta,
    }


@router.get("/test-completo")
def get_whatsapp_test_completo(db: Session = Depends(get_db)):
    """
    Test completo de configuración WhatsApp: verifica conexión con Meta API.
    Devuelve tests (conexión) y resumen (total, exitosos, fallidos, advertencias) para el frontend.
    """
    _load_whatsapp_from_db(db)
    if not _whatsapp_stub:
        _whatsapp_stub.update(_default_config())
    cfg = _whatsapp_stub
    api_url = (cfg.get("api_url") or "https://graph.facebook.com/v18.0").rstrip("/")
    token = (cfg.get("access_token") or "").strip()
    phone_number_id = (cfg.get("phone_number_id") or "").strip()
    # Meta espera el ID numérico (ej. 1038026026054793), no el número de teléfono (+58...)
    phone_number_id_digits = "".join(c for c in phone_number_id if c.isdigit()) if phone_number_id else ""

    # Detectar si el usuario puso el número de teléfono en lugar del Phone Number ID de Meta
    _prefijos_telefono = ("58", "57", "593", "52", "54", "51", "56", "598", "595", "55", "59")
    parece_numero_telefono = (
        len(phone_number_id_digits) >= 10
        and len(phone_number_id_digits) <= 14
        and any(phone_number_id_digits == p or phone_number_id_digits.startswith(p) for p in _prefijos_telefono)
    )

    tests: dict[str, Any] = {}
    exitosos = 0
    fallidos = 0
    advertencias = 0

    # Test 1: Conexión con Meta API (GET phone number info)
    conexion_exito = False
    conexion_mensaje = ""
    conexion_error: Optional[str] = None
    conexion_detalles: Optional[dict] = None
    if not token or token == "***":
        conexion_mensaje = "Falta Access Token. Configura el token en Meta Developers y guárdalo aquí."
        conexion_error = "access_token_no_configurado"
    elif not phone_number_id_digits:
        conexion_mensaje = "Falta Phone Number ID. Usa el Identificador del número de teléfono de Meta (número largo, no el +58...)."
        conexion_error = "phone_number_id_no_configurado"
    elif parece_numero_telefono:
        conexion_mensaje = (
            "Has ingresado lo que parece un número de teléfono (+58, +57, etc.). "
            "Meta requiere el Phone Number ID: el ID numérico que ves en Meta Business Suite → WhatsApp → tu número (ej. 953020801227915), "
            "no el número con código de país. Copia el ID desde la configuración de tu número en Meta."
        )
        conexion_error = "phone_number_id_es_numero_telefono"
        fallidos = 1
    else:
        try:
            import httpx
            url = f"{api_url}/{phone_number_id_digits}"
            params = {"fields": "verified_name,display_phone_number"}
            with httpx.Client(timeout=15.0) as client:
                r = client.get(
                    url,
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
            if r.is_success:
                data = r.json() if r.text else {}
                conexion_exito = True
                conexion_mensaje = "Conexión con Meta API correcta."
                conexion_detalles = data
                exitosos += 1
            else:
                try:
                    err = r.json()
                    api_msg = err.get("error", {}).get("message", r.text[:200] if r.text else "")
                except Exception:
                    api_msg = r.text[:200] if r.text else f"HTTP {r.status_code}"
                    code = None
                # Mensaje amigable para el error típico de Meta (ID no existe o permisos)
                if api_msg and ("does not exist" in api_msg or "missing permissions" in api_msg or "does not support" in api_msg):
                    conexion_mensaje = (
                        "Meta rechazó la petición. Posibles causas: (1) El Phone Number ID no es el correcto: "
                        "debe ser el ID numérico que muestra Meta en Business Suite > WhatsApp > Número de teléfono, "
                        "no el número de teléfono con código de país (+58, etc.). (2) El Access Token no tiene permisos "
                        "whatsapp_business_management y/o whatsapp_business_messaging. (3) El número no está asociado "
                        "a tu app en Meta Developers. Revisa en developers.facebook.com."
                    )
                    conexion_error = api_msg
                else:
                    conexion_mensaje = api_msg
                    conexion_error = api_msg
                fallidos += 1
        except Exception as e:
            conexion_mensaje = str(e)[:200]
            conexion_error = str(e)[:200]
            fallidos += 1

    tests["conexion"] = {
        "nombre": "Conexión Meta API",
        "exito": conexion_exito,
        "mensaje": conexion_mensaje,
        "detalles": conexion_detalles,
        "error": conexion_error,
    }

    total = exitosos + fallidos
    if total == 0:
        advertencias = 1
    resumen = {
        "total": max(total, 1),
        "exitosos": exitosos,
        "fallidos": fallidos,
        "advertencias": advertencias,
    }
    return {
        "tests": tests,
        "resumen": resumen,
    }


AUTORESPONDER_DOC_URL = (
    "https://www.autoresponder.ai/post/connect-your-messengers-to-a-web-server-api-using-autoresponder"
)


class HeaderPar(BaseModel):
    clave: str
    valor: str


class CedulaConsultaMonitorItem(BaseModel):
    """Cédula enmascarada recibida en query.message (máx. 5 en cola por worker)."""

    recibida_en_utc: str
    cedula_mostrada: str


class AutoresponderMonitorStats(BaseModel):
    """Contadores del webhook (memoria por proceso worker)."""

    peticiones_total: int = 0
    pruebas_recibidas_ok: int = 0
    solicitudes_codigo_exitosas: int = 0
    solicitudes_codigo_respuesta_error: int = 0
    fallos_autenticacion: int = 0
    cuerpo_json_invalido: int = 0
    json_incompleto_validacion: int = 0
    sin_configuracion_servidor: int = 0
    excepciones_solicitar_codigo: int = 0
    ultima_peticion_utc: Optional[str] = None
    ultimo_exito_utc: Optional[str] = None
    ultimo_error_resumen: Optional[str] = None
    nota_contadores: str = ""
    cedulas_consulta_recientes: List[CedulaConsultaMonitorItem] = Field(default_factory=list)


class AutoresponderEstadoCuentaInstruccionesResponse(BaseModel):
    """Valores para copiar en AutoResponder > Conectar con tu servidor web (sin exponer la contraseña)."""

    post_url: str
    # Portal SPA: PDF tras cédula + código. Vacío si falta FRONTEND_PUBLIC_URL.
    portal_pdf_url: Optional[str] = None
    basic_auth_usuario: Optional[str] = None
    basic_auth_configurado: bool = False
    headers_recomendados: List[HeaderPar]
    variables_entorno_render: dict[str, str]
    documentacion_url: str
    alcance: str
    sugerencia_regla: str
    monitor: AutoresponderMonitorStats


class ProbarAutoresponderConexionResponse(BaseModel):
    ok: bool
    mensaje: str
    status_code: Optional[int] = None
    latencia_ms: Optional[int] = None
    respuesta_replies: Optional[List[Any]] = None


@router.get("/autoresponder-estado-cuenta", response_model=AutoresponderEstadoCuentaInstruccionesResponse)
def get_autoresponder_estado_cuenta_instrucciones(request: Request):
    """
    Instrucciones y URL del webhook AutoResponder → estado de cuenta (código por correo).
    Requiere sesión de personal. La contraseña del webhook solo vive en variables de entorno.
    """
    post_url = build_autoresponder_webhook_post_url()
    if not post_url:
        post_url = str(request.base_url).rstrip("/") + (
            f"{settings.API_V1_STR}/estado-cuenta/public/webhook-autoresponder"
        )

    u = (getattr(settings, "AUTORESPONDER_WEBHOOK_USER", None) or "").strip() or None
    p_set = bool((getattr(settings, "AUTORESPONDER_WEBHOOK_PASSWORD", None) or "").strip())
    basic_ok = bool(u and p_set)

    headers_recomendados = [
        HeaderPar(clave="Content-Type", valor="application/json"),
    ]

    variables_entorno_render = {
        "AUTORESPONDER_WEBHOOK_USER": "Mismo valor que «Usuario» en Basic Auth de AutoResponder",
        "AUTORESPONDER_WEBHOOK_PASSWORD": "Mismo valor que «Contraseña» (solo en Render; no compartir por chat)",
    }

    alcance = (
        "Al recibir en query.message la cédula, el servidor ejecuta la misma lógica que "
        "«solicitar código» del portal: si aplica, envía un código al correo registrado. "
        "El estado de cuenta en PDF no se embebe en la respuesta JSON de AutoResponder "
        "(solo se pueden enviar mensajes de texto en replies). "
        "El PDF se genera y descarga en el portal público rapicredit-estadocuenta "
        "tras ingresar cédula y código; las respuestas del webhook incluyen el enlace cuando "
        "FRONTEND_PUBLIC_URL está configurada."
    )

    sugerencia_regla = (
        "En AutoResponder, active «Conectar con tu servidor web», pegue la URL, "
        "configure Basic Auth con el mismo usuario y contraseña que definió en Render, "
        "y una regla que envíe al servidor los mensajes donde el usuario escribe solo la cédula "
        "(o el patrón que use su operación)."
    )

    snap = get_autoresponder_webhook_monitor_snapshot()
    monitor = AutoresponderMonitorStats.model_validate(snap)
    portal_pdf = url_portal_estado_cuenta_publico()

    return AutoresponderEstadoCuentaInstruccionesResponse(
        post_url=post_url,
        portal_pdf_url=portal_pdf or None,
        basic_auth_usuario=u,
        basic_auth_configurado=basic_ok,
        headers_recomendados=headers_recomendados,
        variables_entorno_render=variables_entorno_render,
        documentacion_url=AUTORESPONDER_DOC_URL,
        alcance=alcance,
        sugerencia_regla=sugerencia_regla,
        monitor=monitor,
    )


@router.post(
    "/autoresponder-estado-cuenta/probar-conexion",
    response_model=ProbarAutoresponderConexionResponse,
)
def post_autoresponder_probar_conexion():
    """
    POST de prueba al webhook público (JSON con isTestMessage) usando Basic Auth desde settings.
    Verifica conectividad HTTP + credenciales + formato de respuesta replies.
    """
    post_url = build_autoresponder_webhook_post_url()
    if not post_url:
        raise HTTPException(
            status_code=400,
            detail="Defina BACKEND_PUBLIC_URL (URL pública del API) para armar la URL del webhook y probar.",
        )
    u = (getattr(settings, "AUTORESPONDER_WEBHOOK_USER", None) or "").strip()
    p = (getattr(settings, "AUTORESPONDER_WEBHOOK_PASSWORD", None) or "").strip()
    if not u or not p:
        raise HTTPException(
            status_code=400,
            detail="Configure AUTORESPONDER_WEBHOOK_USER y AUTORESPONDER_WEBHOOK_PASSWORD en el entorno del backend.",
        )

    try:
        import httpx

        t0 = time.perf_counter()
        with httpx.Client(timeout=25.0) as client:
            r = client.post(
                post_url,
                json=build_payload_prueba_autoresponder(),
                auth=(u, p),
                headers={"Content-Type": "application/json"},
            )
        latencia_ms = int((time.perf_counter() - t0) * 1000)
        body: Any = None
        try:
            body = r.json() if r.text else None
        except Exception:
            body = None
        replies = body.get("replies") if isinstance(body, dict) else None
        ok = (
            r.status_code == 200
            and isinstance(replies, list)
            and len(replies) > 0
            and isinstance(replies[0], dict)
            and "message" in replies[0]
        )
        if ok:
            return ProbarAutoresponderConexionResponse(
                ok=True,
                mensaje="Conexión correcta: el webhook respondió 200 con replies (mensaje de prueba).",
                status_code=r.status_code,
                latencia_ms=latencia_ms,
                respuesta_replies=replies,
            )
        return ProbarAutoresponderConexionResponse(
            ok=False,
            mensaje=f"Respuesta inesperada (HTTP {r.status_code}). Revise URL y credenciales.",
            status_code=r.status_code,
            latencia_ms=latencia_ms,
            respuesta_replies=replies if isinstance(replies, list) else None,
        )
    except Exception as e:
        logger.warning("autoresponder probar-conexion: %s", e)
        return ProbarAutoresponderConexionResponse(
            ok=False,
            mensaje=f"No se pudo contactar el webhook: {str(e)[:300]}",
        )
