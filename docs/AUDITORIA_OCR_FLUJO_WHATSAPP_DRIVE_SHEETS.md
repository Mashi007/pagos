# Auditoría completa: OCR, endpoints, procesos y reglas
## Flujo WhatsApp → Drive → OCR → BD → Google Sheets

**Objetivo:** Verificar por qué el archivo llega a WhatsApp, se almacena en Drive, pero **no se procesa** y **no llega a Sheet**.

---

## 1. Resumen del flujo (orden real en código)

| Paso | Acción | Archivo / componente | Si falla |
|------|--------|----------------------|----------|
| 1 | Webhook recibe mensaje | `whatsapp.py` POST `/webhook` | No se procesa mensaje |
| 2 | Descarga imagen desde Meta | `whatsapp_service._process_image_message` | `image_error`, "No pudimos procesar" |
| 3 | **OCR** `extract_from_image` | `ocr_service.py` | Se usa `ocr_data_early` con "NA"; flujo continúa |
| 4 | IA / claridad (aceptar foto) | `ai_imagen_respuesta` / `imagen_suficientemente_clara` | Si no aceptar y intento < 3 → `photo_retry` (no Drive, no Sheet) |
| 5 | **Subida a Drive** | `google_drive_service.upload_image_and_get_link` | `link_imagen = "NA"`; flujo continúa |
| 6 | Insert `pagos_whatsapp` + commit | `whatsapp_service` | **Excepción → rollback BD; archivo ya está en Drive** |
| 7 | Insert `pagos_informes` + commit | `whatsapp_service` | **Excepción → rollback BD; archivo ya está en Drive** |
| 8 | **append_row a Google Sheets** | `google_sheets_informe_service.append_row` | Solo log; no lanza excepción; usuario recibe "OK" pero fila no en Sheet |

**Conclusión clave:** Si la imagen **sí aparece en Drive** pero **no en Sheet** y “no se procesa”, el fallo ocurre **después** de la subida a Drive y **antes o durante** el commit en BD o la escritura en Sheets. El archivo en Drive es persistido por la API de Google; el rollback de la BD no borra lo ya subido.

---

## 2. Causas probables: “En Drive pero no procesado / no en Sheet”

### 2.1 Fallo en base de datos (tras subir a Drive)

- **Columna faltante** en `pagos_whatsapp` o `pagos_informes` (p. ej. `link_imagen`, `nombre_banco`, `numero_documento`, `humano`, `observacion`).
- **Error:** `ProgrammingError: column "X" does not exist` (o similar).
- **Efecto:** Excepción en `db.add(row_pw)` o `db.add(informe)` o `db.commit()` → se ejecuta `db.rollback()` → no se inserta fila en BD y **nunca se llama** `append_row` → no hay fila en Sheet. El archivo ya está en Drive.

**Acción:** Ejecutar migraciones:

```bash
# Unificado (recomendado)
psql "<DATABASE_URL>" -f backend/sql/migracion_mvp_ocr_todas_columnas.sql

# O por partes
psql "<DATABASE_URL>" -f backend/sql/migracion_pagos_whatsapp_link_imagen.sql
psql "<DATABASE_URL>" -f backend/sql/migracion_pagos_informes_columnas_faltantes.sql
psql "<DATABASE_URL>" -f backend/sql/migracion_confirmacion_identidad.sql
```

### 2.2 Sheets no configurado o credenciales

- **`google_sheets_id`** vacío o **credenciales** sin permiso para Sheets.
- **Efecto:** `_get_sheets_service()` devuelve `(None, None)` → `append_row` retorna `False` sin lanzar excepción → se loguea `"Sheets no escribió fila (BD OK)"` y el usuario recibe mensaje de éxito, pero la fila **no aparece en la hoja**.

**Acción:** En **Configuración > Informe pagos**:  
- Rellenar **ID de la hoja** (de la URL: `docs.google.com/spreadsheets/d/<ID>/edit`).  
- Tener **credenciales Google** (cuenta de servicio u OAuth con “Conectar con Google”) con scope `spreadsheets`.  
- Verificar estado: **GET** `/api/v1/configuracion/informe-pagos/estado` → `sheets.conectado: true`.

### 2.3 Pestaña incorrecta o hoja vacía

- Si no se configura **Pestaña donde escribir** (`sheet_tab_principal`), se usan pestañas por periodo: **6am**, **1pm**, **4h30**. Si el usuario mira solo “Hoja 1”, no ve los datos.
- **Acción:** En configuración informe pagos, poner **Pestaña donde escribir** = `Hoja 1` (o la pestaña que se use) para que todas las filas vayan ahí; o revisar las pestañas 6am / 1pm / 4h30.

### 2.4 Timeout o error de red

- Si la petición al webhook hace timeout **después** de subir a Drive pero **antes** de `db.commit()` o de `append_row`, el worker puede cortar: BD en rollback y Sheet sin escribir. El archivo queda en Drive.
- **Acción:** Revisar timeouts en Render/hosting y logs en el momento del envío; considerar reintentos o cola asíncrona si es recurrente.

---

## 3. Endpoints implicados

| Método | Ruta | Uso en flujo OCR/Drive/Sheets |
|--------|------|-------------------------------|
| POST | `/api/v1/whatsapp/webhook` | Entrada de mensajes; dispara `_process_image_message` (descarga → OCR → Drive → BD → Sheet). |
| GET  | `/api/v1/configuracion/informe-pagos/estado` | Verificación **real** de Drive, Sheets y OCR (Vision). |
| GET  | `/api/v1/configuracion/informe-pagos/configuracion` | Lectura de configuración (carpeta Drive, hoja, credenciales, palabras clave OCR, etc.). |
| PUT  | `/api/v1/configuracion/informe-pagos/configuracion` | Guardar configuración (persiste en tabla `configuracion`, clave `informe_pagos_config`). |

