# Auditoría completa: Chat AI (https://rapicredit.onrender.com/pagos/chat-ai)

**Fecha:** 2025-02-19  
**Alcance:** Endpoints, configuración de conexión BD, mecanismos de respuesta rápida.

---

## 1. Resumen ejecutivo

| Área | Estado | Observaciones |
|------|--------|---------------|
| **Endpoints** | ✅ Correctos | Todos implementados con `get_db` donde aplica |
| **Configuración BD** | ✅ Correcta | `DATABASE_URL` desde `.env`, pool configurado |
| **Respuesta rápida** | ✅ Optimizado | Sesión corta, 1 consulta BD, timeout 45s OpenRouter |
| **Seguridad** | ⚠️ Revisar | Endpoints protegidos con auth; API key nunca expuesta |

---

## 2. Endpoints del módulo Chat AI

### 2.1 Rutas completas (base: `/api/v1/configuracion/ai`)

| Método | Ruta | Descripción | `get_db` | Auth |
|--------|------|-------------|----------|------|
| GET | `/configuracion` | Config AI (modelo, temperatura, activo) | ✅ | ✅ |
| PUT | `/configuracion` | Actualizar config AI | ✅ | ✅ |
| POST | `/chat` | Enviar pregunta → OpenRouter | N/A* | ✅ |
| POST | `/probar` | Probar conexión OpenRouter | N/A* | ✅ |
| GET | `/documentos` | Lista documentos RAG (stub vacío) | ✅ | ✅ |
| POST | `/chat/stream` | Chat con streaming (SSE) | N/A* | ✅ |
| POST | `/chat/calificar` | Registrar calificación (👍/👎) | ✅ | ✅ |
| GET | `/chat/calificaciones` | Listar calificaciones con filtros | ✅ | ✅ |
| PUT | `/chat/calificaciones/{id}/procesar` | Marcar como procesada | ✅ | ✅ |
| GET | `/prompt` | Prompt personalizado | ✅ | ✅ |
| PUT | `/prompt` | Guardar prompt personalizado | ✅ | ✅ |
| GET | `/tablas-campos` | Catálogo de tablas/campos BD | ✅ | ✅ |
| GET | `/definiciones-campos` | Definiciones de campos | ✅ | ✅ |
| GET | `/diccionario-semantico` | Diccionario semántico | ✅ | ✅ |

\* **POST /chat** y **POST /probar** no usan `Depends(get_db)` porque emplean una **sesión de corta duración** (`SessionLocal()`) que se cierra **antes** de llamar a OpenRouter. Esto evita retener conexiones de BD durante la I/O externa (hasta 45 s).

### 2.2 URL completa del endpoint principal

```
POST https://rapicredit.onrender.com/api/v1/configuracion/ai/chat
```

**Body:**
```json
{ "pregunta": "¿Cuántos clientes hay?" }
```

**Respuesta esperada:**
```json
{
  "success": true,
  "respuesta": "...",
  "pregunta": "¿Cuántos clientes hay?",
  "tokens_usados": 123,
  "modelo_usado": "openai/gpt-4o-mini"
}
```

### 2.3 Flujo frontend → backend

1. **Frontend:** `ChatAI.tsx` → `apiClient.post('/api/v1/configuracion/ai/chat', { pregunta })`
2. **Proxy:** `server.js` redirige `/api/*` a `API_BASE_URL` (backend en Render)
3. **Backend:** FastAPI recibe en `/api/v1/configuracion/ai/chat` (router: `configuracion` + sub-router `ai`)

---

## 3. Configuración de conexión a BD

### 3.1 Origen de la URL

| Variable | Origen | Uso |
|----------|--------|-----|
| `DATABASE_URL` | `.env` o variables de entorno (Render) | Obligatoria en `app/core/config.py` |
| `SECRET_KEY` | `.env` | Obligatoria para JWT |

**Código relevante** (`app/core/config.py`):
```python
DATABASE_URL: str = Field(..., description="URL de conexión a PostgreSQL")
```

### 3.2 Pool de conexiones (`app/core/database.py`)

```python
engine = create_engine(
    _db_url,
    pool_pre_ping=True,   # Verifica conexión antes de usar
    pool_size=5,
    max_overflow=10,
)
```

- **pool_size=5:** 5 conexiones persistentes
- **max_overflow=10:** hasta 15 conexiones bajo carga
- **pool_pre_ping:** evita usar conexiones muertas (útil en Render con spin-down)

### 3.3 Conversión postgres:// → postgresql://

```python
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)
```

Render suele devolver `postgres://`; SQLAlchemy 2 requiere `postgresql://`.

### 3.4 Health check de BD

| Endpoint | Descripción |
|----------|-------------|
| `GET /health` | Estado básico (sin BD) |
| `GET /health/db` | Ejecuta `SELECT 1`; devuelve 503 si falla |

**Verificación:**
```
GET https://rapicredit.onrender.com/health/db
→ {"status": "healthy", "database": "connected"}
```

---

## 4. Mecanismos de respuesta rápida

### 4.1 Sesión de corta duración (no retener conexión durante OpenRouter)

