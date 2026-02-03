# Verificación OCR / Informe de pagos (MVP)

Comprueba que no falten columnas, procesos ni configuración para que el flujo de OCR (foto de papeleta por WhatsApp → Drive → OCR → BD → Google Sheets) funcione en producción.

---

## 1. Base de datos: tablas y columnas

### 1.1 `pagos_informes`

Todas estas columnas deben existir (el modelo `PagosInforme` las usa):

| Columna           | Tipo           | Uso |
|-------------------|----------------|-----|
| id                | SERIAL PK      | — |
| cedula            | VARCHAR(20)    | Del flujo WhatsApp |
| fecha_deposito    | VARCHAR(50)    | OCR |
| nombre_banco      | VARCHAR(255)   | OCR |
| numero_deposito   | VARCHAR(100)   | OCR |
| numero_documento   | VARCHAR(100)   | OCR (palabras clave) |
| cantidad          | VARCHAR(50)    | OCR |
| humano            | VARCHAR(20)    | "HUMANO" si >80% texto baja confianza |
| link_imagen       | TEXT           | URL Google Drive |
| observacion       | TEXT           | Ej. "No confirma identidad" |
| pagos_whatsapp_id | INTEGER FK     | Referencia a pagos_whatsapp |
| periodo_envio    | VARCHAR(20)    | 6am, 1pm, 4h30 |
| fecha_informe     | TIMESTAMP      | — |
| created_at       | TIMESTAMP      | — |

**Si falta alguna:** ejecutar `backend/sql/migracion_pagos_informes_columnas_faltantes.sql` o el script unificado `backend/sql/migracion_mvp_ocr_todas_columnas.sql`.

### 1.2 `conversacion_cobranza`

Necesarias para el flujo cobranza (cédula → confirmación → foto):

| Columna             | Tipo           | Uso |
|---------------------|----------------|-----|
| id, telefono, cedula, estado, intento_foto | (existentes) | — |
| nombre_cliente      | VARCHAR(100)   | Nombre del cliente (desde BD) |
| intento_confirmacion | INTEGER        | Intentos Sí/No (máx. 3) |
| observacion         | TEXT           | Ej. "No confirma identidad" |
| created_at, updated_at | TIMESTAMP   | — |

**Si faltan:** ejecutar `backend/sql/migracion_confirmacion_identidad.sql`.

### 1.3 `pagos_whatsapp`

| Columna         | Tipo    | Uso |
|-----------------|---------|-----|
| id, fecha, cedula_cliente, imagen | (existentes) | — |
| link_imagen     | TEXT    | URL de la imagen en Google Drive |

**Si falta link_imagen:** ejecutar `backend/sql/migracion_pagos_whatsapp_link_imagen.sql` (o el script unificado).

### 1.4 `configuracion`

Tabla clave-valor con al menos la fila `informe_pagos_config` (clave) y el JSON en `valor`. Se crea/actualiza desde **Configuración > Informe pagos** en el frontend.

---

## 2. Procesos y dependencias

### 2.1 Configuración Informe pagos

- **Dónde:** Configuración > Informe pagos (frontend).
- **Persistencia:** tabla `configuracion`, clave `informe_pagos_config`, valor JSON.
- **Campos relevantes para OCR:**  
  - **Credenciales Google:** `google_credentials_json` (cuenta de servicio) **o** OAuth (`google_oauth_*` + "Conectar con Google").  
  - **Vision/OCR:** usa las mismas credenciales; no hay clave aparte.  
  - **Opcional:** `ocr_keywords_numero_documento` (palabras clave para número de documento); si no se configura, se usan valores por defecto.

### 2.2 Google Cloud (Vision API)

- **Requisito:** Vision API habilitada en el proyecto de Google Cloud y facturación activa.
- **Credenciales:**  
  - Cuenta de servicio: JSON con `client_email` y `private_key` en Informe pagos.  
  - OAuth: "Conectar con Google" con los scopes Drive, Sheets y **cloud-vision** (ya incluidos en el backend).

### 2.3 Flujo de la imagen (resumen)

1. WhatsApp recibe imagen → `whatsapp_service._process_image_message`.
2. Descarga bytes → OCR con `extract_from_image` (Vision).
3. Si no hay credenciales Vision, OCR devuelve todo "NA" pero el flujo sigue; la fila se guarda en BD con NA y opcionalmente en Sheets.
4. Subida a Drive (`upload_image_and_get_link`) → si falla, se guarda `link_imagen = "NA"`.
5. Insert en `pagos_whatsapp` y en `pagos_informes`.
6. `append_row` a Google Sheets (pestaña por periodo); si Sheets no está configurado o falla, solo se registra en logs y la digitalización en BD queda OK.

