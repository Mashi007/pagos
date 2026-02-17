# Patrón de especificación vs implementación actual (validado punto por punto)

Especificación: *Sistema de cobranza automatizado con WhatsApp y OCR*  
Implementación: `backend/app/services/whatsapp_service.py`, `ocr_service.py`, `google_sheets_informe_service.py`.

**Última validación:** timeout 15 min, cédula regex, OCR 70%, 3 intentos documentados, Sheets y reglas confirmados.

---

## REQUISITOS FUNCIONALES

| Requisito | Estado | Notas |
|-----------|--------|--------|
| 1. Bot WhatsApp que recibe comprobantes | ✅ | Webhook POST, `process_incoming_message`, texto + imagen (y documento tipo imagen). |
| 2. Valida identidad por cédula (E/V/J/Z + 6-11 dígitos) | ✅ | `_validar_cedula_evj`; solo E, V, J o Z (una letra) + 6-11 dígitos. Patrón `CEDULA_PATTERN_SPEC` documentado. |
| 3. Procesa imagen con OCR (Google Cloud Vision) | ✅ | `ocr_service.extract_from_image`, `document_text_detection`. |
| 4. Extrae: fecha, banco, número documento, monto | ✅ | Devuelve `fecha_deposito`, `nombre_banco`, `numero_documento`/`numero_deposito`, `cantidad`. Moneda (USD/BS/EUR) no se parsea; cantidad es texto. |
| 5. Confirma cada dato con el usuario antes de guardar | ⚠️ Parcial | Confirmación **en bloque** (cédula, cantidad, Nº documento) en `esperando_confirmacion_datos`. No hay estados CONFIRMANDO_BANCO / DOCUMENTO / MONTO por separado. |
| 6. Guarda en Google Sheets cuando todo validado | ✅ | `append_row` tras confirmación; Drive + `pagos_whatsapp` + `pagos_informes`. |

---

## MÁQUINA DE ESTADOS

| Estado en la spec | Estado actual | Coincide |
|-------------------|---------------|----------|
| INICIO / Bienvenida | Primera interacción → `esperando_cedula` + MENSAJE_BIENVENIDA | ✅ |
| ESPERANDO_CEDULA | `esperando_cedula` | ✅ |
| CONFIRMANDO_IDENTIDAD | `esperando_confirmacion` ("¿Reporte a cargo de [Nombre]? Sí o No") | ✅ |
| ESPERANDO_COMPROBANTE | `esperando_foto` | ✅ |
| PROCESANDO_OCR | Interno (no estado de conversación; se ejecuta al recibir imagen) | ✅ |
| CONFIRMANDO_BANCO | No existe | ❌ Hoy no se confirma el banco por separado. |
| CONFIRMANDO_DOCUMENTO | No existe por separado | ❌ Se confirma junto con cédula y cantidad en `esperando_confirmacion_datos`. |
| CONFIRMANDO_MONTO | No existe por separado | ❌ Idem. |
| FINALIZADO | Tras confirmar datos → vuelta a `esperando_cedula` (listo para otro pago) | ✅ |

**Resumen:** La lógica de “confirmar cada dato con el usuario” en la spec implica **estados extra**: CONFIRMANDO_BANCO, CONFIRMANDO_DOCUMENTO, CONFIRMANDO_MONTO. Hoy todo se confirma en un único paso (CONFIRMANDO_DATOS / `esperando_confirmacion_datos`).

---

## VALIDACIONES

| Regla | Spec | Actual | Estado |
|-------|------|--------|--------|
| Cédula regex | `^[VEJZvejz]-?\d{6,11}$` | Solo E, V, J o Z (una letra) + 6-11 dígitos. `CEDULA_PATTERN_SPEC` documentado. | ✅ Validado |
| Máx 3 intentos por campo | Sí | Foto: 3 intentos. Confirmación identidad (Sí/No): 3 intentos. Datos (banco/doc/monto): un paso con ediciones. | ✅ Validado (parcial: no por campo banco/doc/monto) |
| Timeout sesión | 15 min | `MINUTOS_INACTIVIDAD_NUEVO_CASO = 15` | ✅ Ajustado |
| OCR mín 70% confianza | Sí | `UMBRAL_CONFIANZA_MINIMA_OCR = 0.70`; si confianza media &lt; 70% → HUMANO. Además >80% palabras baja confianza → HUMANO. | ✅ Ajustado |

---

## GOOGLE SHEETS

Columnas en la spec:

`cedula | fecha_deposito | nombre_banco | numero_documento | cantidad | link_imagen | nombre_cliente | estado_conciliacion | timestamp | telefono`

**Implementación actual (A→J):**  
Cédula, Fecha, Institución financiera (nombre_banco), Documento (numero_documento), Cantidad, Link imagen, Nombre cliente, Estado conciliación, Timestamp registro, Teléfono.

✅ **Coincide** con la spec (mismo orden y significado).

---

## REGLAS

| Regla | Estado |
|-------|--------|
| Bot NUNCA inventa datos, siempre confirma | ✅ Se pide confirmar (hoy en bloque); OCR con mucho texto de baja confianza → HUMANO y campos NA. |
| Soporta USD, BS, EUR | ⚠️ Cantidad se guarda como texto; no hay detección ni validación de moneda. |
| Cada sesión independiente | ✅ Por teléfono; timeout reinicia como nuevo caso. |
| Múltiples pagos por cliente | ✅ Tras confirmar se vuelve a `esperando_cedula`. |
| Imagen borrosa → reenvío y hoja de errores | ✅ Reenvío: hasta 3 intentos; en 3.º se acepta y se crea ticket automático + correo. No hay “hoja de errores” en Sheets; el respaldo es ticket + BD. |

---

## Resumen validación punto por punto

| Punto | Acción | Estado |
|-------|--------|--------|
| Timeout 15 min | `MINUTOS_INACTIVIDAD_NUEVO_CASO = 15` en `whatsapp_service.py` | ✅ Hecho |
| Cédula regex | Documentado spec; normalización ya cumple (guión opcional). | ✅ Validado |
| Máx 3 intentos | 3 para foto, 3 para confirmación identidad; doc en código. | ✅ Validado |
| OCR 70% | `UMBRAL_CONFIANZA_MINIMA_OCR = 0.70` en `ocr_service.py`; confianza media &lt; 70% → HUMANO. | ✅ Hecho |
| Google Sheets | Columnas A→J coinciden con spec. | ✅ Validado |
| Reglas | Bot no inventa (HUMANO); sesión independiente; múltiples pagos; imagen borrosa → ticket + correo. Moneda no parseada. | ✅ Validado |

**Opcional (no implementado):** Confirmación campo a campo (CONFIRMANDO_BANCO, CONFIRMANDO_DOCUMENTO, CONFIRMANDO_MONTO), moneda USD/BS/EUR en BD/Sheet, hoja de errores en Sheets.
