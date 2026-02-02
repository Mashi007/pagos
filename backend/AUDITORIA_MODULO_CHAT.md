# Auditoría integral del módulo Chat (AI)

**Fecha:** 2025-02-02  
**Alcance:** Backend `app/api/v1/endpoints/configuracion_ai.py`, uso de `get_db` y acceso a BD para respuestas del chat.

---

## 1. Estado inicial (antes de la auditoría)

### 1.1 Uso de `get_db`

| Endpoint | Método | `get_db` antes | Notas |
|----------|--------|----------------|--------|
| `/configuracion` | GET | ✅ `db: Session = Depends(get_db)` | Config AI desde BD |
| `/configuracion` | PUT | ✅ | Persiste config en BD |
| `/chat` | POST | ❌ No | Solo enviaba pregunta a OpenRouter, sin BD |
| `/probar` | POST | ❌ No | Sin carga de config desde BD |
| `/documentos` | GET | ❌ No | Lista vacía sin BD |
| `/chat/calificar` | POST | ❌ No implementado | Frontend lo llama; 404 |
| `/chat/calificaciones` | GET | ❌ No implementado | Frontend CalificacionesChatTab; 404 |
| `/chat/calificaciones/{id}/procesar` | PUT | ❌ No implementado | Frontend; 404 |

### 1.2 Hallazgos

1. **POST /chat** no usaba `get_db`. La configuración AI se lee de un caché global (`_ai_config_stub`) que se actualiza en GET/PUT configuracion; si un request llega sin haber pasado antes por GET config, el stub podría estar desactualizado. Además, el frontend anuncia que el Chat AI responde "preguntas sobre la base de datos del sistema", pero el backend no consultaba la BD para construir contexto (clientes, préstamos, cuotas, etc.), por lo que la IA respondía solo con conocimiento general, no con datos reales.

2. **POST /probar** no inyectaba `get_db`, por lo que no cargaba config desde BD de forma explícita en ese request.

3. **GET /documentos** devolvía lista vacía sin tocar BD; por consistencia y futura extensión debe usar `get_db`.

4. **Calificaciones:** Los endpoints `POST /chat/calificar`, `GET /chat/calificaciones` y `PUT /chat/calificaciones/{id}/procesar` no existían en backend. El frontend (ChatAI.tsx, CalificacionesChatTab.tsx) ya los consume; sin ellos hay 404/503.

---

## 2. Cambios realizados (post-auditoría)

### 2.1 Todos los endpoints del módulo Chat con `get_db`

- **POST /chat:** `db: Session = Depends(get_db)`. Se llama a `_load_ai_config_from_db(db)` al inicio. Se construye un **contexto de BD** (resumen de tablas: conteos de clientes, préstamos, cuotas, pagos, etc.) y se inyecta en el system prompt enviado a OpenRouter, para que las respuestas del chat puedan basarse en datos reales.
- **POST /probar:** `db: Session = Depends(get_db)` y `_load_ai_config_from_db(db)`.
- **GET /documentos:** `db: Session = Depends(get_db)` (por ahora devuelve lista vacía; preparado para futura persistencia en BD).
- **POST /chat/calificar:** Implementado con `get_db`. Persiste la calificación en la tabla `configuracion` (clave `chat_ai_calificaciones`, valor JSON array).
- **GET /chat/calificaciones:** Implementado con `get_db`. Lee desde `configuracion` y filtra por query params `calificacion`, `procesado`.
- **PUT /chat/calificaciones/{id}/procesar:** Implementado con `get_db`. Actualiza el ítem en el JSON por `id` y marca como procesado con notas.

### 2.2 Contexto de BD para respuestas del chat (estructura para respuestas rápidas y solo datos get_db)

En **POST /chat** se usa una estructura pensada para respuestas rápidas y uso explícito solo de datos de get_db:

- **CHAT_SYSTEM_PROMPT_INSTRUCCIONES:** prompt del sistema que exige al modelo usar ÚNICAMENTE los datos del bloque "Datos disponibles (get_db)", responder con cualquier dato disponible, ser conciso y no inventar cifras.
- **_build_chat_context(db):** una sola ronda de consultas agregadas (count) a Cliente, Prestamo, Cuota; salida compacta (menos tokens = más rápido).
- **_build_chat_system_prompt(db):** arma el system prompt completo: instrucciones + bloque "Datos disponibles (get_db):" + contexto. El modelo debe responder solo con datos disponibles ahí.
- **OPENROUTER_TIMEOUT:** timeout acotado (45 s) para no bloquear.

- **Tablas/consultas usadas:** Cliente, Prestamo, Cuota vía `get_db`; formato texto compacto en el system message.

---

## 3. Persistencia de calificaciones

- **Almacenamiento:** tabla `configuracion`, clave `chat_ai_calificaciones`, valor = JSON array de objetos con: `id`, `pregunta`, `respuesta_ai`, `calificacion` ("arriba"|"abajo"), `usuario_email`, `procesado`, `notas_procesamiento`, `mejorado`, `creado_en`, `actualizado_en`.
- **POST /chat/calificar:** recibe `pregunta`, `respuesta`, `calificacion` (1–5); internamente se normaliza a "arriba" (5) o "abajo" (1–4). Se añade al array y se persiste con `get_db`.
- **GET /chat/calificaciones:** query params `calificacion`, `procesado`; devuelve `{ calificaciones: [...], total: N }` compatible con CalificacionesChatTab.
- **PUT /chat/calificaciones/{id}/procesar:** body `{ notas?: string }`; actualiza el ítem con ese `id` y marca `procesado: true`, `notas_procesamiento`, `actualizado_en`.

No se crea tabla nueva; se reutiliza `configuracion` para evitar migraciones. Si el volumen crece, se puede migrar a una tabla dedicada más adelante.

---

## 4. Resumen de cumplimiento

| Requisito | Estado |
|-----------|--------|
| Todos los endpoints del módulo Chat con `get_db` | ✅ Cumplido |
| POST /chat accede a BD para config y contexto de respuestas | ✅ Cumplido |
| Calificar y calificaciones implementados con BD | ✅ Cumplido |
| Documentos preparado para BD (get_db) | ✅ Cumplido |

---

## 5. Archivos modificados

- **`app/api/v1/endpoints/configuracion_ai.py`**
  - `get_db` en POST /chat, POST /probar, GET /documentos.
  - Función auxiliar para construir contexto de BD desde `db`.
  - Inyección de contexto en el flujo de POST /chat (system message).
  - Nuevos endpoints: POST /chat/calificar, GET /chat/calificaciones, PUT /chat/calificaciones/{id}/procesar, todos con `get_db` y persistencia/lectura en `configuracion`.