Ningún paso “no definido”: todos los caminos tienen manejo de error y respuesta al usuario.

### 2.4 Endpoints y routers

- **Configuración informe pagos:** incluida en `app.api.v1.endpoints.configuracion` con prefijo `/informe-pagos`.  
- **Estado de conexiones:** `GET /api/v1/configuracion/informe-pagos/estado` devuelve `drive`, `sheets`, `ocr` (conectado/detalle). Útil para verificar que OCR (Vision) esté operativo.

---

## 3. Comprobaciones rápidas

1. **Columnas en BD:** ejecutar el script unificado una vez en producción:
   ```bash
   psql "<DATABASE_URL>" -f backend/sql/migracion_mvp_ocr_todas_columnas.sql
   ```
2. **Estado OCR/Drive/Sheets:** en el frontend, Configuración > Informe pagos y revisar el estado de conexiones, o:
   ```http
   GET /api/v1/configuracion/informe-pagos/estado
   ```
   (con token de usuario). Debe devolver `ocr.conectado: true` si Vision está bien configurado.
3. **Flujo real:** enviar una foto de papeleta por WhatsApp tras cédula y confirmación; revisar que no haya error 500 y que aparezca fila en `pagos_informes` (y opcionalmente en la hoja de cálculo).

---

## 3.1 Por qué no funciona el OCR (diagnóstico)

Si el OCR no extrae datos (todo sale "NA" o la imagen se considera "no clara" siempre), revisar en este orden:

