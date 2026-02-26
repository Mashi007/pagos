# Mejoras aplicadas (2026-02-26)

Resumen de cambios realizados en backend y frontend.

---

## 1. Logging de requests (backend)

**Archivo:** `backend/app/main.py`

- El middleware `RequestLogMiddleware` ahora:
  - Registra `method`, `path`, `status`, `elapsed_ms` en cada request.
  - Escribe **WARNING** (en lugar de INFO) cuando:
    - `status >= 500` (error de servidor), o
    - `elapsed_ms >= 5000` (más de 5 segundos).
  - El mensaje de WARNING incluye el sufijo `(slow_or_error)` para poder filtrar en Render.

**Objetivo:** Poder localizar en los logs de Render qué rutas devuelven 500 o son lentas sin revisar todas las líneas.

---

## 2. Reporte contable – parámetro años (backend)

**Archivo:** `backend/app/api/v1/endpoints/reportes/reportes_contable.py`

- El endpoint `GET /api/v1/reportes/exportar/contable` ahora:
  - Recibe el objeto `Request` y, si el query param `anos` no viene informado, usa `request.query_params.get("anos") or request.query_params.get("años")`.
  - Así se aceptan tanto `?anos=2025` como `?años=2025` (o `a%C3%B1os=2025`), evitando 500 cuando el frontend enviaba la clave con ñ.

---

## 3. Reporte contable – UniqueViolation en cache (backend)

**Archivo:** `backend/app/api/v1/endpoints/reportes/reportes_contable.py`

- En `refresh_cache_ultimos_7_dias`:
  - Se **deduplican** las filas por `cuota_id` antes de insertar (`by_cuota = {f["cuota_id"]: f for f in filas}`).
  - Se **eliminan** del cache los registros con `cuota_id in (cuota_ids a insertar)` y luego se insertan las filas.
  - Se evita el error `UniqueViolation: duplicate key value violates unique constraint "reporte_contable_cache_cuota_id_key"`.

---

## 4. Frontend – comentario en reporteService

**Archivo:** `frontend/src/services/reporteService.ts`

- Se añadió un comentario junto a `baseUrl` indicando que la API espera el query param **`anos`** (sin ñ) y **`meses_list`** en cartera/pagos/morosidad/asesores, para evitar volver a enviar `años` por error.

---

## Despliegue

- **Backend:** Desplegar los cambios en `main.py` y `reportes_contable.py` en Render para que entren en vigor el logging mejorado, el fallback del parámetro años y la corrección del cache contable.
- **Frontend:** Reconstruir y desplegar para que el comentario quede en el código; el envío de `anos` ya estaba correcto en el repo.
