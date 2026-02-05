"""
Endpoints de configuración AI usando OpenRouter.
La API key se lee SOLO de variables de entorno (OPENROUTER_API_KEY); nunca se expone al frontend.
Configuración (modelo, temperatura, max_tokens, activo) se persiste en BD (tabla configuracion).

Estructura para respuestas rápidas y datos de get_db:
- CHAT_SYSTEM_PROMPT_INSTRUCCIONES: prompt que exige usar solo datos del bloque 'Datos disponibles (get_db)'.
- _build_chat_context(db): una ronda de consultas agregadas (count) para armar ese bloque de forma compacta.
- _build_chat_system_prompt(db): instrucciones + 'Datos disponibles (get_db):' + contexto; el modelo debe
  responder con cualquier dato disponible ahí. OPENROUTER_TIMEOUT acota la espera.
Ref: https://openrouter.ai/docs/api-reference/chat/completion
"""
import json
import urllib.error
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session

import logging

from app.core.config import settings
from app.core.database import get_db, engine, SessionLocal
from app.core.openrouter_client import call_openrouter as _openrouter_call
from app.models.configuracion import Configuracion
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.cuota import Cuota
from app.models.definicion_campo import DefinicionCampo
from app.models.diccionario_semantico import DiccionarioSemantico
from sqlalchemy import func, select, text
from sqlalchemy import inspect as sa_inspect

# Timeout para la consulta de contexto AI (evitar colgar si la BD tarda)
CONTEXTO_AI_STATEMENT_TIMEOUT_MS = 10_000  # 10 segundos

logger = logging.getLogger(__name__)
router = APIRouter()

CLAVE_AI = "configuracion_ai"
# Clave opcional en tabla configuracion: JSON array de {"pregunta": "...", "campo": "..."} para
# personalizar preguntas habituales desde la app (Configuración > AI > Preguntas habituales).
CLAVE_PREGUNTAS_HABITUALES_AI = "preguntas_habituales_ai"

# Preguntas habituales por defecto (se usa si no hay lista en BD).
# Se inyecta en el system prompt para familiarizar al modelo con cómo responder cada tipo de pregunta.
PREGUNTAS_HABITUALES_CAMPOS = (
    "Preguntas habituales y dato a usar: "
    "'cuántos créditos aprobados' / 'créditos aprobados' -> prestamos_aprobados; "
    "'total de financiamiento' / 'financiamiento total' -> total_financiamiento_aprobado (o total_financiamiento_todos si preguntan por todos); "
    "'cuántos clientes' -> clientes_total; "
    "'cuántos préstamos' -> prestamos_total; "
    "'cuotas pagadas' / 'cuotas pendientes' -> cuotas_pagadas, cuotas_pendientes, cuotas_total; "
    "'recaudado' / 'cuánto se ha cobrado en cuotas' -> suma_montos_cuotas_pagadas."
)

# Prompt del sistema para respuestas rápidas usando solo datos de get_db (BD).
# Instruye al modelo a responder únicamente con los datos disponibles en el contexto inyectado.
CHAT_SYSTEM_PROMPT_INSTRUCCIONES = (
    "Eres un asistente que responde SOLO con datos de la base de datos del sistema. "
    "Debes usar ÚNICAMENTE los datos que se te proporcionan en el bloque 'Datos disponibles (get_db)' más abajo; "
    "responde con cualquier dato disponible que responda la pregunta. "
    "Sé conciso y directo para respuestas rápidas. "
    "Si la pregunta no puede responderse con los datos proporcionados, di que ese dato no está disponible en el contexto. "
    "No inventes cifras ni información. "
    "Si la pregunta no es sobre la base de datos del sistema (clientes, préstamos, cuotas, pagos, estadísticas), "
    "indica que solo respondes consultas sobre estos datos. "
    "Responde SIEMPRE en español."
)

# Modelo recomendado para OpenRouter (balance costo/velocidad/calidad para Chat y GPT).
MODELO_RECOMENDADO = "openai/gpt-4o-mini"

# Valores por defecto (se sobrescriben desde BD si existe)
_DEFAULT_AI_CONFIG: dict[str, Any] = {
    "modelo": None,
    "temperatura": "0.7",
    "max_tokens": "1000",
    "activo": "true",
    "openrouter_api_key": None,  # Token OpenRouter; también se puede usar OPENROUTER_API_KEY en env
}

# Caché en memoria sincronizado con BD
_ai_config_stub: dict[str, Any] = dict(_DEFAULT_AI_CONFIG)


def _is_api_key_masked(value: Any) -> bool:
    """True si el frontend envía valor enmascarado (no sobrescribir el token real)."""
    if value is None:
        return True
    s = (value if isinstance(value, str) else str(value)).strip()
    return s == "" or s == "***" or s == "••••••"


def _load_ai_config_from_db(db: Session) -> None:
    """Carga configuración AI desde BD y actualiza _ai_config_stub (incluye openrouter_api_key; no se expone en GET)."""
    global _ai_config_stub
    try:
        row = db.get(Configuracion, CLAVE_AI)
        if row and row.valor:
            data = json.loads(row.valor)
            if isinstance(data, dict):
                for k in ("modelo", "temperatura", "max_tokens", "activo"):
                    if k in data and data[k] is not None:
                        _ai_config_stub[k] = str(data[k])
                if "openrouter_api_key" in data and data["openrouter_api_key"]:
                    _ai_config_stub["openrouter_api_key"] = str(data["openrouter_api_key"]).strip()
                if "prompt_personalizado" in data and data["prompt_personalizado"] is not None:
                    _ai_config_stub["prompt_personalizado"] = str(data["prompt_personalizado"])
    except Exception:
        pass