| # | Comprobación | Dónde / Cómo |
|---|----------------|---------------|
| 1 | **Credenciales Google** | **Configuración > Informe pagos.** Debe haber **o bien** JSON de cuenta de servicio (pegado en "Credenciales Google") **o bien** OAuth: Client ID, Client Secret y haber hecho clic en "Conectar con Google" para obtener el refresh token. Si no hay ninguna, el OCR devuelve todo NA. |
| 2 | **Estado OCR en la app** | En Configuración > Informe pagos, revisar el **estado de conexiones** (Drive, Sheets, OCR). O llamar `GET /api/v1/configuracion/informe-pagos/estado` (con token). El campo `ocr` tiene `conectado: true/false` y `detalle` con el mensaje exacto (ej. "Sin credenciales", "Token OAuth expirado", "Vision API no habilitada"). |
| 3 | **Vision API habilitada** | En [Google Cloud Console](https://console.cloud.google.com/) → tu proyecto → **APIs y servicios** → **Biblioteca** → buscar "Cloud Vision API" → **Habilitar**. |
| 4 | **Facturación activa** | Vision API requiere una cuenta de facturación vinculada al proyecto (aunque haya créditos gratuitos). En Cloud Console → Facturación. |
| 5 | **Proyecto correcto** | Si usas cuenta de servicio, el JSON debe ser del **mismo proyecto** donde habilitaste Vision API. Si usas OAuth, la cuenta de Google con la que autorizaste debe tener acceso al proyecto que tiene Vision habilitada. |

**Logs en Render:** al enviar una foto, si el OCR no tiene credenciales verás: `"OCR: credenciales Google (Vision) no configuradas"`. Si Vision devuelve error: `"OCR: Vision API devolvió error"` con el mensaje de la API.

---

## 4. Resumen: qué puede impedir que el OCR funcione en MVP

| Problema | Síntoma | Solución |
|----------|---------|----------|
| Columna faltante en `pagos_informes` | `ProgrammingError: column "X" does not exist` | Ejecutar `migracion_pagos_informes_columnas_faltantes.sql` o `migracion_mvp_ocr_todas_columnas.sql` |
| Columna faltante en `conversacion_cobranza` | Error al guardar/actualizar conversación | Ejecutar `migracion_confirmacion_identidad.sql` o script unificado |
| Sin credenciales Google (Vision) | OCR devuelve todo "NA"; estado OCR "Sin credenciales" | Configurar cuenta de servicio u OAuth en Informe pagos |
| Vision API no habilitada / sin facturación | Estado OCR "Vision API no habilitada o sin permiso" | Activar Vision API y facturación en Google Cloud |
| Config no guardada | `informe_pagos_config` no existe en `configuracion` | Guardar al menos una vez la configuración en Configuración > Informe pagos |

No hay procesos “no definidos”: el flujo está implementado de extremo a extremo; los fallos son por configuración o por esquema de BD desactualizado.

---

## 5. Mensaje «No pudimos procesar tu imagen» y nada en Drive

Cuando el usuario recibe ese mensaje y **no aparece nada en Drive**, el flujo se cortó **antes** de subir la imagen o **durante** la subida/guardado. La causa real se ve en los **logs del backend** (p. ej. Render).

### 5.1 Causas posibles (orden de ejecución)

| Causa | Log típico (buscar en Render) | Qué hacer |
|------|-------------------------------|-----------|
| **Token WhatsApp no configurado** | `no_digitaliza=image_skipped` / "Token no configurado" | Configuración > WhatsApp: guardar Access token. |
| **Meta no devolvió URL de la imagen** | `no_digitaliza=image_no_url` / "Meta no devolvió URL" | Reintentar; si persiste, revisar app Meta/WhatsApp Business. |
| **Error al descargar la imagen** | `no_digitaliza=image_error` / "error descargando imagen" + excepción | Conectividad Render con graph.facebook.com; timeout 30 s. |
| **Imagen vacía** | `no_digitaliza=image_empty` | Revisar que el webhook reciba bien el media_id. |
| **Fallo en digitalización (Drive/BD/Sheet)** | "Digitalización fallida (Drive/OCR/BD/Sheet)" + excepción | Drive: carpeta/credenciales/OAuth. BD: columna faltante. Sheets: opcional. |

Si hay excepción no capturada, en el log aparecerá `Error procesando mensaje WhatsApp:` con el traceback.

### 5.2 Cómo localizar la causa en Render

1. Servicio en Render → **Logs**.
2. **Búsqueda recomendada:** `INFORME_PAGOS` — muestra todo el flujo de imagen (inicio, descarga, OCR, Drive, BD, Sheets). Para solo fallos: `INFORME_PAGOS FALLO` o `FALLO`.
3. Cada línea incluye `telefono=***` (enmascarado), `status=`, `note=` o `error=` según el caso.
4. Si el error es de BD (p. ej. columna no existe), ejecutar `migracion_mvp_ocr_todas_columnas.sql`.

### 5.3 Resumen

**Nada en Drive** + "No pudimos procesar" = el flujo no llegó a subir o falló antes de confirmar. Revisar **logs en el instante del envío** para ver si fue: token, descarga (Meta/red), o Drive/BD/Sheet.

---

## 6. Estado del checklist (según tu verificación)

Con lo que comprobaste en Google, en la app y en Drive, este es el estado de la lista. Marca ✅ lo que ya verificaste; lo que no tenga ✅ sigue pendiente de comprobar si algo falla.

| # | Comprobación | Estado | Nota |
|---|------------------------------|--------|------|
| 1 | Credenciales Google (OAuth o cuenta de servicio) | ✅ | OAuth conectado; estado Drive/Sheets/OCR operativos. |
| 2 | Estado OCR en la app (Verificar ahora) | ✅ | "Conexión correcta. Vision API (OCR) operativa." |
| 3 | Vision API habilitada en Google Cloud | ✅ | Cloud Vision API → "API habilitada". |
| 4 | Facturación activa en el proyecto GCP | ✅ | Facturación → "Cuenta pagada" (proyecto cobranzas-485720). |
| 5 | Proyecto correcto (mismo que Vision/credenciales) | ✅ | Implícito: estado OCR OK y archivos en Drive. |
| 6 | Columnas BD (pagos_informes, etc.) | ✅ | Migración aplicada; imágenes llegan a Drive y se guardan. |
| 7 | Token WhatsApp configurado | ✅ | Cuando hay imagen en Drive, la descarga desde Meta funcionó. |
| 8 | Descarga de imagen desde Meta | ✅ | En los envíos que acaban en Drive, la descarga funciona. |
| 9 | Flujo real: foto → Drive + BD + Sheets | ✅ | Carpeta Pagos_imagenes con papeleta_*.jpg; flujo operativo. |

**Resumen:** Todo lo de la lista está **destacado (verificado)**. Si en algún envío concreto el usuario sigue viendo "No pudimos procesar" y no aparece archivo en Drive, en ese caso revisar los logs de Render en ese momento (sección 5) para ver la causa puntual (p. ej. timeout o error puntual de Meta).
