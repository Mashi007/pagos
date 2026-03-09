# Auditoría: Pipeline Gmail → Drive → Gemini → Sheets (Pagos)

**Fecha:** 2025-03-08  
**Alcance:** Flujo completo desde «Generar Excel desde Gmail» hasta «Descargar Excel» y «Confirmar día».

---

## 1. Resumen ejecutivo

| Componente | Estado | Notas |
|------------|--------|--------|
| Listado Gmail (no leídos + adjuntos/imágenes) | OK | maxResults=500; filtro por contenido extraíble |
| Filtro por asunto | **Corregido** | `PAGOS_GMAIL_SUBJECT_KEYWORDS_OR` no se usaba; ahora se aplica en pipeline |
| Drive / Sheets | OK | Carpeta y hoja por fecha; subida adjuntos e inline |
| Gemini | OK | NA si no identifica; reintentos 429; prompt sin adivinar |
| Descarga Excel backend | OK | 404 si no hay datos; fallback 3 días anteriores |
| Descarga Excel frontend | OK | Solo descarga si status 200 (evita Excel corrupto) |
| Confirmar día | OK | Borra ítems por sheet_name |
| Credenciales | OK | Archivo tokens o fallback informe_pagos (BD) |

---

## 2. Flujo paso a paso

### 2.1 Usuario pulsa «Generar Excel desde Gmail»

1. **Frontend** (`PagosList.tsx` / `CargaMasivaMenu.tsx`): `pagoService.runGmailNow()`.
2. **Backend** `POST /api/v1/pagos/gmail/run-now`:
   - Comprueba que no haya otra sync en curso (`_is_pipeline_running`).
   - Con `force=true` (por defecto) no aplica intervalo mínimo.
   - Llama a `run_pipeline(db)`.

### 2.2 Pipeline (`pipeline.py`)

1. **Credenciales:** `get_pagos_gmail_credentials()` → archivo `GMAIL_TOKENS_PATH` o credenciales Informe de pagos (BD). Si falla → 503 y mensaje claro.
2. **Gmail:** `list_unread_with_attachments(gmail_svc)`:
   - `messages.list(userId="me", labelIds=["UNREAD"], maxResults=500)`.
   - Por cada mensaje se pide `format="metadata"` y se filtra por `_message_has_extractable_content(payload)` (adjuntos permitidos o imagen/PDF en cuerpo).
   - **Filtro por asunto:** Se aplica `subject_acceptable_for_pipeline(subject, keywords_or)`: se procesa si el asunto contiene un email o alguna de las frases en `PAGOS_GMAIL_SUBJECT_KEYWORDS_OR` (p. ej. "Cobranza Rapicredit", "Pago de crédito"). Los que no cumplan se omiten.
3. **Límite por ejecución:** Si `PAGOS_GMAIL_MAX_EMAILS_PER_RUN > 0`, se truncan los mensajes a ese número (el resto en la siguiente pasada).
4. Por cada mensaje aceptado:
   - Fecha del correo → nombre de carpeta y hoja (ej. `8Marzo2026`, `Pagos_Cobros_8Marzo2026`).
   - Drive: `get_or_create_folder`, `get_or_create_sheet_for_date`.
   - Adjuntos/cuerpo: `get_all_images_and_files_for_message` (adjuntos + inline MIME + imágenes base64 en HTML).
   - Si **>1 adjunto:** una fila con asunto y NA.
   - Si **0 adjuntos:** una fila con asunto y NA.
   - Si **1 adjunto/imagen:** subida a Drive, `extract_payment_data` (Gemini), fila con datos o NA; `PAGOS_GMAIL_DELAY_BETWEEN_GEMINI_SECONDS` entre llamadas.
   - Se marca como **leído** solo si al menos una fila tiene datos válidos (no todo NA); si todo NA se deja no leído para reintento.
5. Se actualiza `pagos_gmail_sync` (emails_processed, files_processed, status, finished_at).

### 2.3 Respuesta run-now

- `sync_id`, `status` ("success" | "error" | "no_credentials"), `emails_processed`, `files_processed`.
- Frontend muestra toast con correos y archivos procesados; si 0/0 sugiere revisar no leídos y adjuntos.

### 2.4 Usuario descarga Excel

1. **Frontend:** `pagoService.downloadGmailExcel(fecha?)` → `GET .../gmail/download-excel?fecha=YYYY-MM-DD` (opcional).
2. **Backend:**
   - Fecha: `fecha` query o día actual (America/Caracas; después de 23:50 → día siguiente).
   - `_find_sheet_date_with_data(db, sheet_date)`: busca datos en esa fecha y hasta 3 días anteriores.
   - Si **no hay datos** → **404** con mensaje: "Sin datos para... Pulse «Generar Excel desde Gmail»...".
   - Si hay datos → genera openpyxl (columnas: Asunto, Fecha Pago, Cedula, Monto, Referencia, Link), devuelve `StreamingResponse` con `Content-Disposition: attachment`.
3. **Frontend:** Solo si `response.status === 200` crea blob y descarga; si no, lanza error (evita guardar HTML/JSON como .xlsx). Toast "Excel descargado" o mensaje de error.

### 2.5 Confirmar día

