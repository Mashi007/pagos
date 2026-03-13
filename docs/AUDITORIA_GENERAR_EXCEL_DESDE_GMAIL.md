# Auditoría: Generar Excel desde Gmail

**Alcance:** Flujo completo desde el botón «Generar Excel desde Gmail» hasta la descarga del Excel y la confirmación de borrado. Incluye backend (pipeline, endpoints, BD), frontend (servicios, hooks, UI) y propuestas de mejora.

---

## 1. Resumen del flujo

| Paso | Componente | Acción |
|------|------------|--------|
| 1 | Usuario | Pulsa «Generar Excel desde Gmail» (PagosList o CargaMasivaMenu). |
| 2 | Frontend | `pagoService.runGmailNow()` → `POST /api/v1/pagos/gmail/run-now`. |
| 3 | Backend | Crea `PagosGmailSync` (status=running), lanza pipeline en background, responde de inmediato. |
| 4 | Pipeline | Gmail (no leídos) → extrae adjuntos/imágenes → Drive → Gemini → BD (`pagos_gmail_sync_item`). |
| 5 | Frontend | Polling `GET /pagos/gmail/status` cada 5 s hasta `last_status` ∈ { success, error }. |
| 6 | Frontend | Al terminar: abre `ConfirmarBorrarDiaDialog` (descargar Excel y elegir si borrar datos). |
| 7 | Usuario | Elige Sí/No → se llama `downloadGmailExcel(fecha)` y luego `confirmarDiaGmail(borrar, fecha)`. |

El Excel se genera en `GET /pagos/gmail/download-excel` leyendo solo de la BD (`pagos_gmail_sync_item`); no se usa Google Sheets.

---

## 2. Backend

### 2.1 Endpoints (`app/api/v1/endpoints/pagos_gmail.py`)

| Método | Ruta | Función | Observación |
|--------|------|---------|-------------|
| POST | `/run-now` | Inicia pipeline en background | 409 si ya hay sync en curso; 503 si no hay credenciales. |
| GET | `/status` | Última ejecución, próxima, `latest_data_date` | Usado para polling y para habilitar «Descargar Excel». |
| GET | `/download-excel` | Genera Excel desde BD | Sin `?fecha`: backlog más reciente. Con `?fecha=YYYY-MM-DD`: esa fecha. 404 si no hay datos. |
| POST | `/confirmar-dia` | Borra ítems del día o todo | Sin fecha: borra todo el acumulado. Con fecha: solo esa `sheet_name`. |
| GET | `/diagnostico` | Prueba credenciales, Gmail, Drive, Gemini | Útil para soporte. |

### 2.2 Generación del Excel (`download_excel`)

- **Origen de datos:** Solo `PagosGmailSyncItem` (BD). Correcto.
- **Columnas generadas:** Correo Pagador, Fecha Pago, Cedula, Monto, Referencia, Link, Ver email. Hipervínculos para Link (imagen en Drive) y Ver email (.eml en Drive).
- **Docstring:** Decía «Asunto» y no mencionaba «Ver email»; corregido en esta auditoría.
- **Manejo de errores:** Si `openpyxl` falla al generar el libro, la excepción no se captura y se propaga (500). Mejora sugerida: try/except y mensaje claro.
- **Consultas:** `_find_sheet_by_fecha` y `_get_latest_date_with_data` hacen `join` con `PagosGmailSync` aunque el filtro es solo por `sheet_name` o por `created_at` en ítems. El join no añade filtro; se puede simplificar a solo `PagosGmailSyncItem` para claridad y un poco menos de trabajo en BD.

### 2.3 Pipeline (`app/services/pagos_gmail/pipeline.py`)

- **Flujo:** Gmail (no leídos) → Drive (carpeta por fecha, subida de imagen + .eml) → Gemini (extracción) → BD. Ciclo de revisión hasta 10 pasadas para procesar nuevos no leídos.
- **Regla de negocio:** Solo correos no leídos; sin filtro por asunto/remitente. Correcto y documentado.
- **Deduplicación:** Se evitan mensajes duplicados por `msg_id` antes de procesar. Correcto.
- **Commit:** Incremental por correo; en error se marca sync como error y se hace commit. Correcto.

### 2.4 Modelos (`app/models/pagos_gmail_sync.py`)

