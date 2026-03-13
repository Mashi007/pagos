# Investigación punta a punta: Pagos Gmail (Generar Excel desde Gmail)

**Alcance:** Flujo completo desde la UI hasta la descarga del Excel, incluyendo backend, Gmail, Drive, Gemini, BD, scheduler y frontend. Incluye análisis de mejoras potenciales.

---

## 1. Flujo punta a punta (resumen)

```
[Usuario] → Clic «Generar Excel desde Gmail»
     ↓
[Frontend] runGmailNow() → POST /pagos/gmail/run-now (timeout 90s)
     ↓
[Backend]  Verifica credenciales (síncrono) → Crea PagosGmailSync (running) → BackgroundTasks.add_task(run_pipeline)
     ↓
[Backend]  Responde 200 { sync_id, status: "running" }
     ↓
[Frontend] Polling GET /pagos/gmail/status cada 5s (máx 25 min)
     ↓
[Pipeline] list_unread_with_attachments (Gmail API, labelIds=UNREAD)
     ↓
[Pipeline] Por cada correo: full_payload → body_text, subject → attachments (imágenes/PDF ≥10KB)
     ↓
[Pipeline] Por cada correo: get_or_create_folder(Drive) → upload .eml → por cada imagen: upload_file(Drive) → extract_payment_data(Gemini: asunto+cuerpo+imagen) → _guardar_en_bd → mark_as_read
     ↓
[Pipeline] Ciclo revisión (hasta 10 pasadas): volver a listar no leídos
     ↓
[Pipeline] sync.status = success|error, finished_at, db.commit
     ↓
[Frontend] last_status !== 'running' → toast → abre ConfirmarBorrarDiaDialog
     ↓
[Usuario]  Descargar Excel → confirmar borrar (sí/no)
     ↓
[Frontend] downloadGmailExcel(fecha) → GET /download-excel → confirmarDiaGmail(borrar, fecha)
```

---

## 2. Componentes revisados

### 2.1 Frontend

| Elemento | Ubicación | Estado |
|----------|-----------|--------|
| runGmailNow | pagoService.ts | POST run-now; timeout 90s en api.ts (run-now es rápido, responde al instante). |
| Polling | useGmailPipeline.ts | Cada 5s, máx 300 intentos (25 min). Para al ver success/error. |
| Descarga | pagoService.downloadGmailExcel | GET download-excel blob; filename desde Content-Disposition; 404 → Error con mensaje. |
| Confirmar borrado | CargaMasivaMenu, PagosList | Si download falla, no se llama confirmarDiaGmail (mejora ya aplicada). |
| Mensaje toast (sin correos) | useGmailPipeline | Dice "solo mensajes NO LEÍDOS con adjuntos" — algo restrictivo; la regla real es solo NO LEÍDOS (con o sin adjuntos). |

### 2.2 Backend – Endpoints

| Endpoint | Comportamiento | Observación |
|----------|----------------|-------------|
| POST /run-now | 409 si pipeline ya running (2h cutoff); 429 si force=false y última ejecución muy reciente; 503 si no hay credenciales; 200 + background task. | Correcto. |
| GET /status | Última sync, next_run_approx, latest_data_date. | No filtra por usuario; cualquier autenticado ve el mismo estado (asumido OK para un solo uso corporativo). |
| GET /download-excel | Sin fecha: todos los ítems ordenados por created_at. Con fecha: ítems con sheet_name de esa fecha. 404 si no hay datos. | _find_most_recent_data carga TODOS los ítems en memoria; con muchos datos podría ser pesado. |
| POST /confirmar-dia | Sin fecha: DELETE todos los ítems. Con fecha: DELETE por sheet_name. | Correcto. |
| GET /diagnostico | Prueba credenciales, list unread, primer correo, imágenes, Gemini health, extracción en primera imagen. | Útil; no incluye asunto/cuerpo en la prueba de extracción. |

### 2.3 Gmail