def _safe_decimal(value: Any) -> str:
    """Formatea un valor numérico/Decimal para el contexto (evitar None o exponencial)."""
    if value is None:
        return "0"
    try:
        f = float(value)
        return f"{f:,.2f}" if f != int(f) else f"{int(f):,}"
    except (TypeError, ValueError):
        return str(value)


def _build_chat_context(db: Session) -> str:
    """
    Construye un resumen compacto de la BD para el system prompt.
    Una sola consulta agregada (1 round-trip) para minimizar tiempo de conexión y
    evitar múltiples accesos que puedan demorar o fallar. SQLAlchemy 2 (select + scalar_subquery).
    """
    lines: list[str] = []
    try:
        # Una única ejecución: todos los escalares en una sola consulta (mejor práctica AI-BD).
        stmt = select(
            select(func.count(Cliente.id)).scalar_subquery().label("total_clientes"),
            select(func.count(Prestamo.id)).scalar_subquery().label("total_prestamos"),
            select(func.count(Prestamo.id))
            .where(Prestamo.estado == "APROBADO")
            .scalar_subquery()
            .label("prestamos_aprobados"),
            select(func.coalesce(func.sum(Prestamo.total_financiamiento), 0))
            .where(Prestamo.estado == "APROBADO")
            .scalar_subquery()
            .label("total_financiamiento_aprobado"),
            select(func.coalesce(func.sum(Prestamo.total_financiamiento), 0))
            .scalar_subquery()
            .label("total_financiamiento_todos"),
            select(func.count(Cuota.id)).scalar_subquery().label("total_cuotas"),
            select(func.count(Cuota.id))
            .where(Cuota.fecha_pago.isnot(None))
            .scalar_subquery()
            .label("cuotas_pagadas_count"),
            select(func.coalesce(func.sum(Cuota.monto), 0))
            .where(Cuota.fecha_pago.isnot(None))
            .scalar_subquery()
            .label("suma_cuotas_pagadas"),
        )
        # Timeout explícito: no retener conexión si la consulta tarda (mejores prácticas AI-BD)
        db.execute(text(f"SET LOCAL statement_timeout = {CONTEXTO_AI_STATEMENT_TIMEOUT_MS}"))
        row = db.execute(stmt).first()
        if not row:
            lines.append("(sin datos)")
            return "\n".join(lines)
        total_clientes = int(row[0] or 0)
        total_prestamos = int(row[1] or 0)
        prestamos_aprobados = int(row[2] or 0)
        total_financiamiento_aprobado = row[3] or 0
        total_financiamiento_todos = row[4] or 0
        total_cuotas = int(row[5] or 0)
        cuotas_pagadas_count = int(row[6] or 0)
        cuotas_pendientes = total_cuotas - cuotas_pagadas_count
        suma_cuotas_pagadas = row[7] or 0
        lines.append(f"clientes_total={total_clientes}")
        lines.append(f"prestamos_total={total_prestamos}; prestamos_aprobados={prestamos_aprobados}")
        lines.append(
            f"total_financiamiento_aprobado={_safe_decimal(total_financiamiento_aprobado)}; "
            f"total_financiamiento_todos={_safe_decimal(total_financiamiento_todos)}"
        )
        lines.append(
            f"cuotas_total={total_cuotas}; cuotas_pagadas={cuotas_pagadas_count}; cuotas_pendientes={cuotas_pendientes}; "
            f"suma_montos_cuotas_pagadas={_safe_decimal(suma_cuotas_pagadas)}"
        )
    except Exception as e:
        logger.exception("AI chat: error al cargar contexto desde BD (tablas clientes/prestamos/cuotas): %s", e)
        lines.append("(error al cargar datos)")
    return "\n".join(lines)


def _get_preguntas_habituales_block(db: Session) -> str:
    """
    Devuelve el bloque de texto 'preguntas habituales -> campos' para el system prompt.
    Si en BD existe configuracion con clave CLAVE_PREGUNTAS_HABITUALES_AI y valor JSON array
    de {"pregunta": "...", "campo": "..."}, se usa esa lista; si no, se usa PREGUNTAS_HABITUALES_CAMPOS.
    Así se pueden familiarizar más preguntas desde la app sin tocar código.
    """
    try:
        row = db.get(Configuracion, CLAVE_PREGUNTAS_HABITUALES_AI)
        if row and row.valor:
            data = json.loads(row.valor)
            if isinstance(data, list) and len(data) > 0:
                parts = []
                for item in data:
                    if isinstance(item, dict) and item.get("pregunta") and item.get("campo"):
                        parts.append(f"'{item['pregunta']}' -> {item['campo']}")
                if parts:
                    return "Preguntas habituales y dato a usar: " + "; ".join(parts) + "."
    except Exception:
        pass
    return PREGUNTAS_HABITUALES_CAMPOS


def _build_chat_system_prompt(db: Session) -> str:
    """
    Arma el system prompt completo. Si hay prompt_personalizado en config, se usa como base
    y se añade el bloque 'Datos disponibles (get_db)'. Si no, instrucciones + preguntas habituales + datos.
    """
    _load_ai_config_from_db(db)
    datos_bd = _build_chat_context(db)
    prompt_custom = (_ai_config_stub.get("prompt_personalizado") or "").strip()
    if prompt_custom:
        return f"{prompt_custom}\n\nDatos disponibles (get_db):\n{datos_bd}"
    preguntas_block = _get_preguntas_habituales_block(db)
    return (
        f"{CHAT_SYSTEM_PROMPT_INSTRUCCIONES}\n\n"
        f"{preguntas_block}\n\n"
        f"Datos disponibles (get_db):\n{datos_bd}"
    )


