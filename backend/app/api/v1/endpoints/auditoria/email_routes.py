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
from app.core.deps import get_current_user, require_admin
from app.models.configuracion import Configuracion
from app.models.user import User
from app.schemas.auth import UserResponse
from app.services.auditoria_email import scan_service as svc
from app.services.pagos_gmail.credentials import (
    SCOPES_GMAIL_DRIVE_SHEETS,
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
    maxMessages: int = 100


class EstimateBody(BaseModel):
    criteria: Dict[str, Any] = Field(default_factory=dict)


class ReescaneoBody(BaseModel):
    messageIds: List[int]
    pipelineIds: Optional[List[str]] = None


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
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Devuelve URL de Google para autorizar cobranza@.
    Entrar en Google **como cobranza@**; el refresh token se guarda aparte de Pagos Gmail.
    """
    client_id, client_secret = _oauth_client_pair()
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=400,
            detail=(
                "Configura AUDITORIA_EMAIL_GOOGLE_CLIENT_ID/SECRET o GOOGLE_CLIENT_ID/SECRET."
            ),
        )
    state = secrets.token_urlsafe(32)
    state_key = f"{OAUTH_STATE_PREFIX}{state}"
    state_val = json.dumps(
        {"user_id": current_user.id, "created_at": datetime.utcnow().isoformat()}
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
    frontend_base = _frontend_base_url()
    redirect_ok = f"{frontend_base}/auditoria/email/conexion?oauth=ok"
    redirect_err = f"{frontend_base}/auditoria/email/conexion?oauth=error"

    def _fail(reason: str) -> RedirectResponse:
        u = f"{redirect_err}&reason={urllib.parse.quote(reason)}"
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
        if datetime.utcnow() - created > timedelta(minutes=10):
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
    payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": _oauth_redirect_uri(),
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
    except Exception as e:
        logger.exception("[AUDITORIA_EMAIL] token exchange: %s", e)
        return _fail("token_exchange")
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        return _fail("no_refresh_token")
    try:
        save_cobranza_gmail_tokens(
            refresh_token=refresh_token,
            access_token=tokens.get("access_token"),
        )
    except Exception as e:
        logger.exception("[AUDITORIA_EMAIL] save tokens: %s", e)
        return _fail("save_failed")
    logger.info("[AUDITORIA_EMAIL] OAuth cobranza@ OK → %s", svc._cobranza_tokens_path())
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
    limit: int = Query(50, ge=1, le=200),
    q: Optional[str] = None,
    route: Optional[str] = None,
    classify: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    return svc.list_messages(
        db, skip=skip, limit=limit, q=q, route=route, classify=classify
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


@router.get("/recibos")
def get_recibos(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    return svc.list_receipts(db, skip=skip, limit=limit)


@router.get("/recibos/{receipt_id}")
def get_recibo(
    receipt_id: int,
    db: Session = Depends(get_db),
    _admin: UserResponse = Depends(require_admin),
) -> Dict[str, Any]:
    from app.models.auditoria_email import AuditoriaEmailReceipt

    row = db.get(AuditoriaEmailReceipt, receipt_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Recibo no encontrado")
    return svc._receipt_dict(row)