| Aspecto | Implementación | Observación |
|---------|----------------|-------------|
| Listado | labelIds=["UNREAD"], paginación 500, luego messages.get(metadata) por cada id. | N+1: un request por mensaje para metadata; con 500 correos son 501 requests. |
| Cuerpo | get_message_body_text(payload): text/plain o text/html→plain, límite 15k caracteres. | Correcto. |
| Adjuntos | get_all_images_and_files_for_message: adjuntos, inline, HTML base64, rfc822; filtro ≥10KB. | Imágenes &lt;10KB descartadas (logos); puede perderse comprobante muy pequeño. |
| Rate limit 429 | Retry-after parseado; si espera ≤2 min se espera y 1 reintento. | Solo 1 reintento; Gmail puede devolver 429 varias veces. |

### 2.4 Drive

| Aspecto | Implementación | Observación |
|---------|----------------|-------------|
| Carpeta | get_or_create_folder(name): list por name en root, si no existe create. | name viene de get_folder_name_from_date (ej. "8Marzo2026"); formato controlado. |
| Subida | upload_file: evita duplicado por nombre+tamaño en la carpeta; resumable=True. | Correcto. |
| Fallo | Si get_or_create_folder falla, el correo se omite (drive_errors++, no se guarda fila para ese msg). | Usuario no ve ese correo en el Excel; solo en logs. |

### 2.5 Gemini

| Aspecto | Implementación | Observación |
|---------|----------------|-------------|
| Entrada | Asunto + cuerpo (texto) + imagen/PDF opcional. | Extracción desde las 3 fuentes. |
| Rate limit | 429: hasta 2 reintentos con delay (45s o Retry-After). | Puede fallar con cuota free con muchos correos. |
| Sin API key | Devuelve NA en todos los campos; pipeline sigue. | Correcto. |
| Respuesta bloqueada | Safety/empty → _empty_result("blocked"); se guarda fila NA. | Correcto. |

### 2.6 BD y modelo

| Aspecto | Implementación | Observación |
|---------|----------------|-------------|
| Sync | PagosGmailSync: status running/success/error, contadores, error_message. | Limpieza de huérfanos al startup (main.py). |
| Items | PagosGmailSyncItem: por imagen/fila; 1 imagen = 1 fila. | Correcto. |
| Consultas download | _find_most_recent_data: select all items order by created_at (sin límite). _find_sheet_by_fecha: join con PagosGmailSync (join innecesario para el filtro). | Riesgo: muchos ítems = mucho uso de memoria. Join prescindible. |

### 2.7 Scheduler

| Aspecto | Implementación | Observación |
|---------|----------------|-------------|
| Job | _job_pagos_gmail_pipeline cada PAGOS_GMAIL_CRON_MINUTES (default 30). | Usa _is_pipeline_running y _last_run_too_recent; no lanza si ya hay uno en curso o si fue hace poco. |
| Sesión BD | SessionLocal() en el job, run_pipeline(db), finally db.close(). | Correcto. |

---

## 3. Fortalezas

- **Regla clara:** Solo correos NO LEÍDOS; sin filtro por asunto/remitente.
- **1 imagen = 1 fila = 1 pago** documentado y cumplido.
- **Extracción multimodal:** Cédula y demás campos desde asunto, cuerpo e imágenes.
- **Run-now asíncrono:** Background task evita timeout en el request; polling en frontend.
- **Credenciales:** Verificación síncrona antes de arrancar; fallback informe_pagos (BD).
- **Manejo de errores:** Descarga fallida no dispara confirmar borrado; Excel con try/except 500; sync huérfana limpiada al startup.
- **Diagnóstico:** Endpoint /diagnostico para soporte (credenciales, Gmail, Drive, Gemini).
- **Deduplicación:** Mensajes por id antes de procesar; Drive evita duplicados por nombre+tamaño.

---

## 4. Debilidades / riesgos