def _build_chat_system_prompt_with_short_session() -> str:
    """
    Construye el system prompt usando una sesión de corta duración, que se cierra
    antes de llamar a OpenRouter. Así no se retiene una conexión de BD durante
    la llamada externa (hasta 45s), cumpliendo buenas prácticas AI-BD.
    """
    session = SessionLocal()
    try:
        _load_ai_config_from_db(session)
        return _build_chat_system_prompt(session)
    finally:
        session.close()


def _get_openrouter_key() -> Optional[str]:
    """API key: primero desde BD (configuración guardada en app), luego desde entorno OPENROUTER_API_KEY."""
    key_bd = (_ai_config_stub.get("openrouter_api_key") or "").strip()
    if key_bd:
        return key_bd
    key_env = getattr(settings, "OPENROUTER_API_KEY", None) or ""
    return key_env.strip() or None


def _get_model() -> str:
    m = _ai_config_stub.get("modelo") or getattr(settings, "OPENROUTER_MODEL", None) or MODELO_RECOMENDADO
    return (m or MODELO_RECOMENDADO).strip()


def _call_openrouter(messages: list[dict], model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 1000) -> dict:
    """Llama a OpenRouter API usando el cliente compartido. La clave solo se usa aquí desde config."""
    key = _get_openrouter_key()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="AI no configurada: ingresa tu API Key de OpenRouter en Configuración > Inteligencia Artificial (o configura OPENROUTER_API_KEY en variables de entorno del servidor). Obtén la clave en https://openrouter.ai/keys",
        )
    try:
        return _openrouter_call(
            messages=messages,
            api_key=key,
            model=model or _get_model(),
            temperature=float(_ai_config_stub.get("temperatura") or temperature),
            max_tokens=int(_ai_config_stub.get("max_tokens") or max_tokens),
        )
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


# --- GET /configuracion/ai/configuracion: devolver config SIN la clave (persistida en BD)
@router.get("/configuracion")
def get_ai_configuracion(db: Session = Depends(get_db)):
    """
    Devuelve la configuración AI para el frontend (desde BD).
    NUNCA incluye el token real: openai_api_key es "***" si hay clave (BD o env), "" si no.
    modelo_recomendado para que el frontend muestre el GPT recomendado.
    """
    _load_ai_config_from_db(db)
    key = _get_openrouter_key()
    modelo = _get_model()
    return {
        "configured": bool(key),
        "provider": "openrouter",
        "modelo": modelo,
        "modelo_recomendado": MODELO_RECOMENDADO,
        "temperatura": _ai_config_stub.get("temperatura", "0.7"),
        "max_tokens": _ai_config_stub.get("max_tokens", "1000"),
        "activo": _ai_config_stub.get("activo", "true"),
        "openai_api_key": "***" if key else "",
    }


class AIConfigUpdate(BaseModel):
    modelo: Optional[str] = None
    temperatura: Optional[str] = None
    max_tokens: Optional[str] = None
    activo: Optional[str] = None
    openai_api_key: Optional[str] = None  # Token OpenRouter; si es *** o vacío no se sobrescribe
    openrouter_api_key: Optional[str] = None  # Alias para el mismo token


@router.put("/configuracion")
def put_ai_configuracion(payload: AIConfigUpdate = Body(...), db: Session = Depends(get_db)):
    """
    Actualiza modelo, temperatura, max_tokens, activo y opcionalmente el token OpenRouter.
    Si openai_api_key u openrouter_api_key viene con *** o vacío, no se sobrescribe el token guardado.
    El token se persiste en BD (tabla configuracion, clave configuracion_ai); nunca se envía al
    frontend ni se registra en logs, para evitar fugas y baneos de la API key.
    """
    _load_ai_config_from_db(db)
    data = payload.model_dump(exclude_none=True)
    for k in ("modelo", "temperatura", "max_tokens", "activo"):
        if k in data and data[k] is not None:
            _ai_config_stub[k] = str(data[k])
    token_nuevo = data.get("openrouter_api_key") or data.get("openai_api_key")
    if token_nuevo is not None and not _is_api_key_masked(token_nuevo):
        _ai_config_stub["openrouter_api_key"] = str(token_nuevo).strip()
    # Persistir en BD (incluye openrouter_api_key si está en el stub); el token queda guardado
    # y no se sobrescribe cuando el frontend envía "***" en siguientes guardados
    try:
        row = db.get(Configuracion, CLAVE_AI)
        payload_bd = {
            "modelo": _ai_config_stub.get("modelo"),
            "temperatura": _ai_config_stub.get("temperatura"),
            "max_tokens": _ai_config_stub.get("max_tokens"),
            "activo": _ai_config_stub.get("activo"),
        }
        if _ai_config_stub.get("openrouter_api_key"):
            payload_bd["openrouter_api_key"] = _ai_config_stub["openrouter_api_key"]
        if "prompt_personalizado" in _ai_config_stub:
            payload_bd["prompt_personalizado"] = _ai_config_stub["prompt_personalizado"]
        valor_json = json.dumps(payload_bd)
        if row:
            row.valor = valor_json
        else:
            db.add(Configuracion(clave=CLAVE_AI, valor=valor_json))
        db.commit()
    except Exception:
        db.rollback()
    return get_ai_configuracion(db)