1. Usuario elige Sí/No en el diálogo (tras descargar).
2. `pagoService.confirmarDiaGmail(borrar, fecha?)` → `POST .../gmail/confirmar-dia` con `{ confirmado, fecha? }`.
3. Si `confirmado=true`: `DELETE` ítems donde `sheet_name == get_sheet_name_for_date(sheet_date)`; commit. Respuesta incluye `borrados`.
4. Futuras descargas para esa fecha devolverán 404 hasta que haya nueva ejecución del pipeline.

---

## 3. Configuración crítica (.env / variables de entorno)

| Variable | Uso | Valor típico |
|----------|-----|--------------|
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | OAuth Gmail/Drive/Sheets | De Google Cloud Console |
| `GMAIL_TOKENS_PATH` | Ruta al JSON con refresh_token | `gmail_tokens.json` |
| `GEMINI_API_KEY` | Extracción de datos en comprobantes | API Key de Google AI Studio |
| `GEMINI_MODEL` | Modelo Gemini | `gemini-2.0-flash` (o el que permita la API) |
| `PAGOS_GMAIL_CRON_MINUTES` | Intervalo cron (y ventana "too recent") | 30 (gratis) / 15 (de pago) |
| `PAGOS_GMAIL_DELAY_BETWEEN_GEMINI_SECONDS` | Pausa entre llamadas Gemini | 4 (gratis ~15 RPM) |
| `PAGOS_GMAIL_MAX_EMAILS_PER_RUN` | Límite de correos por ejecución (0 = sin límite) | 0 o 15 en gratis |
| `PAGOS_GMAIL_SUBJECT_KEYWORDS_OR` | Frases en asunto para aceptar correo (si no tiene email) | `Cobranza Rapicredit,Pago de crédito` |
| `DRIVE_ROOT_FOLDER_ID` | Carpeta raíz Drive para subir adjuntos | ID de carpeta en Drive |

**Health:** `GET /health/db` verifica BD. No hay un health específico de Gmail/Gemini; si falla run-now, el detalle viene en 503 (credenciales) o en logs (excepciones).

---

## 4. Puntos de fallo y mitigaciones

| Punto | Riesgo | Mitigación |
|-------|--------|------------|
| Credenciales OAuth inválidas | 503, "invalid_client" | Reconectar en Configuración > Informe de pagos; mismo Client ID/Secret |
| GEMINI_API_KEY ausente | Filas con NA | Variable de entorno; mensaje en logs |
| Modelo Gemini 404 | Error en extracción | Usar modelo válido (docs Google) |
| Cuota Gemini (429) | Reintentos con backoff | PAGOS_GMAIL_DELAY_BETWEEN_GEMINI_SECONDS; hasta 2 reintentos |
| Más de 500 no leídos | Solo se listan 500 | Paginación no implementada; ejecutar varias veces o marcar leídos |
| Descarga sin datos | 404 | Mensaje claro; no se devuelve Excel vacío |
| Descarga con status ≠ 200 | Excel corrupto (HTML/JSON guardado como .xlsx) | Frontend solo descarga si status 200 |
| Desajuste de fecha (zona horaria) | Usuario descarga "hoy" y no hay datos | Backend prueba hasta 3 días anteriores |
| Correos sin asunto válido | No se procesaban / se procesaban todos | Filtro por asunto aplicado con PAGOS_GMAIL_SUBJECT_KEYWORDS_OR |

---

## 5. Archivos clave

- **Backend:** `app/api/v1/endpoints/pagos_gmail.py`, `app/services/pagos_gmail/pipeline.py`, `gmail_service.py`, `gemini_service.py`, `credentials.py`, `helpers.py`, `drive_service.py`, `sheets_service.py`.
- **Frontend:** `pagoService.ts` (runGmailNow, downloadGmailExcel, confirmarDiaGmail, getGmailStatus), `PagosList.tsx`, `CargaMasivaMenu.tsx`.
- **Modelos:** `app/models/pagos_gmail_sync.py` (PagosGmailSync, PagosGmailSyncItem).
- **Config:** `app/core/config.py` (variables PAGOS_GMAIL_*, GEMINI_*, GOOGLE_*, GMAIL_TOKENS_PATH).

---

## 6. Recomendaciones

1. **Logs:** Buscar `[PAGOS_GMAIL]` y `[PAGOS_GMAIL_CONFIG]` para diagnosticar fallos de pipeline o configuración.
2. **Si 0 correos procesados:** Verificar que haya correos no leídos, con adjuntos o imágenes en cuerpo, y que el asunto cumpla (email o keyword en `PAGOS_GMAIL_SUBJECT_KEYWORDS_OR`).
3. **Si 404 al descargar:** Ejecutar «Generar Excel desde Gmail», esperar a que termine y volver a descargar; comprobar que GEMINI_API_KEY esté configurado.
4. **Paginación Gmail:** Si en el futuro se necesitan >500 no leídos por ejecución, implementar `nextPageToken` en `list_unread_with_attachments`.
5. **Filtro asunto:** Si se quieren procesar todos los no leídos con adjuntos sin filtrar por asunto, dejar `PAGOS_GMAIL_SUBJECT_KEYWORDS_OR` vacío y asegurar que los asuntos contengan al menos un email, o ampliar keywords.

---

*Documento generado en el marco de la auditoría del flujo Gmail → Excel (módulo Pagos).*
