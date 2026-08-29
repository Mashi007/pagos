"""
Submódulo Auditoría → Email (buzón cobranza@rapicreditca.com).
OAuth callback es público (Google redirige sin Bearer).
"""
from __future__ import annotations

import json
import logging
import secrets
import urllib.parse
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_admin
from app.models.configuracion import Configuracion
from app.schemas.auth import UserResponse
from app.services.auditoria_email import scan_service as svc
from app.services.pagos_gmail.credentials import (
    SCOPES_GMAIL_DRIVE_SHEETS,
    cobranza_oauth_log_context,
    save_cobranza_gmail_tokens,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email", tags=["auditoria-email"])
router_oauth_callback = APIRouter(tags=["auditoria-email-oauth"])

GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
OAUTH_STATE_PREFIX = "auditoria_email_oauth_state_"


class ScanCreateBody(BaseModel):
    mode: str = Field(default="single", description="single | batch")
    criteria: Dict[str, Any] = Field(default_factory=dict)
    pipelineIds: Optional[List[str]] = None
    lotSize: int = 100
    maxMessages: int = 32000


class EstimateBody(BaseModel):
    criteria: Dict[str, Any] = Field(default_factory=dict)


class ReescaneoBody(BaseModel):
    messageIds: List[int]
    pipelineIds: Optional[List[str]] = None


class AprobarRecibosLoteBody(BaseModel):
    receiptIds: List[int] = Field(default_factory=list)


def _backend_base_url() -> str:
    url = (getattr(settings, "BACKEND_PUBLIC_URL", None) or "").strip()
    if url:
        return url.rstrip("/")
    redirect_uri = (getattr(settings, "GOOGLE_REDIRECT_URI", None) or "").strip()
    if redirect_uri and redirect_uri.startswith("http"):
        try:
            parsed = urllib.parse.urlparse(redirect_uri)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            pass
    return "https://rapicredit.onrender.com"


def _frontend_base_url() -> str:
    url = (getattr(settings, "FRONTEND_PUBLIC_URL", None) or "").strip()
    if url:
        return url.rstrip("/")
    return _backend_base_url()


def _auditoria_email_conexion_url(*, query: str) -> str:
    """SPA con basename /pagos (mismo patrón que informe-pagos → /pagos/configuracion)."""
    return f"{_frontend_base_url()}/pagos/auditoria/email/conexion?{query.lstrip('?')}"


def _oauth_redirect_uri() -> str:
    return f"{_backend_base_url()}{settings.API_V1_STR}/auditoria/email/oauth/callback"


def _oauth_client_pair() -> tuple[Optional[str], Optional[str]]:
    return svc._cobranza_client_pair()


@router.get("/status")
def get_status(
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    data = svc.connection_status(db)
    data["oauth_redirect_uri"] = _oauth_redirect_uri()
    return data


@router.get("/oauth/redirect-uri")
def get_oauth_redirect_uri(
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, str]:
    return {"redirect_uri": _oauth_redirect_uri()}


@router.get("/oauth/authorize")
def oauth_authorize(
    db: Session = Depends(get_db),
    admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Devuelve URL de Google para autorizar cobranza@ (solo admin).
    Entrar en Google **como cobranza@**; el refresh token se guarda aparte de Pagos Gmail.
    """
    client_id, client_secret = _oauth_client_pair()
    if not client_id or not client_secret:
        logger.warning(
            "[AUDITORIA_EMAIL] OAuth authorize sin credenciales %s",
            cobranza_oauth_log_context(),
        )
        raise HTTPException(
            status_code=400,
            detail=(
                "Configura OAuth para cobranza@: en Render AUDITORIA_EMAIL_GOOGLE_CLIENT_ID "
                "(cliente Web cobranzas …bitt…) y Client ID + Secret en Configuración > Informe de "
                "pagos (mismo cliente). Si itmaster ya funciona, cobranza@ reutiliza el secret de "
                "Informe de pagos automáticamente."
            ),
        )
    state = secrets.token_urlsafe(32)
    state_key = f"{OAUTH_STATE_PREFIX}{state}"
    state_val = json.dumps(
        {"user_id": admin.id, "created_at": datetime.utcnow().isoformat()}
    )
    row = db.get(Configuracion, state_key)
    if row:
        row.valor = state_val
    else:
        db.add(Configuracion(clave=state_key, valor=state_val))
    db.commit()
    params = {
        "client_id": client_id,
        "redirect_uri": _oauth_redirect_uri(),
        "response_type": "code",
        "scope": " ".join(SCOPES_GMAIL_DRIVE_SHEETS),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "login_hint": svc.mailbox_target(),
    }
    url = f"{GOOGLE_AUTH_URI}?{urllib.parse.urlencode(params)}"
    logger.info(
        "[AUDITORIA_EMAIL] OAuth authorize user_id=%s redirect_uri=%s %s",
        admin.id,
        _oauth_redirect_uri(),
        cobranza_oauth_log_context(),
    )
    return {
        "redirect_url": url,
        "mailbox": svc.mailbox_target(),
        "redirect_uri": _oauth_redirect_uri(),
    }


@router_oauth_callback.get("/auditoria/email/oauth/callback")
def oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    redirect_ok = _auditoria_email_conexion_url(query="oauth=ok")

    def _fail(reason: str) -> RedirectResponse:
        logger.warning(
            "[AUDITORIA_EMAIL] OAuth callback fail reason=%s %s",
            reason,
            cobranza_oauth_log_context(),
        )
        u = _auditoria_email_conexion_url(
            query=f"oauth=error&reason={urllib.parse.quote(reason)}"
        )
        return RedirectResponse(url=u, status_code=302)

    if error or not code or not state:
        logger.warning("[AUDITORIA_EMAIL] OAuth callback error=%s", error)
        return _fail("no_code")
    state_key = f"{OAUTH_STATE_PREFIX}{state}"
    row = db.get(Configuracion, state_key)
    if not row or not row.valor:
        return _fail("state_invalid")
    try:
        data = json.loads(row.valor)
        created = datetime.fromisoformat(data["created_at"])
        if datetime.utcnow() - created > timedelta(minutes=30):
            db.delete(row)
            db.commit()
            return _fail("state_expired")
    except Exception:
        db.delete(row)
        db.commit()
        return _fail("state_expired")
    db.delete(row)
    db.commit()

    client_id, client_secret = _oauth_client_pair()
    if not client_id or not client_secret:
        return _fail("no_credentials")
    redirect_uri = _oauth_redirect_uri()
    logger.info(
        "[AUDITORIA_EMAIL] OAuth callback token_exchange start redirect_uri=%s %s",
        redirect_uri,
        cobranza_oauth_log_context(),
    )
    payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    try:
        with httpx.Client() as client:
            r = client.post(
                GOOGLE_TOKEN_URI,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=20.0,
            )
            r.raise_for_status()
            tokens = r.json()
    except httpx.HTTPStatusError as e:
        google_err = "token_exchange"
        google_desc = ""
        try:
            err_body = e.response.json()
            google_err = str(err_body.get("error") or google_err)
            google_desc = str(err_body.get("error_description") or "")[:240]
        except Exception:
            pass
        logger.error(
            "[AUDITORIA_EMAIL] token exchange status=%s error=%s desc=%s client_suffix=%s secret_len=%s secret_suffix=%s",
            e.response.status_code,
            google_err,
            google_desc,
            client_id[-20:] if client_id else None,
            len(client_secret) if client_secret else 0,
            client_secret[-4:] if client_secret and len(client_secret) >= 4 else None,
        )
        known = frozenset(
            {"invalid_client", "redirect_uri_mismatch", "invalid_grant", "unauthorized_client"}
        )
        return _fail(google_err if google_err in known else "token_exchange")
    except Exception as e:
        logger.exception("[AUDITORIA_EMAIL] token exchange: %s", e)
        return _fail("token_exchange")
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        logger.warning(
            "[AUDITORIA_EMAIL] OAuth OK sin refresh_token (reintenta con prompt=consent) %s",
            cobranza_oauth_log_context(),
        )
        return _fail("no_refresh_token")
    try:
        path = save_cobranza_gmail_tokens(
            refresh_token=refresh_token,
            access_token=tokens.get("access_token"),
            db=db,
        )
    except Exception as e:
        logger.exception("[AUDITORIA_EMAIL] save tokens: %s", e)
        return _fail("save_failed")
    logger.info(
        "[AUDITORIA_EMAIL] OAuth cobranza@ OK path=%s %s",
        path,
        cobranza_oauth_log_context(),
    )
    return RedirectResponse(url=redirect_ok, status_code=302)


@router.get("/kpis")
def get_kpis(
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    return svc.kpis(db)


@router.get("/pipelines")
def get_pipelines(
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    return {"items": svc.pipelines_catalog()}


@router.get("/alineamiento")
def get_alineamiento(
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    return svc.alineamiento()


@router.get("/bitacora")
def get_bitacora(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    return {"items": svc.list_bitacora(db, limit=limit)}


@router.get("/scans/paused")
def get_paused_scans(
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    return {"items": svc.list_paused_scans(db)}


@router.post("/scans/estimate")
def post_estimate(
    body: EstimateBody,
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    return svc.estimate(db, body.criteria or {})


@router.get("/scans/preset-defaults")
def get_preset_defaults(
    preset: str = Query("ultimos-7"),
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    """Criterios frescos al cambiar preset en Escanear (UI alineada con query)."""
    from app.services.auditoria_email.query import criteria_from_preset

    return criteria_from_preset(preset)


@router.post("/scans")
def post_create_scan(
    body: ScanCreateBody,
    db: Session = Depends(get_db),
    admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    try:
        scan = svc.create_scan(
            db,
            mode=body.mode,
            criteria=body.criteria or {},
            pipeline_ids=body.pipelineIds,
            lot_size=body.lotSize,
            max_messages=body.maxMessages,
            created_by=getattr(admin, "email", None),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    try:
        return svc.advance_scan(db, scan.id, max_lots=1)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:500]) from e


@router.get("/scans/{scan_id}")
def get_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    try:
        return svc.get_scan(db, scan_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/scans/{scan_id}/advance")
def post_advance_scan(
    scan_id: int,
    maxLots: int = Query(1, ge=1, le=3),
    background: bool = Query(True),
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    try:
        return svc.advance_scan(
            db, scan_id, max_lots=maxLots, background=background
        )
    except ValueError as e:
        msg = str(e)
        code = 404 if "no encontrado" in msg.lower() else 400
        raise HTTPException(status_code=code, detail=msg) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:500]) from e


@router.get("/bandeja")
def get_bandeja(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=10000),
    q: Optional[str] = None,
    route: Optional[str] = None,
    classify: Optional[str] = None,
    cedula: Optional[str] = Query(
        None,
        description="Filtro cédula: valor parcial, o 'NA' / 'sin' para sin cédula",
    ),
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    return svc.list_messages(
        db,
        skip=skip,
        limit=limit,
        q=q,
        route=route,
        classify=classify,
        cedula_filter=cedula,
    )


@router.get("/bandeja/{message_id}")
def get_bandeja_item(
    message_id: int,
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    try:
        return svc.get_message(db, message_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/bandeja/re-escanear")
def post_reescaneo(
    body: ReescaneoBody,
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    if not body.messageIds:
        raise HTTPException(status_code=400, detail="messageIds vacío")
    try:
        return svc.reescaneo(
            db, message_ids=body.messageIds, pipeline_ids=body.pipelineIds
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:500]) from e


@router.post("/bandeja/eliminar-lote")
def post_eliminar_bandeja_lote(
    body: ReescaneoBody,
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    """Selección múltiple: elimina mensajes de Bandeja (+ recibos pending)."""
    if not body.messageIds:
        raise HTTPException(status_code=400, detail="messageIds vacío")
    try:
        return svc.eliminar_mensajes_lote(db, body.messageIds)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:500]) from e


@router.get("/recibos")
def get_recibos(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=10000),
    status: str = Query("pending", description="pending|approved|revision|all"),
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    return svc.list_receipts(db, skip=skip, limit=limit, status=status)


@router.post("/recibos/aprobar-lote")
def post_aprobar_recibos_lote(
    body: AprobarRecibosLoteBody,
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Selección múltiple: por cada recibo pending aplica validadores.
    OK → cuotas/cartera; si no → pagos_con_errores (revisión manual).
    """
    from app.services.auditoria_email.receipts_service import aprobar_recibos_lote

    if not body.receiptIds:
        raise HTTPException(status_code=400, detail="receiptIds vacío")
    try:
        return aprobar_recibos_lote(db, body.receiptIds)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:500]) from e


@router.post("/recibos/eliminar-lote")
def post_eliminar_recibos_lote(
    body: AprobarRecibosLoteBody,
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    """Selección múltiple: elimina pending de la cola Recibos."""
    from app.services.auditoria_email.receipts_service import eliminar_recibos_lote

    if not body.receiptIds:
        raise HTTPException(status_code=400, detail="receiptIds vacío")
    try:
        return eliminar_recibos_lote(db, body.receiptIds)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:500]) from e


