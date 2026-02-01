# Revisión módulo Chat AI

**Fecha:** 2026-02-01  
**Alcance:** Endpoints backend, conexión a base de datos, caracteres especiales en frontend.

---

## 1. Endpoints usados por el frontend (Chat AI)

| Método | Ruta | Uso en frontend |
|--------|------|------------------|
| GET | `/api/v1/configuracion/ai/configuracion` | Verificar si AI está configurado (token, activo) |
| POST | `/api/v1/configuracion/ai/chat` | Enviar pregunta y recibir respuesta (consulta BD + OpenAI) |
| POST | `/api/v1/configuracion/ai/chat/calificar` | Registrar calificación (arriba/abajo) de una respuesta |

Otros endpoints AI usados desde Configuración > AI y Calificaciones:
- GET/PUT `/api/v1/configuracion/ai/configuracion`
- GET/POST `/api/v1/configuracion/ai/chat/calificaciones`
- PATCH `/api/v1/configuracion/ai/chat/calificaciones/{id}/procesar`

---

## 2. Estado en backend

**No implementado.** El router actual de configuración (`backend/app/api/v1/endpoints/configuracion.py`) solo expone:

- `GET /configuracion/general`
- `GET /configuracion/logo/{filename}`

No existe rama `/configuracion/ai/*`. Por tanto:

- Las llamadas desde `ChatAI.tsx` y desde Configuración > AI reciben **404** (o error de red si el backend no tiene esa ruta).
- No hay conexión a base de datos para el Chat AI en el backend: el módulo que debería ejecutar consultas SQL (o usar un servicio que consulte la BD), llamar a OpenAI y devolver la respuesta **no está implementado**.

Para implementar el módulo Chat AI en backend haría falta:

1. **Nuevo router** (p. ej. `configuracion_ai.py` o subrouter bajo `configuracion`) con prefijo `/configuracion/ai`.
2. **Endpoints:**
   - `GET /configuracion/ai/configuracion` — devolver configuración AI (openai_api_key enmascarado, activo, etc.) desde BD o env.
   - `POST /configuracion/ai/chat` — recibir `pregunta`, validar, ejecutar consultas a la BD según el prompt/reglas, llamar a OpenAI, devolver `{ success, respuesta, pregunta, tokens_usados?, modelo_usado?, tiempo_respuesta? }`.
   - `POST /configuracion/ai/chat/calificar` — guardar en BD (pregunta, respuesta, calificación 1–5).
   - `GET /configuracion/ai/chat/calificaciones` (paginado) y `PATCH .../calificaciones/{id}/procesar` si se usan en frontend.
3. **Conexión a base de datos:** uso del mismo cliente/engine que el resto de la app (SQLAlchemy/session) para:
   - Leer configuración AI.
   - Ejecutar consultas de solo lectura para “contexto” que se pasa al LLM (tablas, esquema, o datos agregados).
   - Persistir calificaciones del chat en una tabla dedicada (p. ej. `chat_ai_calificaciones`).

---

## 3. Caracteres especiales en frontend (Chat AI)

En `frontend/src/pages/ChatAI.tsx` se detectaron cadenas con **mojibake** (UTF-8 interpretado como Latin-1):

- `Â¡` en lugar de `¡` (mensaje de bienvenida).
- Emojis/símbolos corruptos: `âœ…`, `âï¸`, `ðŸ'¡`, `âš ï¸`, `âŒ`, `âœ"` en mensajes de error y en etiquetas de calificación.

**Acción:** Se han corregido en `ChatAI.tsx` reemplazando por los caracteres Unicode correctos (¡, ✅, ⏱️, 💡, ⚠️, ❌, ✔). Para el resto del frontend puede ejecutarse `frontend/fix-encoding.ps1` (PowerShell) para aplicar las reglas de corrección ya definidas.

---

## 4. Resumen

| Aspecto | Estado |
|---------|--------|
| Endpoints Chat AI en backend | No implementados |
| Conexión a BD para Chat AI | No existe (módulo no implementado) |
| Caracteres especiales en ChatAI.tsx | Corregidos en este revisión |
| Timeout en api.ts para `/configuracion/ai/chat` | Ya configurado (5 min) |

Implementar el backend del Chat AI implica crear la rama `/configuracion/ai/*`, con acceso a BD para configuración, contexto de consultas y tabla de calificaciones, e integración con OpenAI.
