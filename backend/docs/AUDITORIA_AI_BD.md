# Auditoría: integración AI ↔ BD (consultas y mejores prácticas)

## Objetivo

Garantizar que el mecanismo de aprendizaje y las consultas de la IA a la base de datos sigan buenas prácticas: menor tiempo de conexión, menos round-trips, no retener conexiones durante I/O externa (OpenRouter) y acceso correcto a tablas con trazabilidad ante fallos.

---

## Hallazgos y correcciones aplicadas

### 1. Múltiples consultas por request (resuelto)

- **Problema**: `_build_chat_context(db)` ejecutaba **9 consultas** separadas (count clientes, count préstamos, count aprobados, sum financiamiento aprobado, sum financiamiento todos, count cuotas, count cuotas pagadas, sum montos cuotas pagadas) con `db.query(...).scalar()` (API antigua SQLAlchemy 1.x).
- **Impacto**: Más round-trips a la BD, mayor tiempo con la conexión abierta y más riesgo de timeout o bloqueos.
- **Solución**: Una **única consulta** con subconsultas escalares (SQLAlchemy 2: `select(...scalar_subquery().label(...), ...)` + `db.execute(stmt).first()`). Un solo round-trip para todo el contexto.

### 2. Conexión retenida durante la llamada a OpenRouter (resuelto)

- **Problema**: En `POST /chat`, la sesión inyectada por `Depends(get_db)` se mantenía abierta durante toda la petición, **incluidos los hasta 45 segundos** de la llamada HTTP a OpenRouter. Eso retenía un slot del pool (pool_size=5) y podía provocar lentitud o “no accede a tablas” por agotamiento de conexiones.
- **Solución**:
  - **Chat**: Se usa una **sesión de corta duración** (`SessionLocal()`) solo para cargar config y construir el contexto; se cierra en un `finally` **antes** de llamar a `_call_openrouter()`. El endpoint ya no recibe `db: Depends(get_db)` para el flujo de chat.
  - **Probar**: Igual: sesión corta para `_load_ai_config_from_db(session)`, se cierra, y después se llama a OpenRouter.
- **Resultado**: Durante la llamada a OpenRouter no se mantiene ninguna conexión de BD abierta.

### 3. Trazabilidad cuando no se accede a las tablas (resuelto)

- **Problema**: Si fallaba la lectura de BD, solo se añadía "(error al cargar datos)" al prompt, sin log.
- **Solución**: En `_build_chat_context` se usa `logger.exception(...)` en el `except`, indicando que el error es al cargar contexto desde BD (tablas clientes/prestamos/cuotas). Así se puede diagnosticar “demora” o “no accede a tablas” en logs.

### 4. Estilo SQLAlchemy 2 y consistencia

- **Antes**: Uso de `db.query(...).scalar()` en el módulo AI.
- **Ahora**: Uso de `select()` + `scalar_subquery()` + `db.execute(stmt).first()`, alineado con el resto del proyecto (pagos, reportes, auditoría, etc.).

---

## Buenas prácticas aplicadas

| Práctica | Implementación |
|----------|----------------|
| **Mínimos round-trips** | Una sola consulta agregada para el contexto del chat (8 métricas en 1 ejecución). |
| **No retener conexión en I/O externa** | Sesión corta para config + contexto; se cierra antes de llamar a OpenRouter. |
| **Sesión por request donde aplica** | Endpoints que solo leen/escriben BD siguen usando `Depends(get_db)`. |
| **Logging en fallos de BD** | `logger.exception` en `_build_chat_context` cuando falla el acceso a tablas. |
| **API SQLAlchemy 2** | `select()` + `execute()` en lugar de `query()` en el flujo AI-BD y en ai_training (métricas, estadísticas, preparar). |
| **Pool de conexiones** | `database.py`: `pool_pre_ping=True`, `pool_size=5`, `max_overflow=10`; no se bloquea durante OpenRouter. |
| **Timeout de consulta** | `SET LOCAL statement_timeout = 10000` (10 s) en la consulta de contexto del chat para no colgar la conexión. |

---

## Flujo actual (chat)

1. Cliente llama a `POST /api/v1/ai/configuracion/chat` (o ruta equivalente con prefijo).
2. Backend abre una sesión corta `SessionLocal()`.
3. En esa sesión: `_load_ai_config_from_db(session)`, `_build_chat_context(session)` (1 consulta), `_get_preguntas_habituales_block(session)`.
4. Se cierra la sesión (`session.close()`).
5. Se arma el system prompt en memoria y se llama a `_call_openrouter(messages)` (sin usar BD).
6. Se devuelve la respuesta al cliente.

Ninguna conexión de BD queda retenida durante el paso 5.

---

## Otros puntos revisados

- **Configuración AI (GET/PUT)** y **calificaciones, definiciones, diccionario semántico**: Siguen usando `Depends(get_db)` porque son operaciones cortas de lectura/escritura en la misma request, sin llamadas externas largas.
- **RAG / documentos / embeddings**: Por ahora el módulo devuelve lista vacía o stubs; cuando se implemente persistencia en BD, conviene aplicar el mismo patrón: sesión corta para leer contexto y cerrar antes de llamadas a modelos externos.
- **AI training (conversaciones, métricas)**: Refactor aplicado: `_metricas_from_db` y `get_estadisticas_feedback` usan una o pocas consultas (select + scalar_subquery / group_by) en lugar de muchas; `post_fine_tuning_preparar` solo lee `id` y `feedback` necesarios. Fine-tuning y RAG siguen siendo stubs; cuando se implementen llamadas externas largas, usar sesión corta para BD y cerrar antes de la I/O externa.

### 5. Timeout en consulta de contexto (aplicado)

- **Problema**: Si la BD tarda mucho, la consulta de contexto podía colgar y retener la conexión.
- **Solución**: En `_build_chat_context` se ejecuta `SET LOCAL statement_timeout = 10000` (10 s) antes de la consulta agregada. Solo afecta a la transacción actual (PostgreSQL revierte al terminar).

---

## Cómo verificar

1. **Logs**: Si el chat devuelve "(error al cargar datos)", revisar el log con mensaje `"AI chat: error al cargar contexto desde BD"` para ver la excepción (permisos, tablas inexistentes, timeout, etc.).
2. **Pool**: Bajo carga concurrente de chat, comprobar que no aparezcan timeouts de conexión; con la sesión corta no debería agotarse el pool durante la llamada a OpenRouter.
3. **Rendimiento**: El tiempo hasta “primer byte” del chat debería depender sobre todo de OpenRouter; la parte BD queda reducida a una sola consulta y una sesión breve.