# --- Prompt personalizado (GET/PUT /ai/prompt) ---

CLAVE_PROMPT_VARIABLES = "configuracion_ai_prompt_variables"


def _get_prompt_personalizado(db: Session) -> str:
    """Lee el prompt personalizado desde la config AI (misma fila que modelo, etc.)."""
    _load_ai_config_from_db(db)
    return (_ai_config_stub.get("prompt_personalizado") or "").strip()


def _set_prompt_personalizado(db: Session, texto: str) -> None:
    """Persiste el prompt personalizado en la fila configuracion_ai."""
    row = db.get(Configuracion, CLAVE_AI)
    data = {}
    if row and row.valor:
        try:
            data = json.loads(row.valor)
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}
    data["prompt_personalizado"] = texto
    global _ai_config_stub
    _ai_config_stub["prompt_personalizado"] = texto
    valor_json = json.dumps(data)
    if row:
        row.valor = valor_json
    else:
        db.add(Configuracion(clave=CLAVE_AI, valor=valor_json))
    db.commit()


def _get_prompt_variables_list(db: Session) -> list[dict]:
    """Lee la lista de variables del prompt desde configuracion (JSON array)."""
    try:
        row = db.get(Configuracion, CLAVE_PROMPT_VARIABLES)
        if row and row.valor:
            data = json.loads(row.valor)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def _set_prompt_variables_list(db: Session, variables: list[dict]) -> None:
    """Persiste la lista de variables del prompt."""
    row = db.get(Configuracion, CLAVE_PROMPT_VARIABLES)
    valor_json = json.dumps(variables)
    if row:
        row.valor = valor_json
    else:
        db.add(Configuracion(clave=CLAVE_PROMPT_VARIABLES, valor=valor_json))
    db.commit()


class PromptPutBody(BaseModel):
    prompt: str = ""


@router.get("/prompt")
def get_ai_prompt(db: Session = Depends(get_db)):
    """
    Devuelve el prompt personalizado y si se está usando el por defecto.
    Incluye variables personalizadas para el frontend (Editor de prompt).
    """
    prompt_text = _get_prompt_personalizado(db)
    variables = _get_prompt_variables_list(db)
    # Asegurar que cada item tenga id, variable, descripcion, activo, orden
    variables_ok = []
    for i, v in enumerate(variables):
        if not isinstance(v, dict):
            continue
        variables_ok.append({
            "id": v.get("id", i + 1),
            "variable": v.get("variable", ""),
            "descripcion": v.get("descripcion", ""),
            "activo": v.get("activo", True),
            "orden": v.get("orden", i),
        })
    return {
        "prompt_personalizado": prompt_text,
        "tiene_prompt_personalizado": bool(prompt_text),
        "usando_prompt_default": not bool(prompt_text),
        "variables_personalizadas": variables_ok,
    }


@router.put("/prompt")
def put_ai_prompt(payload: PromptPutBody = Body(...), db: Session = Depends(get_db)):
    """Guarda el prompt personalizado. Si prompt está vacío, se restaura el por defecto."""
    texto = (payload.prompt or "").strip()
    _set_prompt_personalizado(db, texto)
    return get_ai_prompt(db)


# --- Variables del prompt (GET/POST/PUT/DELETE /ai/prompt/variables) ---

class PromptVariableCreate(BaseModel):
    variable: str
    descripcion: str
    activo: Optional[bool] = True
    orden: Optional[int] = None


class PromptVariableUpdate(BaseModel):
    variable: Optional[str] = None
    descripcion: Optional[str] = None
    activo: Optional[bool] = None


@router.get("/prompt/variables")
def get_ai_prompt_variables(db: Session = Depends(get_db)):
    """Lista las variables personalizadas del prompt."""
    variables = _get_prompt_variables_list(db)
    out = []
    for i, v in enumerate(variables):
        if not isinstance(v, dict):
            continue
        out.append({
            "id": v.get("id", i + 1),
            "variable": v.get("variable", ""),
            "descripcion": v.get("descripcion", ""),
            "activo": v.get("activo", True),
            "orden": v.get("orden", i),
        })
    return {"variables": out, "total": len(out)}


@router.post("/prompt/variables")
def post_ai_prompt_variable(payload: PromptVariableCreate = Body(...), db: Session = Depends(get_db)):
    """Crea una variable para el prompt."""
    variables = _get_prompt_variables_list(db)
    max_id = max((v.get("id") for v in variables if isinstance(v, dict) and v.get("id") is not None), default=0)
    try:
        max_id = max(int(max_id), 0)
    except (TypeError, ValueError):
        max_id = 0
    new_id = max_id + 1
    variable = (payload.variable or "").strip()
    if not variable:
        raise HTTPException(status_code=400, detail="variable es requerida")
    if not variable.startswith("{"):
        variable = "{" + variable
    if not variable.endswith("}"):
        variable = variable + "}"
    orden = payload.orden if payload.orden is not None else len(variables)
    new_var = {
        "id": new_id,
        "variable": variable,
        "descripcion": (payload.descripcion or "").strip(),
        "activo": payload.activo if payload.activo is not None else True,
        "orden": orden,
    }
    variables.append(new_var)
    _set_prompt_variables_list(db, variables)
    return new_var