- **Download Excel sin límite:** _find_most_recent_data trae todos los ítems; con decenas de miles de filas puede consumir mucha memoria y tardar.
- **Gmail N+1:** Un request por mensaje para metadata; con muchos no leídos el listado es lento.
- **Imágenes &lt;10KB descartadas:** Comprobante muy pequeño podría no procesarse.
- **Mensaje frontend:** Toast "solo mensajes NO LEÍDOS con adjuntos" sugiere que hace falta adjunto; la regla real es solo NO LEÍDOS.
- **Join innecesario:** _find_sheet_by_fecha y _get_latest_date_with_data hacen join con PagosGmailSync sin necesidad.
- **Drive falla:** Si la carpeta no se puede crear, el correo se omite sin fila; el usuario no ve feedback por correo.
- **Un solo pipeline a la vez:** 409 si ya hay uno en curso; con ejecuciones largas el usuario debe esperar.

---

## 5. Mejoras potenciales (priorizadas)

### 5.1 Prioridad alta

| # | Mejora | Dónde | Estado |
|---|--------|-------|--------|
| 1 | Límite en download Excel | pagos_gmail.py, config | **Implementado:** PAGOS_GMAIL_DOWNLOAD_EXCEL_MAX_ITEMS (default 5000). _find_most_recent_data usa order_by desc + limit + reverse para devolver los N más recientes en orden ascendente. |
| 2 | Corregir mensaje toast "solo NO LEÍDOS con adjuntos" | useGmailPipeline.ts | **Implementado:** Mensaje actualizado a "solo mensajes NO LEÍDOS (con o sin adjuntos). Marque como no leído si quiere reprocesar." |

### 5.2 Prioridad media

| # | Mejora | Dónde | Descripción |
|---|--------|-------|-------------|
| 3 | Simplificar consultas BD | pagos_gmail.py | _find_sheet_by_fecha y _get_latest_date_with_data: quitar join con PagosGmailSync; filtrar solo por PagosGmailSyncItem. |
| 4 | Gmail: batch get metadata | gmail_service.py | Gmail API permite messages.get en batch (o al menos reducir round-trips); explorar si existe batch para metadata para bajar el N+1. |
| 5 | Diagnóstico con asunto/cuerpo | pagos_gmail.py diagnostico | Incluir en paso 6 (extracción) el asunto y cuerpo del primer correo para probar extracción multimodal. |
| 6 | Configurable umbral mínimo de imagen | gmail_service.py / config | Hacer MIN_PAYMENT_IMAGE_BYTES configurable (ej. PAGOS_GMAIL_MIN_IMAGE_BYTES) para permitir comprobantes &lt;10KB si se desea. |

### 5.3 Prioridad baja

| # | Mejora | Dónde | Descripción |
|---|--------|-------|-------------|
| 7 | Sanitizar nombre de carpeta Drive | drive_service.py | Aunque folder_name viene de fecha, sanitizar (escapar comillas) en la query de list para evitar inyección si en el futuro se usara otro origen. |
| 8 | Indicador de progreso en UI | CargaMasivaMenu, PagosList | Mostrar "Procesados X correos, Y archivos" durante el polling (ya viene en status; se puede mostrar en un pequeño banner). |
| 9 | SHOW_DESCARGA_EXCEL_EN_SUBMENU | PagosList.tsx | Valorar activar (true) para permitir "Descargar Excel" sin pasar por el diálogo de confirmar borrado. |
| 10 | Reintentos Gmail 429 | gmail_service.py | Aumentar reintentos o backoff cuando Gmail devuelve 429 (ej. 2–3 reintentos con espera). |
| 11 | Columna "Asunto" en Excel | download_excel, modelo | El modelo ya tiene asunto; podría añadirse columna "Asunto" en el Excel para trazabilidad. |

---

## 6. Resumen ejecutivo

- El flujo punta a punta está bien definido: run-now en background, polling, descarga Excel desde BD, confirmar borrado sin ejecutarlo si la descarga falla.
- Regla de negocio correcta (solo NO LEÍDOS) y extracción desde asunto, cuerpo e imágenes.
- Los principales riesgos son: **descarga Excel sin límite** (memoria/tiempo con muchos datos) y el **mensaje en frontend** que sugiere que se requieren adjuntos. Las mejoras de prioridad alta abordan eso; el resto son optimizaciones y mejoras de UX/observabilidad.

---

**Documento generado tras investigación punta a punta del flujo Pagos Gmail (Generar Excel desde Gmail).**