**Problema resuelto:** Antes, la sesión `Depends(get_db)` permanecía abierta durante toda la petición, **incluidos los hasta 45 segundos** de la llamada a OpenRouter (retenía un slot del pool).

**Solución actual** (`configuracion_ai.py`):

```python
def _build_chat_system_prompt_with_short_session() -> str:
    session = SessionLocal()
    try:
        _load_ai_config_from_db(session)
        return _build_chat_system_prompt(session)
    finally:
        session.close()  # ← Se cierra ANTES de llamar a OpenRouter
```

**Flujo POST /chat:**
1. Abrir sesión corta
2. Cargar config y construir contexto desde BD
3. Cerrar sesión
4. Llamar a `_call_openrouter(messages)` (sin BD abierta)
5. Devolver respuesta

### 4.2 Una sola consulta para el contexto

**Antes:** 9 consultas separadas (count clientes, préstamos, cuotas, etc.).

**Ahora:** `_build_chat_context(db)` ejecuta **una única consulta** con subconsultas escalares (SQLAlchemy 2):

```python
stmt = select(
    select(func.count(Cliente.id)).scalar_subquery().label("total_clientes"),
    select(func.count(Prestamo.id)).scalar_subquery().label("total_prestamos"),
    # ... 8 métricas en 1 round-trip
)
row = db.execute(stmt).first()
```

### 4.3 Timeout en consulta de contexto

```python
CONTEXTO_AI_STATEMENT_TIMEOUT_MS = 10_000  # 10 segundos
db.execute(text(f"SET LOCAL statement_timeout = {CONTEXTO_AI_STATEMENT_TIMEOUT_MS}"))
```

Si la BD tarda más de 10 s, PostgreSQL cancela la consulta y no se cuelga la conexión.

### 4.4 Timeout OpenRouter

```python
# openrouter_client.py
OPENROUTER_TIMEOUT = 45  # segundos
with urllib.request.urlopen(req, timeout=OPENROUTER_TIMEOUT) as resp:
    return json.loads(resp.read().decode())
```

### 4.5 Prompt optimizado para respuestas rápidas

- **CHAT_SYSTEM_PROMPT_INSTRUCCIONES:** Instruye al modelo a usar **solo** los datos del bloque "Datos disponibles (get_db)", ser conciso y no inventar cifras.
- **Contexto expandido:** Incluye fecha_actual, mora (cuotas_en_mora, monto_cuotas_en_mora, prestamos_con_mora), prestamos_draft, muestra de clientes_en_mora.
- **Lookup dinámico por cédula:** Si la pregunta incluye una cédula (V12345678, 12345678, etc.), se busca el cliente y se añade `cliente_buscado` al contexto.
- **Preguntas habituales:** Mapeo pregunta → campo para respuestas más directas.

---

## 5. Tablas y datos usados por el Chat

| Tabla | Uso |
|-------|-----|
| `configuracion` | Clave `configuracion_ai` (modelo, temperatura, API key, prompt) |
| `configuracion` | Clave `chat_ai_calificaciones` (JSON array de calificaciones) |
| `configuracion` | Clave `preguntas_habituales_ai` (opcional) |
| `clientes` | Count, muestra en mora, lookup por cédula |
| `prestamos` | Count por estado (APROBADO, DRAFT), sum total_financiamiento |
| `cuotas` | Count, sum montos pagados, cuotas en mora, monto en mora |

---

## 6. Recomendaciones

### 6.1 Cumplidas ✅

- [x] Todos los endpoints del módulo Chat con acceso a BD donde aplica
- [x] POST /chat no retiene conexión durante OpenRouter
- [x] Una sola consulta para el contexto
- [x] Timeout en consulta de contexto (10 s)
- [x] Timeout OpenRouter (45 s)
- [x] Logging en fallos de BD (`logger.exception` en `_build_chat_context`)
- [x] API key nunca expuesta al frontend
- [x] **Caché de contexto:** TTL 90 s, invalidación al cambiar config/prompt
- [x] **Streaming:** POST `/chat/stream` con SSE; frontend con toggle
- [x] **Rate limiting:** 10 peticiones/minuto por usuario (429 si excede)
- [x] **Métricas:** Log `context_ms`, `cache_hit`, `openrouter_ms`, `total_ms`

---

## 7. Verificación rápida

```bash
# Health BD
curl https://rapicredit.onrender.com/health/db

# Chat (requiere token JWT)
curl -X POST https://rapicredit.onrender.com/api/v1/configuracion/ai/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"pregunta": "¿Cuántos clientes hay?"}'
```

---

## 8. Referencias

- `backend/app/api/v1/endpoints/configuracion_ai.py` — Implementación principal
- `backend/app/core/database.py` — Pool y sesiones
- `backend/app/core/openrouter_client.py` — Cliente OpenRouter
- `backend/AUDITORIA_MODULO_CHAT.md` — Auditoría previa (get_db, calificaciones)
- `backend/docs/AUDITORIA_AI_BD.md` — Buenas prácticas AI-BD aplicadas
