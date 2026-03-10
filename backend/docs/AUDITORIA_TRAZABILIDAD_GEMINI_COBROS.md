# Auditoría de trazabilidad: Gemini conectado al servicio Pagos Reportados

**Objetivo:** Comprobar que el servicio Gemini está correctamente conectado al flujo de [Pagos Reportados](https://rapicredit.onrender.com/pagos/cobros/pagos-reportados), desde el envío del formulario público hasta la visualización en el listado administrativo.

**Fecha de auditoría:** 2025-03-10  
**Alcance:** Módulo Cobros — reporte público de pago → validación con Gemini → listado en `/pagos/cobros/pagos-reportados`.

---

## 1. Flujo end-to-end (trazabilidad)

```
[Usuario] Formulario público (rapicredit-cobros)
    → POST /api/v1/cobros/public/enviar-reporte (form + comprobante)
    → Backend: crea PagoReportado en BD (estado inicial "pendiente")
    → compare_form_with_image(form_data, image_bytes)  ← Gemini
    → Resultado: coincide_exacto (bool), comentario (str)
    → Backend: pr.gemini_coincide_exacto = "true"|"false", pr.gemini_comentario = comentario
    → Si coincide_exacto: estado = "aprobado", genera recibo y envía email
    → Si no: estado = "en_revision"
    → db.commit()

[Admin] Listado Pagos Reportados
    → GET /api/v1/cobros/pagos-reportados (con auth)
    → Backend: lee pagos_reportados; cada ítem incluye observacion = gemini_comentario
    → Frontend: columna "Observación" muestra divergencias Gemini; Estado muestra aprobado/en_revision
```

---

## 2. Referencias de código (trazabilidad)

| Paso | Archivo | Descripción |
|------|---------|-------------|
| Entrada pública | `app/api/v1/endpoints/cobros_publico.py` | Router sin auth; `enviar_reporte` recibe formulario + archivo comprobante. |
| Llamada Gemini | `app/api/v1/endpoints/cobros_publico.py` ~L289 | `gemini_result = compare_form_with_image(form_data, content, filename)` |
| Persistencia resultado | `app/api/v1/endpoints/cobros_publico.py` ~L291-292 | `pr.gemini_coincide_exacto = "true" if coincide else "false"`; `pr.gemini_comentario = gemini_result.get("comentario")` |
| Servicio Gemini | `app/services/pagos_gmail/gemini_service.py` | `compare_form_with_image()`: usa `GEMINI_API_KEY` y `GEMINI_MODEL`, envía formulario + imagen a Gemini, retorna `{coincide_exacto, requiere_revision_humana, comentario}`. |
| Modelo BD | `app/models/pago_reportado.py` | Campos `gemini_coincide_exacto` (VARCHAR(10)), `gemini_comentario` (TEXT). |
| Listado (API) | `app/api/v1/endpoints/cobros.py` | `GET /pagos-reportados`: construye `PagoReportadoListItem` con `observacion=r.gemini_comentario`. |
| Listado (UI) | `frontend/src/pages/CobrosPagosReportadosPage.tsx` | Tabla con columna "Observación" que muestra `row.observacion` (texto de divergencias Gemini). |

---

## 3. Comprobación en producción

### 3.1 Health check del módulo Cobros (Gemini conectado)

El endpoint **GET /api/v1/health/cobros** verifica:

- **BD:** ejecuta `SELECT 1`.
- **GEMINI_API_KEY:** configurado (no expone el valor).
- **Servicio Gemini para Cobros:** que la función `compare_form_with_image` sea cargable (mismo módulo que usa el flujo real).

**URL en producción:**

```http
GET https://rapicredit.onrender.com/api/v1/health/cobros
```

**Respuesta esperada si Gemini está bien conectado:**

```json
{
  "status": "ok",
  "db_ok": true,
  "gemini_configured": true,
  "cobros_gemini_service_connected": true,
  "smtp_configured": true,
  "error": null
}
```

Si `cobros_gemini_service_connected` es `false` o `gemini_configured` es `false`, el estado será `"degraded"` y en `error` aparecerá el motivo (ej. "GEMINI_API_KEY no configurado" o "Servicio Gemini para Cobros no cargable").

**Código:** `app/api/v1/endpoints/health.py` — `health_check_cobros` (~L142-198).

### 3.2 Verificación desde el listado Pagos Reportados

1. **Acceder** a [Pagos Reportados](https://rapicredit.onrender.com/pagos/cobros/pagos-reportados) con usuario autenticado.
2. **Comprobar columnas:**
   - **Estado:** debe mostrar "Aprobado" o "En revisión (manual)" según lo que Gemini haya devuelto (`gemini_coincide_exacto`).
   - **Observación:** si Gemini detectó divergencias, aquí aparece el `comentario` (gemini_comentario); si no hay divergencias, suele mostrarse "—".
3. **Trazabilidad:** un pago enviado por el formulario público que tenga estado "En revisión" y texto en Observación confirma que Gemini se ejecutó y guardó el comentario en BD, y que el listado lo expone correctamente.

### 3.3 Verificación opcional: Health Gemini (raíz)

```http
GET https://rapicredit.onrender.com/health/gemini
```

Este endpoint (en `app/main.py`) llama a `check_gemini_available()` del mismo `gemini_service` y devuelve 200 si la API key y el servicio responden. No es específico de Cobros pero confirma que Gemini está operativo.

---

## 4. Checklist de trazabilidad (Gemini bien conectado)

| # | Verificación | Cómo comprobarlo |
|---|----------------|-------------------|
| 1 | Health Cobros indica Gemini conectado | `GET /api/v1/health/cobros` → `cobros_gemini_service_connected: true` y `gemini_configured: true`. |
| 2 | Formulario público usa el mismo servicio | Código: `cobros_publico.py` importa y llama `compare_form_with_image` tras crear el `PagoReportado`. |
| 3 | Resultado Gemini se persiste en BD | Campos `pagos_reportados.gemini_coincide_exacto` y `pagos_reportados.gemini_comentario` actualizados tras la llamada. |
| 4 | Listado expone resultado para revisión | `GET /api/v1/cobros/pagos-reportados` incluye `observacion` (gemini_comentario); la UI muestra columna "Observación". |
| 5 | Comportamiento según resultado | Si `coincide_exacto`: estado "aprobado", recibo y email. Si no: estado "en_revision", comentario visible en Observación. |

---

## 5. Resumen

- **Conexión Gemini ↔ Pagos Reportados:** el flujo está trazado desde el endpoint público `enviar-reporte` hasta el listado administrativo; la única llamada a Gemini en este flujo es `compare_form_with_image` en `cobros_publico.py`, usando el servicio en `gemini_service.py`.
- **Comprobación rápida en producción:** llamar a **GET https://rapicredit.onrender.com/api/v1/health/cobros** y revisar que `cobros_gemini_service_connected` y `gemini_configured` sean `true`. Luego, en la pantalla [Pagos Reportados](https://rapicredit.onrender.com/pagos/cobros/pagos-reportados), comprobar que la columna **Observación** muestre las divergencias de Gemini cuando existan y que el **Estado** refleje aprobado/en revisión según el resultado de Gemini.
