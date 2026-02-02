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
import urllib.request
import urllib.error
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session

import logging

from app.core.config import settings
from app.core.database import get_db, engine
from app.models.configuracion import Configuracion
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.cuota import Cuota
from app.models.definicion_campo import DefinicionCampo
from sqlalchemy import func
from sqlalchemy import inspect as sa_inspect

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
    Construye un resumen compacto de la BD (get_db) para el system prompt.
    Incluye conteos y totales (financiamiento, cuotas) para que el modelo pueda
    responder preguntas como "total de financiamiento", "créditos aprobados", etc.
    """
    lines: list[str] = []
    try:
        total_clientes = db.query(func.count(Cliente.id)).scalar() or 0
        total_prestamos = db.query(func.count(Prestamo.id)).scalar() or 0
        prestamos_aprobados = db.query(func.count(Prestamo.id)).filter(Prestamo.estado == "APROBADO").scalar() or 0
        # Total de financiamiento: suma de total_financiamiento (aprobados y total)
        total_financiamiento_aprobado = db.query(func.coalesce(func.sum(Prestamo.total_financiamiento), 0)).filter(
            Prestamo.estado == "APROBADO"
        ).scalar() or 0
        total_financiamiento_todos = db.query(func.coalesce(func.sum(Prestamo.total_financiamiento), 0)).scalar() or 0
        total_cuotas = db.query(func.count(Cuota.id)).scalar() or 0
        cuotas_pagadas_count = db.query(func.count(Cuota.id)).filter(Cuota.fecha_pago.isnot(None)).scalar() or 0
        cuotas_pendientes = total_cuotas - cuotas_pagadas_count
        suma_cuotas_pagadas = db.query(func.coalesce(func.sum(Cuota.monto), 0)).filter(
            Cuota.fecha_pago.isnot(None)
        ).scalar() or 0
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
    except Exception:
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
    Arma el system prompt completo: instrucciones + preguntas habituales -> campos
    + bloque 'Datos disponibles (get_db)'. Así el modelo sabe qué dato usar para cada pregunta típica.
    """
    datos_bd = _build_chat_context(db)
    preguntas_block = _get_preguntas_habituales_block(db)
    return (
        f"{CHAT_SYSTEM_PROMPT_INSTRUCCIONES}\n\n"
        f"{preguntas_block}\n\n"
        f"Datos disponibles (get_db):\n{datos_bd}"
    )


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


# Timeout para llamadas a OpenRouter (segundos). Acotado para respuestas rápidas.
OPENROUTER_TIMEOUT = 45


def _call_openrouter(messages: list[dict], model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 1000) -> dict:
    """Llama a OpenRouter API. La clave solo se usa aquí desde settings."""
    key = _get_openrouter_key()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="AI no configurada: ingresa tu API Key de OpenRouter en Configuración > Inteligencia Artificial (o configura OPENROUTER_API_KEY en variables de entorno del servidor). Obtén la clave en https://openrouter.ai/keys",
        )
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
        with urllib.request.urlopen(req, timeout=OPENROUTER_TIMEOUT) as resp:
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
        valor_json = json.dumps(payload_bd)
        if row:
            row.valor = valor_json
        else:
            db.add(Configuracion(clave=CLAVE_AI, valor=valor_json))
        db.commit()
    except Exception:
        db.rollback()
    return get_ai_configuracion(db)


class ChatRequest(BaseModel):
    pregunta: str


@router.post("/chat")
def post_ai_chat(payload: ChatRequest = Body(...), db: Session = Depends(get_db)):
    """
    Chat completions vía OpenRouter. Usa get_db para cargar config y para inyectar
    'Datos disponibles (get_db)' en el system prompt. El prompt exige respuestas
    rápidas y solo con datos disponibles en ese bloque.
    """
    _load_ai_config_from_db(db)
    pregunta = (payload.pregunta or "").strip()
    if not pregunta:
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía")
    if _ai_config_stub.get("activo", "true").lower() != "true":
        raise HTTPException(status_code=400, detail="El servicio AI está desactivado en configuración")
    system_prompt = _build_chat_system_prompt(db)
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
def post_ai_probar(payload: ProbarRequest = Body(...), db: Session = Depends(get_db)):
    """Prueba la conexión con OpenRouter y devuelve la respuesta para el chat de prueba. Carga config desde BD."""
    _load_ai_config_from_db(db)
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
    Lista tablas y campos del esquema de la BD (para Catálogo de Campos).
    El frontend usa tablas_campos y total_tablas.
    """
    tablas_campos = _inspector_tablas_campos()
    return {"tablas_campos": tablas_campos, "total_tablas": len(tablas_campos)}


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
