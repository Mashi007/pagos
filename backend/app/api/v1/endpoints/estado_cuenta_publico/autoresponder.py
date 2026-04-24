"""
Webhook HTTP para la app AutoResponder (Android) → solicitud de código de estado de cuenta por cédula.

Contrato: POST JSON como documenta https://www.autoresponder.ai/post/connect-your-messengers-to-a-web-server-api-using-autoresponder
Respuesta: {"replies": [{"message": "..."}]}

Seguridad: si AUTORESPONDER_WEBHOOK_USER y AUTORESPONDER_WEBHOOK_PASSWORD están definidos en el entorno,
el endpoint exige Authorization: Basic ...; si faltan, responde 503 (no se expone lógica sin credenciales).

Monitor: contadores en memoria por proceso worker (Gunicorn/uvicorn); ver ``get_autoresponder_webhook_monitor_snapshot``.
"""
from __future__ import annotations

import base64
import logging
import secrets
import threading
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.config import settings, get_effective_api_public_base_url
from app.core.database import get_db

from app.api.v1.endpoints.estado_cuenta_publico.routes import (
    SolicitarCodigoRequest,
    solicitar_codigo_estado_cuenta,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["estado-cuenta-autoresponder"])


@dataclass
class _AutoresponderWebhookStats:
    """Contadores por proceso (no compartidos entre workers)."""

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


_stats_lock = threading.Lock()
_stats = _AutoresponderWebhookStats()

# Últimas consultas con cédula recibida en el JSON (solo flujo real, no isTestMessage). Máx. 5 por worker.
_MAX_CEDULAS_MONITOR = 5
_cedulas_recientes: Deque[Dict[str, str]] = deque(maxlen=_MAX_CEDULAS_MONITOR)


def _mask_cedula_para_monitor(texto: str) -> str:
    """
    Muestra solo prefijo nacional (V/E) y últimos 4 dígitos para verificar que llegó dato desde la API
    sin persistir la cédula completa en el monitor.
    """
    s = (texto or "").strip().upper()
    if not s:
        return "(vacío)"
    letters = "".join(ch for ch in s if ch.isalpha())[:1]
    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) < 4:
        return "***" if digits else "(sin dígitos)"
    suf = digits[-4:]
    if letters in ("V", "E", "J", "G"):
        return f"{letters}-***{suf}"
    return f"***{suf}"


def _registrar_cedula_recibida_api(texto_cedula: str) -> None:
    """FIFO de hasta 5 entradas; llamar solo en consultas reales (post auth, no prueba)."""
    item = {
        "recibida_en_utc": _now_iso(),
        "cedula_mostrada": _mask_cedula_para_monitor(texto_cedula),
    }
    with _stats_lock:
        _cedulas_recientes.append(item)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _record(
    *,
    categoria: str,
    exito: bool = False,
    error_resumen: Optional[str] = None,
) -> None:
    with _stats_lock:
        _stats.peticiones_total += 1
        _stats.ultima_peticion_utc = _now_iso()
        if exito:
            _stats.ultimo_exito_utc = _stats.ultima_peticion_utc
            _stats.ultimo_error_resumen = None
        elif error_resumen:
            _stats.ultimo_error_resumen = (error_resumen or "")[:500]
        if categoria == "sin_config":
            _stats.sin_configuracion_servidor += 1
        elif categoria == "auth_fail":
            _stats.fallos_autenticacion += 1
        elif categoria == "json_invalido":
            _stats.cuerpo_json_invalido += 1
        elif categoria == "json_incompleto":
            _stats.json_incompleto_validacion += 1
        elif categoria == "prueba_ok":
            _stats.pruebas_recibidas_ok += 1
        elif categoria == "solicitar_ok":
            _stats.solicitudes_codigo_exitosas += 1
        elif categoria == "solicitar_error_respuesta":
            _stats.solicitudes_codigo_respuesta_error += 1
        elif categoria == "solicitar_excepcion":
            _stats.excepciones_solicitar_codigo += 1


