"""
Endpoints de configuración AI usando OpenRouter.
La API key se lee SOLO de variables de entorno (OPENROUTER_API_KEY); nunca se expone al frontend.
Configuración (modelo, temperatura, max_tokens, activo) se persiste en BD (tabla configuracion).
Ref: https://openrouter.ai/docs/api-reference/chat/completion
"""
import json
import urllib.request
import urllib.error
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.configuracion import Configuracion
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.cuota import Cuota
from sqlalchemy import func

router = APIRouter()

CLAVE_AI = "configuracion_ai"

# Valores por defecto (se sobrescriben desde BD si existe)
_DEFAULT_AI_CONFIG: dict[str, Any] = {
    "modelo": None,
    "temperatura": "0.7",
    "max_tokens": "1000",
    "activo": "true",
}

# Caché en memoria sincronizado con BD
_ai_config_stub: dict[str, Any] = dict(_DEFAULT_AI_CONFIG)


def _load_ai_config_from_db(db: Session) -> None:
    """Carga configuración AI desde BD y actualiza _ai_config_stub."""
    global _ai_config_stub
    try:
        row = db.get(Configuracion, CLAVE_AI)
        if row and row.valor:
            data = json.loads(row.valor)
            if isinstance(data, dict):
                for k in ("modelo", "temperatura", "max_tokens", "activo"):
                    if k in data and data[k] is not None:
                        _ai_config_stub[k] = str(data[k])
    except Exception:
        pass


def _build_chat_context(db: Session) -> str:
    """Construye un resumen de la BD para inyectar en el system prompt del chat (respuestas con datos reales)."""
    lines: list[str] = []
    try:
        total_clientes = db.query(func.count(Cliente.id)).scalar() or 0
        total_prestamos = db.query(func.count(Prestamo.id)).scalar() or 0
        prestamos_activos = db.query(func.count(Prestamo.id)).filter(Prestamo.estado == "ACTIVO").scalar() or 0
        total_cuotas = db.query(func.count(Cuota.id)).scalar() or 0
        cuotas_pagadas = db.query(func.count(Cuota.id)).filter(Cuota.fecha_pago.isnot(None)).scalar() or 0
        cuotas_pendientes = total_cuotas - cuotas_pagadas
        lines.append(f"- Clientes: {total_clientes} total.")
        lines.append(f"- Préstamos: {total_prestamos} total; {prestamos_activos} activos.")
        lines.append(f"- Cuotas: {total_cuotas} total; {cuotas_pagadas} pagadas; {cuotas_pendientes} pendientes.")
    except Exception:
        lines.append("(No se pudo cargar el resumen de la base de datos.)")
    return "Contexto actual de la base de datos del sistema:\n" + "\n".join(lines)


def _get_openrouter_key() -> Optional[str]:
    """API key solo desde entorno; nunca desde body ni BD."""
    key = getattr(settings, "OPENROUTER_API_KEY", None) or ""
    return key.strip() or None


def _get_model() -> str:
    m = _ai_config_stub.get("modelo") or getattr(settings, "OPENROUTER_MODEL", None) or "openai/gpt-4o-mini"
    return (m or "openai/gpt-4o-mini").strip()