No hay un endpoint específico “solo OCR”; el OCR se ejecuta dentro del flujo del webhook al procesar una imagen.

---

## 4. Procesos y servicios

| Proceso / servicio | Rol |
|--------------------|-----|
| `whatsapp_service._process_image_message` | Orquesta: descarga imagen, OCR, IA/claridad, subida Drive, insert `pagos_whatsapp`, insert `pagos_informes`, `append_row` Sheets, reset conversación. |
| `ocr_service.extract_from_image` | Vision API → extrae fecha, banco, número depósito, número documento, cantidad (y “HUMANO” si baja confianza). |
| `ocr_service.get_full_text` | Texto completo para IA de respuesta. |
| `google_drive_service.upload_image_and_get_link` | Sube bytes a la carpeta configurada y devuelve `webViewLink` (o `None` si falla). |
| `google_sheets_informe_service.append_row` | Añade una fila a la pestaña configurada (o 6am/1pm/4h30). No lanza si falla; retorna `False`. |
| `configuracion_informe_pagos._verificar_drive/sheets/ocr` | Pruebas reales de conexión para el endpoint `/estado`. |

**Regla de negocio (datos reales):** Los datos mostrados en dashboard/informes deben venir de la BD; el flujo usa `get_db` y escribe en `pagos_whatsapp` y `pagos_informes`. No hay stubs en este flujo.

---

## 5. Configuración y reglas (informe pagos)

- **Origen:** Tabla `configuracion`, clave `informe_pagos_config`, valor JSON.  
- **Sincronización:** `informe_pagos_config_holder.sync_from_db()` carga ese JSON en memoria; lo llaman Drive, Sheets, OCR y endpoints de configuración.  
- **Campos críticos para “no procesa / no Sheet”:**  
  - **Drive:** `google_drive_folder_id` + credenciales (JSON o OAuth).  
  - **Sheets:** `google_sheets_id` + credenciales; opcional `sheet_tab_principal`.  
  - **OCR:** Mismas credenciales; scope Vision incluido en OAuth; opcional `ocr_keywords_numero_documento`.  

Si **Drive** funciona pero **Sheets** no, lo más habitual es: `google_sheets_id` vacío, credenciales sin acceso a la hoja, o pestaña equivocada (revisar sección 2.2 y 2.3).

---

## 6. Checklist de diagnóstico (archivo en Drive, no en Sheet)

1. **Logs del backend** (Render u otro) en el momento de enviar la foto:  
   - Buscar `[INFORME_PAGOS]` y `[INFORME_PAGOS] FALLO`.  
   - Si aparece `digitalización fallida (Drive/OCR/BD/Sheet)` con excepción de BD (p. ej. `column "X" does not exist`) → aplicar migraciones (sección 2.1).  
   - Si aparece `Sheets no escribió fila (BD OK)` o `Sheets append error` → revisar Sheets (sección 2.2 y 2.3).

2. **Estado de conexiones:**  
   `GET /api/v1/configuracion/informe-pagos/estado` (con token de usuario).  
   - `drive.conectado`, `sheets.conectado`, `ocr.conectado` en `true`.  
   - Si `sheets.conectado === false`, leer `sheets.detalle` (ej. “google_sheets_id vacío”, “Sin permiso”).

3. **Base de datos:**  
   - Comprobar que existen todas las columnas de `pagos_whatsapp` y `pagos_informes` (ver `docs/VERIFICACION_OCR_MVP.md` y modelos en `backend/app/models/`).  
   - Ejecutar `migracion_mvp_ocr_todas_columnas.sql` si falta alguna.

4. **Configuración informe pagos (UI):**  
   - ID carpeta Drive, ID hoja Sheets, credenciales (o OAuth conectado).  
   - Opcional: “Pestaña donde escribir” = `Hoja 1` (o la pestaña que se revise).

5. **Flujo completo de prueba:**  
   Enviar una foto de papeleta por WhatsApp (tras cédula y confirmación) y comprobar en el mismo momento:  
   - Que no haya 500 en el webhook.  
   - Que aparezca fila en `pagos_informes` (y en `pagos_whatsapp`).  
   - Que aparezca la fila en la pestaña esperada de Google Sheets.

---

## 7. Resumen de auditoría

| Área | Estado | Notas |
|------|--------|--------|
| Orden del flujo (WhatsApp → Drive → BD → Sheet) | Correcto | Drive se ejecuta antes que commit BD; si BD falla, el archivo ya está en Drive. |
| OCR (Vision) | Integrado | Se llama siempre; si falla, se usan "NA" y el flujo sigue. |
| Endpoints | Correctos | Webhook + configuración y estado; no falta endpoint para el flujo. |
| Fallo Sheets silencioso | Riesgo | `append_row` no lanza; si falla, solo log y respuesta “OK” al usuario. |
| Migraciones BD | Crítico | Columnas faltantes explican “Drive OK, no procesa, no Sheet”. |
| Configuración Sheets | Crítico | `google_sheets_id` y permisos deben estar correctos para que llegue a Sheet. |

**Recomendación prioritaria:** Aplicar migraciones de BD y verificar en **Configuración > Informe pagos** el estado de Drive, Sheets y OCR y el ID de la hoja + pestaña. Revisar logs en el instante del envío para distinguir fallo de BD vs fallo de Sheets.
