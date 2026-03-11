# Pagos Gmail: flujo de inicio a fin, endpoints y procesos

Documento de referencia del módulo **Pagos Gmail** (Gmail → Drive → Gemini → BD → Excel). Incluye endpoints, criterios, procesos y reglas del prompt para evitar ambigüedades.

---

## 1. Resumen del flujo (inicio → fin)

| Fase | Qué ocurre |
|------|------------|
| **Entrada** | Usuario pulsa "Generar Excel desde Gmail" en la UI **o** el cron (cada `PAGOS_GMAIL_CRON_MINUTES` min) dispara el pipeline. |
| **API** | `POST /api/v1/pagos/gmail/run-now` (con auth). Si no hay otra ejecución en curso y las credenciales son válidas, se crea un registro `PagosGmailSync` (status=running) y se lanza el pipeline en segundo plano. |
| **Pipeline** | 1) Listar correos **no leídos** en Gmail (sin filtro por asunto/remitente). 2) Deduplicar por message id. 3) Opcional: limitar a `PAGOS_GMAIL_MAX_EMAILS_PER_RUN`. 4) Procesar lote inicial (por cada correo: carpeta Drive por fecha, .eml a Drive, extraer imágenes/PDF ≥10KB, enviar a Gemini, guardar fila en `PagosGmailSyncItem`, marcar como leído). 5) **Ciclo de revisión**: volver a listar no leídos; si hay alguno, procesar (máx. 10 pasadas). 6) Cerrar sync (finished_at, status success/error). |
| **Salida** | Usuario hace polling a `GET /api/v1/pagos/gmail/status` hasta `last_status` = success o error. Luego puede descargar Excel con `GET /api/v1/pagos/gmail/download-excel` (con o sin `?fecha=YYYY-MM-DD`). |

---

## 2. Endpoints (prefijo base: `/api/v1/pagos/gmail`)

Todos requieren autenticación (`get_current_user`), salvo que se indique lo contrario.

| Método | Ruta | Descripción |
|--------|------|-------------|
| **POST** | `/run-now` | Inicia el pipeline en background. Query: `force` (bool, default True). Devuelve `sync_id`, `status: "running"`. Con `force=False` se respeta el intervalo mínimo desde la última ejecución (429 si demasiado pronto). |
| **GET** | `/status` | Última ejecución: `last_run`, `last_status`, `last_emails`, `last_files`, `last_error`, `next_run_approx`, `latest_data_date`. Para polling hasta que termine. |
| **GET** | `/download-excel` | Genera Excel desde BD. Query opcional: `fecha=YYYY-MM-DD`. Sin fecha: datos más recientes en BD (backlog). 404 si no hay datos. |
| **POST** | `/confirmar-dia` | Body: `{ "confirmado": true/false, "fecha": "YYYY-MM-DD" opcional }`. Si confirmado y con fecha: borra ítems de esa fecha. Sin fecha: borra todo el acumulado. |
| **GET** | `/diagnostico` | Diagnóstico paso a paso: credenciales, listado Gmail, primer correo, imágenes, health Gemini, extracción con Gemini. No modifica datos. |

---

## 3. Procesos clarificados

### 3.1 Criterio de qué se descarga

- **Único criterio:** correos con etiqueta **UNREAD** en la cuenta Gmail configurada. Debe descargar y procesar **todos** los correos no leídos. La lista de Gmail usa **paginación** (nextPageToken) para obtener todos los no leídos, no solo los primeros 500. Para no limitar por ejecución use **PAGOS_GMAIL_MAX_EMAILS_PER_RUN=0** en producción.
- **No** se filtra por asunto ni por remitente; se procesan todos los no leídos.
- Si un correo no tiene imágenes/adjuntos ≥10KB, se guarda una fila con valores NA y se marca como leído.

### 3.2 Ejecución en background y bloqueos

- Solo puede haber **una** ejecución "running" a la vez. Si hay un sync con `status=running` y `started_at` dentro de las últimas 2 horas, `POST /run-now` devuelve **409**.
- `force=True` (por defecto): se ignora el intervalo mínimo; pensado para ejecución manual desde la UI.
- `force=False`: se aplica un intervalo mínimo (`PAGOS_GMAIL_CRON_MINUTES - 2` min, mínimo 5 min); si la última ejecución terminó hace menos, se devuelve **429** con mensaje de espera.

### 3.3 Ciclo de revisión

