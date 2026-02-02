"""
Endpoints de configuración WhatsApp para Comunicaciones.
GET/PUT /configuracion/whatsapp/configuracion.
Políticas: no exponer access_token en GET (se devuelve ***), no sobrescribir token
cuando el frontend envía valor enmascarado (*** o vacío). Persiste en BD (tabla configuracion).
"""
import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.whatsapp_config_holder import sync_from_db as whatsapp_sync_from_db
from app.models.configuracion import Configuracion

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
    ok = send_whatsapp_text(destino, mensaje)
    if ok:
        return {
            "success": True,
            "mensaje": "Mensaje de prueba enviado correctamente.",
            "telefono_destino": destino,
        }
    return {
        "success": False,
        "mensaje": "No se pudo enviar. Revisa Access Token, Phone Number ID y que el número tenga formato internacional.",
        "telefono_destino": destino,
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