- `PagosGmailSync`: id, started_at, finished_at, status, emails_processed, files_processed, error_message.
- `PagosGmailSyncItem`: sync_id, correo_origen, asunto, fecha_pago, cedula, monto, numero_referencia, drive_file_id, drive_link, drive_email_link, sheet_name, created_at. Todos los campos usados en el Excel están cubiertos.

---

## 3. Frontend

### 3.1 Servicio (`pagoService.ts`)

- `runGmailNow(force)` → POST run-now. Correcto.
- `getGmailStatus()` → GET status. Correcto.
- `downloadGmailExcel(fecha?)` → GET download-excel con blob; valida status 200; si no, parsea JSON para `detail` y lanza Error. Nombre de archivo desde `Content-Disposition`. Correcto.
- `confirmarDiaGmail(confirmado, fecha?)` → POST confirmar-dia. Correcto.

### 3.2 Hook `useGmailPipeline`

- Polling cada 5 s; máximo 300 intentos (25 min). En `last_status` success/error se detiene y se llama `onDone`/`onStatusUpdate`. Maneja toast según resultado (éxito, error, sin correos, timeout con datos disponibles). Correcto.

### 3.3 Componentes

- **CargaMasivaMenu:** Botón «Generar Excel desde Gmail» → `runGmail()`; al terminar abre `ConfirmarBorrarDiaDialog`. En el diálogo, `onElegir` hace: 1) `downloadGmailExcel(fecha)`, 2) `confirmarDiaGmail(borrar, fecha)`. **Problema:** Si la descarga falla (404, red, etc.) se muestra toast de error pero igual se llama `confirmarDiaGmail`. Si el usuario eligió «Sí», se borrarían datos sin haber recibido el archivo. **Mejora:** No llamar a `confirmarDiaGmail` cuando la descarga falla; cerrar el diálogo y permitir reintentar.
- **PagosList:** Mismo patrón en `ConfirmarBorrarDiaDialog` (mismo bug). Además tiene opción «Descargar Excel» en submenú controlada por `SHOW_DESCARGA_EXCEL_EN_SUBMENU` (actualmente `false`).

---

## 4. Mejoras implementadas / recomendadas

### 4.1 Implementadas en esta auditoría

1. **Docstring `download_excel`:** Actualizado a «Columnas: Correo Pagador, Fecha Pago, Cédula, Monto, Referencia, Link, Ver email».
2. **Flujo ConfirmarBorrarDiaDialog:** Si `downloadGmailExcel` lanza, no se llama a `confirmarDiaGmail`; se muestra el error y se mantienen los datos en BD. Aplicado en CargaMasivaMenu y PagosList.

### 4.2 Implementadas adicionales

3. **Manejo de errores en `download_excel`:** Envolver generación del Workbook y `wb.save` en try/except; en caso de excepción devolver 500 con mensaje claro y log de la excepción.

### 4.3 Recomendadas (opcionales)

4. **Simplificar consultas BD:** En `_find_sheet_by_fecha` y `_get_latest_date_with_data`, quitar el join con `PagosGmailSync` y consultar solo `PagosGmailSyncItem` (el filtro/orden no depende del sync).
5. **Content-Disposition filename:** Asegurar que el nombre del archivo en la respuesta use formato RFC 5987 (filename*=UTF-8'') si hubiera caracteres no ASCII, para evitar problemas en algunos clientes.
6. **Excel:** Añadir ancho de columnas automático (`ws.column_dimensions`) o formato de fecha en columna «Fecha Pago» para mejor legibilidad.
7. **Descarga directa sin diálogo:** Valorar dejar `SHOW_DESCARGA_EXCEL_EN_SUBMENU = true` para que el usuario pueda «Descargar Excel» sin pasar por el diálogo de confirmar borrado, cuando ya sabe que no quiere borrar aún.

---

## 5. Checklist de validación

- [x] run-now crea sync y lanza pipeline en background.
- [x] Polling termina en success/error y actualiza UI.
- [x] download-excel lee solo BD; columnas e hipervínculos correctos.
- [x] confirmar-dia borra por fecha o todo; no toca registros de sync.
- [x] Si la descarga falla, no se confirma borrado (mejora aplicada).
- [x] Try/except en generación Excel en backend (500 con mensaje claro).
- [ ] (Opcional) Simplificar joins en consultas de ítems.

---

**Documento generado tras auditoría del flujo «Generar Excel desde Gmail».**