- Tras procesar el lote inicial, se vuelve a llamar a Gmail para listar no leídos.
- Si hay alguno, se procesan y se repite hasta que **no quede ninguno** o se alcancen **10 pasadas**.
- Así se cubren correos re-marcados como no leídos durante la misma ejecución.

### 3.4 Fecha del Excel y de las hojas

- Cada correo se agrupa por **fecha del correo** (header Date) → `sheet_name` = `Pagos_Cobros_{día}{Mes}{Año}` (ej. `Pagos_Cobros_8Marzo2026`).
- **Download Excel sin `?fecha`:** se usan los ítems más recientes en BD (por `created_at`), sin importar la fecha del correo (backlog).
- **Download Excel con `?fecha=YYYY-MM-DD`:** solo ítems cuyo `sheet_name` corresponde a esa fecha.
- **Confirmar día con fecha:** borra solo ítems de ese `sheet_name`. **Confirmar día sin fecha:** borra todos los ítems.

### 3.5 Imágenes y Gemini

- Solo se envían a Gemini archivos **≥ 10 KB** (logos/decoraciones se descartan).
- Fuentes: adjuntos, partes MIME inline, imágenes en HTML (base64), mensajes reenviados (message/rfc822).
- Por cada imagen/PDF: se sube a Drive, se llama a `extract_payment_data` (Gemini), se normalizan fecha/cédula/monto/referencia y se guarda una fila en `PagosGmailSyncItem`.
- Si Gemini no está configurado (`GEMINI_API_KEY`) o falla, se guarda la fila con NA en los campos extraídos.

---

## 4. Prompt Gemini (extracción de pagos) – reglas para evitar ambigüedades

El prompt en `gemini_service.py` (`GEMINI_PROMPT`) debe dejar claro:

1. **Formato de respuesta:** únicamente un objeto JSON; sin texto antes/después, sin markdown ni bloques ```json.
2. **Campos exactos:** `fecha_pago`, `cedula`, `monto`, `numero_referencia`. Si falta un dato → `"NA"`.
3. **No inventar:** si un dato no aparece en la imagen, usar `"NA"`. Si la imagen no es un comprobante (logo, firma, publicidad), devolver los cuatro campos con `"NA"`.
4. **Cédula:** solo dígitos (sin prefijo V-/E-/J- en el valor); el sistema luego formatea con `formatear_cedula`.
5. **Referencia:** solo el número/código, sin la etiqueta (Ref:, Serial:, Operación:, etc.).
6. **Monto:** incluir moneda (ej. `142.00 USD`, `80000.00 Bs`).

Así se reduce que el modelo devuelva texto libre o respuestas ambiguas que traben el parseo JSON.

---

## 5. Configuración relevante (`app.core.config`)

| Variable | Uso |
|----------|-----|
| `GEMINI_API_KEY` | Obligatoria para extracción; si falta, se guardan NA. |
| `GEMINI_MODEL` | Modelo Gemini (ej. `gemini-2.5-flash`). |
| `PAGOS_GMAIL_CRON_MINUTES` | Intervalo del cron y cálculo de "próxima ejecución" y de intervalo mínimo con `force=False`. |
| `PAGOS_GMAIL_DELAY_BETWEEN_GEMINI_SECONDS` | Pausa entre llamadas a Gemini (evitar 429). |
| `PAGOS_GMAIL_MAX_EMAILS_PER_RUN` | 0 = sin límite; >0 limita correos por ejecución. |
| `PAGOS_GMAIL_SUBJECT_KEYWORDS_OR` / `PAGOS_GMAIL_SENDER_PREFIXES_ALWAYS_INCLUDE` | No se usan en el pipeline actual (criterio = solo no leídos); quedan por si se reutilizan en otro flujo. |

---

## 6. Mejoras aplicadas / recomendadas

- **Prompt:** Añadidas instrucciones explícitas de formato (solo JSON), no inventar datos y devolver NA cuando la imagen no sea comprobante.
- **Pipeline:** Docstring actualizado: "ciclo de revisión (hasta 10 pasadas)" en lugar de "revisión final".
- **run-now:** Docstring aclarado: `force=True` para UI manual, `force=False` para respetar intervalo (cron).
- **Paginación Gmail:** Ya implementada: se usa nextPageToken hasta agotar todos los no leídos.

Este documento sirve como referencia única de inicio a fin para revisar procesos, endpoints y criterios del módulo Pagos Gmail.