@router.put("/prompt/variables/{variable_id}")
def put_ai_prompt_variable(
    variable_id: int,
    payload: PromptVariableUpdate = Body(...),
    db: Session = Depends(get_db),
):
    """Actualiza una variable del prompt."""
    variables = _get_prompt_variables_list(db)
    for v in variables:
        if not isinstance(v, dict):
            continue
        if v.get("id") == variable_id:
            if payload.variable is not None:
                var = (payload.variable or "").strip()
                if not var.startswith("{"):
                    var = "{" + var
                if not var.endswith("}"):
                    var = var + "}"
                v["variable"] = var
            if payload.descripcion is not None:
                v["descripcion"] = (payload.descripcion or "").strip()
            if payload.activo is not None:
                v["activo"] = bool(payload.activo)
            _set_prompt_variables_list(db, variables)
            return v
    raise HTTPException(status_code=404, detail="Variable no encontrada")


@router.delete("/prompt/variables/{variable_id}")
def delete_ai_prompt_variable(variable_id: int, db: Session = Depends(get_db)):
    """Elimina una variable del prompt."""
    variables = _get_prompt_variables_list(db)
    new_list = [v for v in variables if isinstance(v, dict) and v.get("id") != variable_id]
    if len(new_list) == len(variables):
        raise HTTPException(status_code=404, detail="Variable no encontrada")
    _set_prompt_variables_list(db, new_list)
    return {"ok": True}


class ChatRequest(BaseModel):
    pregunta: str


@router.post("/chat")
def post_ai_chat(payload: ChatRequest = Body(...)):
    """
    Chat completions vía OpenRouter. Carga config y contexto desde BD en una
    sesión de corta duración que se cierra antes de llamar a OpenRouter, para
    no retener conexión durante la llamada externa (mejores prácticas AI-BD).
    """
    pregunta = (payload.pregunta or "").strip()
    if not pregunta:
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía")
    # Construir prompt con sesión corta; conexión liberada antes de OpenRouter
    system_prompt = _build_chat_system_prompt_with_short_session()
    if _ai_config_stub.get("activo", "true").lower() != "true":
        raise HTTPException(status_code=400, detail="El servicio AI está desactivado en configuración")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": pregunta},
    ]
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
    """Prueba la conexión con OpenRouter. Carga config desde BD en sesión corta (no retiene conexión durante la llamada)."""
    session = SessionLocal()
    try:
        _load_ai_config_from_db(session)
    finally:
        session.close()
    mensaje = (payload.mensaje or payload.pregunta or "Hola, responde OK si me escuchas.").strip() or "Hola."
    messages = [
        {"role": "system", "content": "Responde SIEMPRE en español."},
        {"role": "user", "content": mensaje},
    ]
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
def get_ai_documentos(db: Session = Depends(get_db)):
    """
    Listado de documentos para RAG/IA. El frontend AIConfig lo usa.
    Con get_db para futura persistencia en BD; por ahora devuelve lista vacía.
    """
    return {"total": 0, "documentos": []}


# --- Calificaciones del Chat AI (persistidas en BD: tabla configuracion, clave chat_ai_calificaciones) ---

CLAVE_CHAT_CALIFICACIONES = "chat_ai_calificaciones"


def _get_calificaciones_list(db: Session) -> list[dict]:
    """Lee la lista de calificaciones desde configuracion (JSON array)."""
    try:
        row = db.get(Configuracion, CLAVE_CHAT_CALIFICACIONES)
        if row and row.valor:
            data = json.loads(row.valor)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def _save_calificaciones_list(db: Session, items: list[dict]) -> None:
    """Persiste la lista de calificaciones en configuracion."""
    try:
        valor = json.dumps(items)
        row = db.get(Configuracion, CLAVE_CHAT_CALIFICACIONES)
        if row:
            row.valor = valor
        else:
            db.add(Configuracion(clave=CLAVE_CHAT_CALIFICACIONES, valor=valor))
        db.commit()
    except Exception:
        db.rollback()
        raise


class CalificarRequest(BaseModel):
    pregunta: str
    respuesta: str
    calificacion: int  # 5 = arriba, 1-4 = abajo


@router.post("/chat/calificar")
def post_chat_calificar(payload: CalificarRequest = Body(...), db: Session = Depends(get_db)):
    """
    Registra una calificación del usuario sobre una respuesta del Chat AI.
    Persiste en BD (configuracion.chat_ai_calificaciones). get_db para acceso a BD.
    """
    calificacion_tipo = "arriba" if (payload.calificacion or 0) >= 5 else "abajo"
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    items = _get_calificaciones_list(db)
    next_id = max((item.get("id", 0) for item in items), default=0) + 1
    item = {
        "id": next_id,
        "pregunta": (payload.pregunta or "").strip(),
        "respuesta_ai": (payload.respuesta or "").strip(),
        "calificacion": calificacion_tipo,
        "usuario_email": None,
        "procesado": False,
        "notas_procesamiento": None,
        "mejorado": False,
        "creado_en": now,
        "actualizado_en": now,
    }
    items.append(item)
    _save_calificaciones_list(db, items)
    return {"success": True, "id": next_id, "calificacion": calificacion_tipo}


