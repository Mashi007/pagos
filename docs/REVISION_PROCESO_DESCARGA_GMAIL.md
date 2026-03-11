# Revisión: proceso de descarga Gmail (Pagos Gmail pipeline)

**Objetivo:** Verificar que el proceso de descarga esté claro y bien definido, y señalar dudas o mejoras.

---

## 1. Criterio único: correo no leído

| Aspecto | Estado | Definición |
|---------|--------|------------|
| Qué se descarga | OK | Todos los correos con etiqueta **UNREAD** en la cuenta Gmail configurada. |
| Filtro por asunto/remitente | OK (eliminado) | Ya no se filtra: se procesan todos los no leídos. |
| Origen de la lista | Definido | `list_unread_with_attachments(gmail_svc)` → Gmail API `users().messages().list(userId="me", labelIds=["UNREAD"], maxResults=500)`. |

**Nota:** El nombre de la función sugiere “con adjuntos”, pero en el código **no** se filtra por `has:attachment` en la query. Se listan todos los UNREAD; si un correo no tiene imágenes/adjuntos, se guarda una fila con valores NA y se marca como leído. Comportamiento correcto y documentado en el docstring de `gmail_service.list_unread_with_attachments`.

---

## 2. Flujo del pipeline (pasos definidos)

1. **Credenciales** → Si no hay, retorna `no_credentials` y no se ejecuta nada.
2. **Servicios** → Se construyen Drive y Gmail con las credenciales.
3. **Registro de sync** → Se crea o reutiliza un `PagosGmailSync` (running).
4. **Listar no leídos** → `list_unread_with_attachments(gmail_svc)`.
5. **Deduplicar** → Se eliminan duplicados por `message id`.
6. **Límite opcional** → Si `PAGOS_GMAIL_MAX_EMAILS_PER_RUN` > 0, se trunca el lote a ese máximo.
7. **Procesar lote inicial** → `process_message_batch(messages, "inicial")` (una sola vez, fuera del bucle por mensaje).
8. **Ciclo de revisión** → Hasta 10 pasadas: se vuelve a listar no leídos; si hay alguno, se procesan; si no hay ninguno, se sale.
9. **Cerrar sync** → Se actualiza `finished_at`, `emails_processed`, `files_processed`, `status` y se hace commit.

Por cada **mensaje** en un batch:

- Se obtiene fecha, carpeta/hoja por fecha.
- Se crea/obtiene carpeta en Drive.
- Se obtiene payload completo y, si hay reenvío, remitente reenviado.
- Se sube el .eml a Drive (si está disponible).
- Se extraen adjuntos/imágenes con `get_all_images_and_files_for_message`.
- Por cada adjunto: se sube a Drive, se envía a Gemini (`extract_payment_data`), se normaliza fecha/cédula/monto/referencia y se guarda una fila en `PagosGmailSyncItem`.
- Si no hay adjuntos, se guarda una fila NA.
- Se marca el mensaje como **leído** en Gmail (`mark_as_read`).
- Se actualiza el sync y se hace commit.

Todo lo anterior está definido y es coherente con “descargar todos los no leídos” y “al terminar volver a revisar hasta que no quede ninguno”.

---

## 3. Corrección aplicada (indentación)

- **Problema:** La llamada `process_message_batch(messages, "inicial")` estaba **dentro** del bucle que procesa cada mensaje, lo que provocaba recursión/reprocesos incorrectos.
- **Corrección:** Esa llamada se movió al nivel del bloque principal (misma indentación que el comentario `# Ciclo:`), de modo que:
  - El lote inicial se procesa **una vez**.
  - Luego se ejecuta el ciclo de revisión (volver a listar no leídos y procesar hasta 10 pasadas).

---

## 4. Dudas y límites conocidos

| Tema | Situación | Recomendación |
|------|-----------|----------------|
| Paginación Gmail | `list_unread_with_attachments` usa `maxResults=500` y **no** recorre `nextPageToken`. Si hay más de 500 no leídos, solo se procesan los primeros 500 por ejecución. | Si se esperan >500 no leídos, implementar bucle con `pageToken` hasta agotar resultados. |
| Orden de los mensajes | La API no garantiza orden por fecha; el orden puede ser por relevancia o interno. | Si se necesita “fecha primera → fecha última” explícito, ordenar la lista por `get_message_date(headers)` antes de procesar. |
| `max_revision_passes = 10` | Límite fijo en código. Con muchos correos que se re-marcan como no leídos, en teoría se podría necesitar más de 10 pasadas. | Valor 10 es razonable; si en producción se viera truncado, hacer el límite configurable por variable de entorno. |
| Rate limit 429 | Gmail puede devolver 429; el código espera hasta `Retry-After` (máx. 2 min) y reintenta una vez; si falla de nuevo, devuelve `[]`. | Comportamiento definido; en entornos con mucho volumen, monitorear 429 y considerar backoff más conservador. |

---

## 5. Resumen

- **Criterio de descarga:** Solo “no leído” (UNREAD). Sin filtro por asunto ni remitente.
- **Procesos:** Pasos del pipeline y del ciclo de revisión están claros y definidos en código y docstrings.
- **Bug corregido:** Llamada al lote inicial fuera del bucle por mensaje.
- **Dudas/mejoras:** Paginación si >500 no leídos; orden por fecha si se requiere; límite de 10 pasadas de revisión configurable si fuera necesario.

Si quieres, el siguiente paso puede ser implementar paginación en `list_unread_with_attachments` o documentar el orden (por fecha) en el flujo operativo.