def _call_openrouter(messages: list[dict], model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 1000) -> dict:
    """Llama a OpenRouter API. La clave solo se usa aquí desde settings."""
    key = _get_openrouter_key()
    if not key:
        raise HTTPException(status_code=503, detail="AI no configurada: falta OPENROUTER_API_KEY en el servidor. Configúrala en variables de entorno (dashboard de Render, etc.).")
    url = "https://openrouter.ai/api/v1/chat/completions"
    body = {
        "model": model or _get_model(),
        "messages": messages,
        "temperature": float(_ai_config_stub.get("temperatura") or temperature),
        "max_tokens": int(_ai_config_stub.get("max_tokens") or max_tokens),
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "HTTP-Referer": "https://rapicredit.onrender.com",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            out = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_err = e.read().decode() if e.fp else ""
        try:
            err_obj = json.loads(body_err) if body_err else {}
            detail = err_obj.get("error", {}).get("message", body_err) or str(e)
        except Exception:
            detail = body_err or str(e)
        raise HTTPException(status_code=min(e.code, 502), detail=f"OpenRouter: {detail}")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Error llamando a OpenRouter: {e}")
    return out


# --- GET /configuracion/ai/configuracion: devolver config SIN la clave (persistida en BD)
@router.get("/configuracion")
def get_ai_configuracion(db: Session = Depends(get_db)):
    """
    Devuelve la configuración AI para el frontend (desde BD).
    NUNCA incluye la API key; solo 'configured' (true si OPENROUTER_API_KEY está definida).
    """
    _load_ai_config_from_db(db)
    key = _get_openrouter_key()
    modelo = _get_model()
    return {
        "configured": bool(key),
        "provider": "openrouter",
        "modelo": modelo,
        "temperatura": _ai_config_stub.get("temperatura", "0.7"),
        "max_tokens": _ai_config_stub.get("max_tokens", "1000"),
        "activo": _ai_config_stub.get("activo", "true"),
        # Compatibilidad con frontend que esperaba openai_api_key: no enviar la clave, solo un placeholder
        "openai_api_key": "***" if key else "",
    }


class AIConfigUpdate(BaseModel):
    modelo: Optional[str] = None
    temperatura: Optional[str] = None
    max_tokens: Optional[str] = None
    activo: Optional[str] = None


@router.put("/configuracion")
def put_ai_configuracion(payload: AIConfigUpdate = Body(...), db: Session = Depends(get_db)):
    """
    Actualiza modelo, temperatura, max_tokens, activo y persiste en BD.
    La API key NUNCA se acepta ni se guarda aquí; solo desde variables de entorno.
    """
    _load_ai_config_from_db(db)
    data = payload.model_dump(exclude_none=True)
    for k in ("modelo", "temperatura", "max_tokens", "activo"):
        if k in data and data[k] is not None:
            _ai_config_stub[k] = str(data[k])
    # Persistir en BD
    try:
        row = db.get(Configuracion, CLAVE_AI)
        valor_json = json.dumps({
            "modelo": _ai_config_stub.get("modelo"),
            "temperatura": _ai_config_stub.get("temperatura"),
            "max_tokens": _ai_config_stub.get("max_tokens"),
            "activo": _ai_config_stub.get("activo"),
        })
        if row:
            row.valor = valor_json
        else:
            row = Configuracion(clave=CLAVE_AI, valor=valor_json)
            db.add(row)
        db.commit()
    except Exception:
        db.rollback()
    return get_ai_configuracion(db)


class ChatRequest(BaseModel):
    pregunta: str


@router.post("/chat")
def post_ai_chat(payload: ChatRequest = Body(...)):
    """
    Chat completions vía OpenRouter. La clave se usa solo en el backend.
    """
    pregunta = (payload.pregunta or "").strip()
    if not pregunta:
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía")
    if _ai_config_stub.get("activo", "true").lower() != "true":
        raise HTTPException(status_code=400, detail="El servicio AI está desactivado en configuración")
    messages = [{"role": "user", "content": pregunta}]
    try:
        out = _call_openrouter(messages)
    except HTTPException:
        raise
    choices = out.get("choices") or []
    if not choices:
        raise HTTPException(status_code=502, detail="OpenRouter no devolvió respuesta")
    content = (choices[0].get("message") or {}).get("content") or ""
    usage = out.get("usage") or {}
    return {
        "success": True,
        "respuesta": content,
        "pregunta": pregunta,
        "tokens_usados": usage.get("total_tokens"),
        "modelo_usado": out.get("model"),
    }


class ProbarRequest(BaseModel):
    mensaje: Optional[str] = None
    pregunta: Optional[str] = None
    usar_documentos: Optional[bool] = None


@router.post("/probar")
def post_ai_probar(payload: ProbarRequest = Body(...)):
    """Prueba la conexión con OpenRouter y devuelve la respuesta para el chat de prueba."""
    mensaje = (payload.mensaje or payload.pregunta or "Hola, responde OK si me escuchas.").strip() or "Hola."
    messages = [{"role": "user", "content": mensaje}]
    try:
        out = _call_openrouter(messages)
    except HTTPException:
        raise
    choices = out.get("choices") or []
    content = (choices[0].get("message") or {}).get("content") if choices else ""
    ok = bool(content)
    return {
        "success": ok,
        "message": "Conexión con OpenRouter correcta" if ok else "Sin respuesta",
        "mensaje": content if ok else ("Sin respuesta" if not content else content),
        "respuesta": content,
        "modelo_usado": out.get("model"),
        "tokens_usados": (out.get("usage") or {}).get("total_tokens"),
    }


@router.get("/documentos")
def get_ai_documentos():
    """
    Listado de documentos para RAG/IA. El frontend AIConfig lo usa.
    Sin persistencia de documentos se devuelve lista vacía para evitar 404.
    """
    return {"total": 0, "documentos": []}