def get_autoresponder_webhook_monitor_snapshot() -> Dict[str, Any]:
    """Copia segura de contadores para GET configuración (un proceso por respuesta)."""
    with _stats_lock:
        d = asdict(_stats)
        cedulas = list(_cedulas_recientes)
    d["cedulas_consulta_recientes"] = cedulas
    d["nota_contadores"] = (
        "Los números son por proceso del servidor (worker). "
        "Con varios workers en Render, cada instancia lleva su propio contador. "
        f"Hasta {_MAX_CEDULAS_MONITOR} cédulas enmascaradas (últimas recibidas en query.message, sin mensajes de prueba)."
    )
    return d


class _AutoResponderQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sender: str = ""
    message: str = ""
    isGroup: bool = False
    groupParticipant: str = ""
    ruleId: int = 0
    isTestMessage: bool = False


class AutoResponderWebhookBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    appPackageName: Optional[str] = None
    messengerPackageName: Optional[str] = None
    query: Optional[_AutoResponderQuery] = None


def _autoresponder_credentials_configured() -> bool:
    u = (getattr(settings, "AUTORESPONDER_WEBHOOK_USER", None) or "").strip()
    p = (getattr(settings, "AUTORESPONDER_WEBHOOK_PASSWORD", None) or "").strip()
    return bool(u and p)


def _verify_basic_autoresponder(request: Request) -> bool:
    if not _autoresponder_credentials_configured():
        return False
    expected_u = (settings.AUTORESPONDER_WEBHOOK_USER or "").strip()
    expected_p = (settings.AUTORESPONDER_WEBHOOK_PASSWORD or "").strip()
    auth = (request.headers.get("Authorization") or "").strip()
    if not auth.lower().startswith("basic "):
        return False
    try:
        decoded = base64.b64decode(auth[6:].strip(), validate=True).decode(
            "utf-8", errors="strict"
        )
    except Exception:
        return False
    if ":" not in decoded:
        return False
    user, _, password = decoded.partition(":")
    return secrets.compare_digest(user, expected_u) and secrets.compare_digest(
        password, expected_p
    )


def _json_replies(messages: list[str], status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"replies": [{"message": m} for m in messages]},
        media_type="application/json; charset=utf-8",
    )


def build_payload_prueba_autoresponder() -> dict:
    """Cuerpo JSON con isTestMessage (no dispara solicitar-código ni correo)."""
    return {
        "appPackageName": "tkstudio.autoresponder",
        "messengerPackageName": "com.whatsapp",
        "query": {
            "sender": "Monitor RapiCredit",
            "message": "0",
            "isGroup": False,
            "groupParticipant": "",
            "ruleId": 0,
            "isTestMessage": True,
        },
    }


