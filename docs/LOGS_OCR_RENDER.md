# Logs OCR en Render – Dónde está el error

Guía para localizar fallos en el proceso OCR/comunicaciones en [RapiCredit](https://rapicredit.onrender.com/pagos/comunicaciones) usando los logs del backend en Render.

---

## 1. Búsquedas recomendadas en Render

En el panel de **Logs** del servicio backend en Render, usa estos filtros:

| Objetivo | Buscar |
|----------|--------|
| Todo el flujo de imagen/OCR | `INFORME_PAGOS` |
| Solo errores/fallos | `INFORME_PAGOS FALLO` o `FALLO` |
| Inicio del flujo por imagen | `FLUJO_OCR INICIO` |
| Paso 1: descarga de imagen | `Imagen descargada` o `image_error` / `image_no_url` |
| Paso 2: OCR (Vision) | `[OCR]` o `extract_from_image` |
| Paso 3: Drive | `Drive upload` |
| Paso 4–5: BD y Sheet | `Digitalizando` / `pagos_whatsapp guardado` / `Escribiendo Sheet` / `append_row` |
| Paso 6: confirmación de datos | `esperando_confirmacion_datos` / `Confirmación datos` |
| Fallo global de digitalización | `digitalización fallida` |

---

## 2. Orden típico de mensajes (flujo correcto)

Si todo va bien, deberías ver algo como esto **en el mismo minuto** (por un mismo envío de foto):

1. `[INFORME_PAGOS] FLUJO_OCR INICIO | pasos: 1=descarga 2=OCR 3=Drive 4=BD 5=Sheet 6=confirmacion | telefono=...`
2. `[INFORME_PAGOS] Inicio procesamiento imagen | telefono=... media_id=... cedula=...`
3. `[INFORME_PAGOS] Imagen descargada | telefono=... bytes=...`
4. `[INFORME_PAGOS] [OCR] INICIO extract_from_image | telefono=...`
5. `[INFORME_PAGOS] [OCR] Paso 1/4: sync_from_db...` → luego `Paso 1/4 OK` o `Paso 1/4 FALLO`
6. `[INFORME_PAGOS] [OCR] Paso 2/4...` / `Paso 3/4...` / `Paso 4/4...` (según si es get_full_text o extract)
7. `[INFORME_PAGOS] [OCR] RESULTADO extract_from_image | telefono=... banco=... fecha=...`
8. `[INFORME_PAGOS] [OCR] Decisión por OCR: aceptable=...`
9. `[INFORME_PAGOS] Digitalizando (Drive+BD+Sheet) | telefono=...`
10. `[INFORME_PAGOS] Drive upload INICIO | filename=... bytes=...`
11. `[INFORME_PAGOS] Drive upload OK | file_id=...`
12. `[INFORME_PAGOS] pagos_whatsapp guardado | id=... telefono=...`
13. `[INFORME_PAGOS] OK digitalización completa | pagos_whatsapp_id=... pagos_informe_id=...`
14. `[INFORME_PAGOS] Escribiendo Sheet | telefono=...`
15. `[INFORME_PAGOS] Sheets append_row OK | cedula=... tab=...`
16. `[INFORME_PAGOS] FLUJO_OCR OK hasta Sheet | estado=esperando_confirmacion_datos informe_id=...`

Si el usuario luego escribe **SÍ** o corrige datos:

17. `[INFORME_PAGOS] Confirmación datos: estado=esperando_confirmacion_datos informe_id=...`
18. `[INFORME_PAGOS] Confirmación datos: cliente confirmó SÍ` **o** `cliente editó campos | informe_id=... campos=[...]`
19. Si editó: `[INFORME_PAGOS] Sheets update_row INICIO | informe_id=...` y luego `Sheets update_row OK`

---

## 3. Dónde se corta el flujo (diagnóstico rápido)

| Último log que ves | Probable causa |
|--------------------|----------------|
| `FLUJO_OCR INICIO` pero no `Imagen descargada` | Token WhatsApp, media_id, o fallo de red/Meta al descargar. Busca `image_error`, `image_no_url`, `image_empty`. |
| `Imagen descargada` pero no `[OCR] RESULTADO` | Fallo en Vision (credenciales, API no habilitada). Busca `[OCR] Paso 1/4 FALLO` o `Paso 2/4 FALLO` o `FALLO extract_from_image`. |
| `[OCR] RESULTADO` pero no `Digitalizando` | OCR decidió “no aceptable” y no es 3.º intento. Busca `Imagen no aceptada` / `photo_retry`. |
| `Digitalizando` pero no `Drive upload OK` | Carpeta Drive o credenciales. Busca `Drive upload error` o `Drive no configurado`. |
| `Drive upload OK` pero no `OK digitalización completa` | Error en BD (p. ej. columna faltante). Busca `digitalización fallida` y el traceback. |
| `OK digitalización completa` pero no `Sheets append_row OK` | Sheet no configurado o permisos. Busca `Sheets append error` o `Sheets no configurado`. |
| `FLUJO_OCR OK hasta Sheet` pero el usuario no ve mensaje | Envío a WhatsApp o estado `esperando_confirmacion_datos`; revisar `Confirmación datos` y respuesta enviada. |

---

## 4. Niveles de log

- **INFO**: flujo normal (pasos, IDs, telefono enmascarado).
- **WARNING**: configuración faltante, respuesta inesperada, fallback (p. ej. IA no disponible).
- **ERROR/EXCEPTION**: excepciones; en Render suelen incluir traceback.

En producción conviene tener al menos **INFO** para el tag `[INFORME_PAGOS]` para poder seguir todo el flujo y usar esta guía.