@router.get("/chat/calificaciones")
def get_chat_calificaciones(
    calificacion: Optional[str] = None,
    procesado: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Lista calificaciones del Chat AI desde BD. Filtros: calificacion (arriba|abajo), procesado (true|false).
    get_db para acceso a BD.
    """
    items = _get_calificaciones_list(db)
    if calificacion and calificacion.lower() in ("arriba", "abajo"):
        items = [i for i in items if (i.get("calificacion") or "").lower() == calificacion.lower()]
    if procesado is not None:
        want = procesado.lower() == "true"
        items = [i for i in items if i.get("procesado") is want]
    return {"calificaciones": items, "total": len(items)}


class ProcesarCalificacionRequest(BaseModel):
    notas: Optional[str] = None


@router.put("/chat/calificaciones/{calificacion_id}/procesar")
def put_chat_calificacion_procesar(
    calificacion_id: int,
    payload: ProcesarCalificacionRequest = Body(...),
    db: Session = Depends(get_db),
):
    """
    Marca una calificación como procesada y opcionalmente guarda notas.
    get_db para acceso a BD.
    """
    from datetime import datetime, timezone
    items = _get_calificaciones_list(db)
    for i, item in enumerate(items):
        if item.get("id") == calificacion_id:
            items[i] = {**item, "procesado": True, "notas_procesamiento": (payload.notas or "").strip() or None, "actualizado_en": datetime.now(timezone.utc).isoformat()}
            _save_calificaciones_list(db, items)
            return {"success": True, "id": calificacion_id}
    raise HTTPException(status_code=404, detail="Calificación no encontrada")


# --- Catálogo de campos: tablas/campos desde BD y definiciones (reglas de negocio) ---

def _inspector_tablas_campos() -> dict[str, list[dict]]:
    """Obtiene tablas y columnas del esquema actual de la BD vía SQLAlchemy inspector."""
    result: dict[str, list[dict]] = {}
    try:
        insp = sa_inspect(engine)
        table_names = insp.get_table_names()
        for table in table_names:
            cols = insp.get_columns(table)
            pk = insp.get_pk_constraint(table)
            pk_cols = set((pk or {}).get("constrained_columns") or [])
            fks = insp.get_foreign_keys(table)
            fk_by_col: dict[str, Any] = {}
            for fk in fks:
                for c in (fk.get("constrained_columns") or []):
                    fk_by_col[c] = fk
            campos = []
            for col in cols:
                name = col.get("name") or ""
                tipo = str(col.get("type", ""))
                nullable = col.get("nullable", True)
                es_pk = name in pk_cols
                fk_info = fk_by_col.get(name)
                campos.append({
                    "nombre": name,
                    "tipo": tipo,
                    "nullable": nullable,
                    "es_obligatorio": not nullable,
                    "es_primary_key": es_pk,
                    "tiene_indice": es_pk or bool(fk_info),
                    "es_clave_foranea": bool(fk_info),
                    "tabla_referenciada": (fk_info or {}).get("referred_table") if fk_info else None,
                    "campo_referenciado": ((fk_info or {}).get("referred_columns") or [None])[0] if fk_info else None,
                })
            result[table] = campos
    except Exception as e:
        logger.warning("Inspector tablas-campos: %s", e)
    return result


@router.get("/tablas-campos")
def get_tablas_campos(db: Session = Depends(get_db)):
    """
    Lista tablas y campos del esquema de la BD (para Catálogo de Campos y Fine-tuning).
    El frontend usa tablas_campos, total_tablas y fecha_consulta.
    """
    from datetime import datetime, timezone
    tablas_campos = _inspector_tablas_campos()
    return {
        "tablas_campos": tablas_campos,
        "total_tablas": len(tablas_campos),
        "fecha_consulta": datetime.now(timezone.utc).isoformat(),
    }


def _definicion_to_dict(row: DefinicionCampo) -> dict:
    """Convierte fila DefinicionCampo a dict esperado por el frontend."""
    def parse_json_array(s: Optional[str]):
        if not s or not s.strip():
            return []
        try:
            out = json.loads(s)
            return out if isinstance(out, list) else []
        except Exception:
            return []
    return {
        "id": row.id,
        "tabla": row.tabla or "",
        "campo": row.campo or "",
        "definicion": row.definicion or "",
        "tipo_dato": row.tipo_dato,
        "es_obligatorio": bool(row.es_obligatorio),
        "tiene_indice": bool(row.tiene_indice),
        "es_clave_foranea": bool(row.es_clave_foranea),
        "tabla_referenciada": row.tabla_referenciada,
        "campo_referenciado": row.campo_referenciado,
        "valores_posibles": parse_json_array(row.valores_posibles),
        "ejemplos_valores": parse_json_array(row.ejemplos_valores),
        "notas": row.notas,
        "activo": bool(row.activo),
        "orden": int(row.orden or 0),
        "creado_en": row.creado_en.isoformat() if row.creado_en else "",
        "actualizado_en": row.actualizado_en.isoformat() if row.actualizado_en else "",
    }


@router.get("/definiciones-campos")
def get_definiciones_campos(db: Session = Depends(get_db)):
    """
    Lista definiciones de campos desde la tabla definiciones_campos (BD).
    Sirve al Catálogo de Campos en Configuración > AI > Catálogo de Campos.
    """
    rows = db.query(DefinicionCampo).order_by(DefinicionCampo.tabla, DefinicionCampo.orden, DefinicionCampo.campo).all()
    definiciones = [_definicion_to_dict(r) for r in rows]
    return {"definiciones": definiciones, "total": len(definiciones)}


@router.get("/definiciones-campos/tablas")
def get_definiciones_campos_tablas(db: Session = Depends(get_db)):
    """
    Lista nombres de tablas con al menos una definición (desde definiciones_campos).
    Usado por el Catálogo de Campos para el filtro por tabla.
    """
    from sqlalchemy import distinct
    tablas = db.query(distinct(DefinicionCampo.tabla)).where(DefinicionCampo.tabla.isnot(None)).all()
    lista = sorted([t[0] for t in tablas if t[0]])
    return {"tablas": lista, "total": len(lista)}


class DefinicionCampoCreate(BaseModel):
    tabla: str
    campo: str
    definicion: str
    tipo_dato: Optional[str] = None
    es_obligatorio: bool = False
    tiene_indice: bool = False
    es_clave_foranea: bool = False
    tabla_referenciada: Optional[str] = None
    campo_referenciado: Optional[str] = None
    valores_posibles: Optional[list[str]] = None
    ejemplos_valores: Optional[list[str]] = None
    notas: Optional[str] = None
    activo: bool = True
    orden: int = 0


class DefinicionCampoUpdate(BaseModel):
    definicion: Optional[str] = None
    tipo_dato: Optional[str] = None
    es_obligatorio: Optional[bool] = None
    tiene_indice: Optional[bool] = None
    es_clave_foranea: Optional[bool] = None
    tabla_referenciada: Optional[str] = None
    campo_referenciado: Optional[str] = None
    valores_posibles: Optional[list[str]] = None
    ejemplos_valores: Optional[list[str]] = None
    notas: Optional[str] = None
    activo: Optional[bool] = None
    orden: Optional[int] = None


@router.post("/definiciones-campos/sincronizar")
def post_definiciones_campos_sincronizar(db: Session = Depends(get_db)):
    """
    Sincroniza definiciones con el esquema actual de la BD.
    Crea definiciones para campos nuevos; actualiza tipo_dato/obligatorio/índice/FK
    en existentes sin sobrescribir definicion/notas si ya están rellenados.
    """
    tablas_campos = _inspector_tablas_campos()
    creados = 0
    actualizados = 0
    existentes = 0
    for tabla, campos in tablas_campos.items():
        for c in campos:
            nombre = c.get("nombre") or ""
            if not nombre:
                continue
            existente = db.query(DefinicionCampo).filter(
                DefinicionCampo.tabla == tabla,
                DefinicionCampo.campo == nombre,
            ).first()
            def_text = (c.get("definicion") or "").strip() or f"Campo {nombre} de la tabla {tabla}. Tipo: {c.get('tipo', '')}. {'Obligatorio' if c.get('es_obligatorio') else 'Opcional'}."
            if existente:
                # Actualizar solo datos técnicos; no sobrescribir definicion/notas si ya tienen contenido
                existente.tipo_dato = c.get("tipo") or existente.tipo_dato
                existente.es_obligatorio = c.get("es_obligatorio", existente.es_obligatorio)
                existente.tiene_indice = c.get("tiene_indice", existente.tiene_indice)
                existente.es_clave_foranea = c.get("es_clave_foranea", existente.es_clave_foranea)
                existente.tabla_referenciada = c.get("tabla_referenciada") or existente.tabla_referenciada
                existente.campo_referenciado = c.get("campo_referenciado") or existente.campo_referenciado
                actualizados += 1
            else:
                db.add(DefinicionCampo(
                    tabla=tabla,
                    campo=nombre,
                    definicion=def_text,
                    tipo_dato=c.get("tipo"),
                    es_obligatorio=c.get("es_obligatorio", False),
                    tiene_indice=c.get("tiene_indice", False),
                    es_clave_foranea=c.get("es_clave_foranea", False),
                    tabla_referenciada=c.get("tabla_referenciada"),
                    campo_referenciado=c.get("campo_referenciado"),
                    valores_posibles=None,
                    ejemplos_valores=None,
                    notas=None,
                    activo=True,
                    orden=0,
                ))
                creados += 1
    db.commit()
    total = creados + actualizados
    return {
        "mensaje": f"Sincronización completada: {creados} creados, {actualizados} actualizados.",
        "campos_creados": creados,
        "campos_actualizados": actualizados,
        "campos_existentes": existentes,
        "total_procesados": total,
    }


@router.post("/definiciones-campos")
def post_definiciones_campos(payload: DefinicionCampoCreate = Body(...), db: Session = Depends(get_db)):
    """Crea una definición de campo."""
    if not (payload.tabla or "").strip() or not (payload.campo or "").strip() or not (payload.definicion or "").strip():
        raise HTTPException(status_code=400, detail="Tabla, campo y definición son obligatorios")
    existente = db.query(DefinicionCampo).filter(DefinicionCampo.tabla == payload.tabla.strip(), DefinicionCampo.campo == payload.campo.strip()).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe una definición para esta tabla y campo")
    vals_pos = json.dumps(payload.valores_posibles) if payload.valores_posibles else None
    ejem_pos = json.dumps(payload.ejemplos_valores) if payload.ejemplos_valores else None
    row = DefinicionCampo(
        tabla=payload.tabla.strip(),
        campo=payload.campo.strip(),
        definicion=payload.definicion.strip(),
        tipo_dato=payload.tipo_dato or None,
        es_obligatorio=payload.es_obligatorio,
        tiene_indice=payload.tiene_indice,
        es_clave_foranea=payload.es_clave_foranea,
        tabla_referenciada=payload.tabla_referenciada or None,
        campo_referenciado=payload.campo_referenciado or None,
        valores_posibles=vals_pos,
        ejemplos_valores=ejem_pos,
        notas=payload.notas or None,
        activo=payload.activo,
        orden=payload.orden,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _definicion_to_dict(row)


@router.put("/definiciones-campos/{definicion_id}")
def put_definiciones_campos(definicion_id: int, payload: DefinicionCampoUpdate = Body(...), db: Session = Depends(get_db)):
    """Actualiza una definición de campo (parcial)."""
    row = db.get(DefinicionCampo, definicion_id)
    if not row:
        raise HTTPException(status_code=404, detail="Definición no encontrada")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k in ("valores_posibles", "ejemplos_valores") and v is not None:
            setattr(row, k, json.dumps(v))
        elif hasattr(row, k):
            setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _definicion_to_dict(row)


@router.delete("/definiciones-campos/{definicion_id}")
def delete_definiciones_campos(definicion_id: int, db: Session = Depends(get_db)):
    """Elimina una definición de campo."""
    row = db.get(DefinicionCampo, definicion_id)
    if not row:
        raise HTTPException(status_code=404, detail="Definición no encontrada")
    db.delete(row)
    db.commit()
    return {"message": "Definición eliminada"}


# --- Diccionario semántico (Configuración > AI > Diccionario semántico) ---

def _parse_json_list(s: Optional[str]):
    if not s or not s.strip():
        return []
    try:
        out = json.loads(s)
        return out if isinstance(out, list) else []
    except Exception:
        return []


def _diccionario_to_dict(row: DiccionarioSemantico) -> dict:
    return {
        "id": row.id,
        "palabra": row.palabra or "",
        "definicion": row.definicion or "",
        "categoria": row.categoria,
        "campo_relacionado": row.campo_relacionado,
        "tabla_relacionada": row.tabla_relacionada,
        "sinonimos": _parse_json_list(row.sinonimos),
        "ejemplos_uso": _parse_json_list(row.ejemplos_uso),
        "activo": bool(row.activo),
        "orden": int(row.orden or 0),
        "creado_en": row.creado_en.isoformat() if row.creado_en else "",
        "actualizado_en": row.actualizado_en.isoformat() if row.actualizado_en else "",
    }


@router.get("/diccionario-semantico")
def get_diccionario_semantico(db: Session = Depends(get_db)):
    """Lista entradas del diccionario semántico."""
    rows = db.query(DiccionarioSemantico).order_by(DiccionarioSemantico.orden, DiccionarioSemantico.palabra).all()
    entradas = [_diccionario_to_dict(r) for r in rows]
    return {"entradas": entradas, "total": len(entradas)}


@router.get("/diccionario-semantico/categorias")
def get_diccionario_semantico_categorias(db: Session = Depends(get_db)):
    """Lista categorías distintas del diccionario."""
    from sqlalchemy import distinct
    cats = db.query(distinct(DiccionarioSemantico.categoria)).where(DiccionarioSemantico.categoria.isnot(None)).all()
    lista = sorted([c[0] for c in cats if c[0]])
    return {"categorias": lista, "total": len(lista)}


class DiccionarioSemanticoCreate(BaseModel):
    palabra: str
    definicion: str
    categoria: Optional[str] = None
    campo_relacionado: Optional[str] = None
    tabla_relacionada: Optional[str] = None
    sinonimos: Optional[list[str]] = None
    ejemplos_uso: Optional[list[str]] = None
    activo: bool = True
    orden: int = 0


class DiccionarioSemanticoUpdate(BaseModel):
    palabra: Optional[str] = None
    definicion: Optional[str] = None
    categoria: Optional[str] = None
    campo_relacionado: Optional[str] = None
    tabla_relacionada: Optional[str] = None
    sinonimos: Optional[list[str]] = None
    ejemplos_uso: Optional[list[str]] = None
    activo: Optional[bool] = None
    orden: Optional[int] = None


@router.post("/diccionario-semantico")
def post_diccionario_semantico(payload: DiccionarioSemanticoCreate = Body(...), db: Session = Depends(get_db)):
    """Crea entrada en el diccionario semántico."""
    if not (payload.palabra or "").strip() or not (payload.definicion or "").strip():
        raise HTTPException(status_code=400, detail="Palabra y definición son obligatorios")
    sinon = json.dumps(payload.sinonimos) if payload.sinonimos else None
    ejem = json.dumps(payload.ejemplos_uso) if payload.ejemplos_uso else None
    row = DiccionarioSemantico(
        palabra=payload.palabra.strip(),
        definicion=payload.definicion.strip(),
        categoria=payload.categoria or None,
        campo_relacionado=payload.campo_relacionado or None,
        tabla_relacionada=payload.tabla_relacionada or None,
        sinonimos=sinon,
        ejemplos_uso=ejem,
        activo=payload.activo,
        orden=payload.orden,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _diccionario_to_dict(row)


@router.put("/diccionario-semantico/{entrada_id}")
def put_diccionario_semantico(entrada_id: int, payload: DiccionarioSemanticoUpdate = Body(...), db: Session = Depends(get_db)):
    """Actualiza entrada del diccionario semántico."""
    row = db.get(DiccionarioSemantico, entrada_id)
    if not row:
        raise HTTPException(status_code=404, detail="Entrada no encontrada")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k in ("sinonimos", "ejemplos_uso") and v is not None:
            setattr(row, k, json.dumps(v))
        elif hasattr(row, k):
            setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _diccionario_to_dict(row)


@router.delete("/diccionario-semantico/{entrada_id}")
def delete_diccionario_semantico(entrada_id: int, db: Session = Depends(get_db)):
    """Elimina entrada del diccionario semántico."""
    row = db.get(DiccionarioSemantico, entrada_id)
    if not row:
        raise HTTPException(status_code=404, detail="Entrada no encontrada")
    db.delete(row)
    db.commit()
    return {"message": "Entrada eliminada"}


@router.post("/diccionario-semantico/procesar")
def post_diccionario_semantico_procesar(payload: dict = Body(...)):
    """Procesa entrada con IA para mejorar definición (stub)."""
    return {"mensaje": "Procesamiento con IA no implementado aún", "definicion_mejorada": payload.get("definicion", "")}