@router.post("/webhook-autoresponder")
async def post_autoresponder_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Recibe POST JSON de AutoResponder. ``query.message`` se usa como cédula (texto del chat).
    Delega en la misma lógica que ``POST /estado-cuenta/public/solicitar-codigo`` (código por correo).

    Si ``query.isTestMessage`` es true (prueba desde AutoResponder o monitor interno), responde OK
    sin enviar correo ni consultar cédula.
    """
    if not _autoresponder_credentials_configured():
        _record(categoria="sin_config", exito=False, error_resumen="webhook sin variables de entorno")
        return _json_replies(
            [
                "El enlace con AutoResponder no está activo en el servidor. "
                "El administrador debe definir AUTORESPONDER_WEBHOOK_USER y AUTORESPONDER_WEBHOOK_PASSWORD en Render."
            ],
            status_code=503,
        )

    if not _verify_basic_autoresponder(request):
        _record(categoria="auth_fail", exito=False, error_resumen="Basic Auth inválido o ausente")
        return JSONResponse(
            status_code=401,
            content={"replies": [{"message": "No autorizado."}]},
            headers={"WWW-Authenticate": 'Basic realm="AutoResponder"'},
            media_type="application/json; charset=utf-8",
        )

    raw = await request.body()
    try:
        body = AutoResponderWebhookBody.model_validate_json(raw or b"{}")
    except Exception:
        _record(categoria="json_invalido", exito=False, error_resumen="JSON no parseable")
        return _json_replies(
            [
                "JSON no válido o incompleto. Revise que AutoResponder envíe el cuerpo oficial "
                "(appPackageName, messengerPackageName, query.message, etc.)."
            ],
            status_code=400,
        )

    q = body.query
    if q and q.isTestMessage:
        if not body.appPackageName or not body.messengerPackageName:
            _record(
                categoria="json_incompleto",
                exito=False,
                error_resumen="prueba sin app/messenger package",
            )
            return _json_replies(
                ["JSON incompleto (mensaje de prueba). Revise appPackageName y messengerPackageName."],
                status_code=400,
            )
        _record(categoria="prueba_ok", exito=True)
        return _json_replies(
            [
                "Prueba recibida: el webhook y Basic Auth funcionan.",
                "No se envió ningún código de estado de cuenta (mensaje de prueba).",
            ]
        )

    if (
        not body.appPackageName
        or not body.messengerPackageName
        or not q
        or not (q.sender or "").strip()
        or not (q.message or "").strip()
    ):
        _record(
            categoria="json_incompleto",
            exito=False,
            error_resumen="faltan campos obligatorios del contrato AutoResponder",
        )
        return _json_replies(
            ["JSON incompleto. ¿La petición fue enviada por AutoResponder?"],
            status_code=400,
        )

    cedula_text = (q.message or "").strip()
    if not cedula_text:
        _record(categoria="json_incompleto", exito=False, error_resumen="message vacío")
        return _json_replies(["Envíe solo el número de cédula (mensaje de texto)."])

    _registrar_cedula_recibida_api(cedula_text)

    try:
        resp = solicitar_codigo_estado_cuenta(
            request, SolicitarCodigoRequest(cedula=cedula_text), db
        )
    except HTTPException as he:
        det = he.detail
        msg = det if isinstance(det, str) else "No se pudo procesar la solicitud."
        _record(
            categoria="solicitar_excepcion",
            exito=False,
            error_resumen=f"HTTPException {he.status_code}: {msg[:200]}",
        )
        logger.info(
            "autoresponder_webhook solicitar_codigo HTTPException status=%s sender=%s",
            he.status_code,
            (q.sender or "")[:40],
        )
        return _json_replies([msg])

    if resp.ok:
        _record(categoria="solicitar_ok", exito=True)
        msg = (resp.mensaje or "").strip() or (
            "Si la cédula está registrada, recibirá un código por correo para consultar su estado de cuenta."
        )
        lines = [msg]
        # AutoResponder solo admite texto en "replies"; el PDF no viaja en el JSON.
        portal_pdf = url_portal_estado_cuenta_publico()
        if portal_pdf:
            lines.append(
                "Para descargar su estado de cuenta en PDF: abra "
                f"{portal_pdf} e ingrese su cédula y el código enviado a su correo. "
                "En esa página podrá ver y descargar el PDF."
            )
        else:
            lines.append(
                "El PDF del estado de cuenta se obtiene en el portal web público "
                "ingresando la cédula y el código que recibirá por correo "
                "(WhatsApp solo muestra texto; el archivo PDF no se adjunta por este webhook)."
            )
        return _json_replies(lines)

    err = (resp.error or "No se pudo procesar la solicitud.").strip()
    _record(
        categoria="solicitar_error_respuesta",
        exito=False,
        error_resumen=err[:200],
    )
    return _json_replies([err])


def url_portal_estado_cuenta_publico() -> str:
    """
    URL del SPA donde el cliente ingresa cédula + código y obtiene/descarga el PDF.
    Depende de FRONTEND_PUBLIC_URL (ej. https://host/pagos → .../pagos/rapicredit-estadocuenta).
    """
    base = (getattr(settings, "FRONTEND_PUBLIC_URL", None) or "").strip().rstrip("/")
    if not base:
        return ""
    return f"{base}/rapicredit-estadocuenta"


def build_autoresponder_webhook_post_url() -> str:
    """URL absoluta del POST (sin barra final duplicada)."""
    base = get_effective_api_public_base_url().strip().rstrip("/")
    if not base:
        return ""
    path = f"{settings.API_V1_STR}/estado-cuenta/public/webhook-autoresponder"
    return f"{base}{path}"