@router.get("/recibos/{receipt_id}")
def get_recibo(
    receipt_id: int,
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    from app.models.auditoria_email import AuditoriaEmailReceipt
    from app.services.auditoria_email.receipts_service import (
        receipt_dict,
        serial_estado_recibo,
    )

    row = db.get(AuditoriaEmailReceipt, receipt_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Recibo no encontrado")
    return receipt_dict(row, serial_estado=serial_estado_recibo(db, row))


@router.post("/recibos/{receipt_id}/aprobar")
def post_aprobar_recibo(
    receipt_id: int,
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    from app.services.auditoria_email.receipts_service import aprobar_recibo

    try:
        return aprobar_recibo(db, receipt_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:500]) from e


@router.delete("/recibos/{receipt_id}")
def delete_recibo(
    receipt_id: int,
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    from app.services.auditoria_email.receipts_service import eliminar_recibo

    try:
        return eliminar_recibo(db, receipt_id)
    except ValueError as e:
        msg = str(e)
        code = 404 if "no encontrado" in msg.lower() else 400
        raise HTTPException(status_code=code, detail=msg) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:500]) from e


@router.post("/recibos/{receipt_id}/revision-manual")
def post_revision_manual_recibo(
    receipt_id: int,
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    from app.services.auditoria_email.receipts_service import revision_manual_recibo

    try:
        return revision_manual_recibo(db, receipt_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)[:500]) from e
