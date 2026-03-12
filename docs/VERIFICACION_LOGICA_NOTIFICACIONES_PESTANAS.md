# Verificación lógica: /pagos/notificaciones (envío por pestaña)

**Lógica que se quería verificar:** En cada pestaña, cuando hay un cliente al que debe mandársele notificación, el sistema: (1) toma la plantilla asignada a esa pestaña (email con variables por cliente), (2) adjunta PDF con variables específicas, (3) adjunta PDF fijo (sin variables), (4) envía el correo.

---

## Qué hace el código hoy

Origen: `backend/app/api/v1/endpoints/notificaciones_tabs.py`, función `_enviar_correos_items`.

### 1. Plantilla asignada por pestaña (email con variables por cliente)

- **Sí está implementado.** Para cada ítem (cliente) se obtiene el `tipo` según la pestaña (p. ej. `PAGO_5_DIAS_ANTES`, `PAGO_3_DIAS_ANTES`, `PAGO_DIA_0`, `PAGO_1_DIA_ATRASADO`, `PREJUDICIAL`, `MORA_90`).
- La configuración de envíos (`notificaciones_envios` en BD) tiene **por tipo** un `plantilla_id`. Ese es el “por pestaña” (cada tipo/pestaña tiene su plantilla asignada).
- Se llama a `get_plantilla_asunto_cuerpo(db, plantilla_id, item, asunto_base, cuerpo_base, ...)` y se obtienen **asunto y cuerpo con variables sustituidas por ese cliente** (nombre, cédula, fecha_vencimiento, monto, etc.). Si no hay plantilla_id o no hay plantilla, se usan asunto_base/cuerpo_base con variables sustituidas.
- Ese par (asunto, cuerpo) es el email que se envía. **Orden: primero el email (plantilla con variables por cliente).**

### 2. Adjuntar PDF con variables específicas

- **Solo se hace cuando la plantilla asignada a ese tipo es de tipo COBRANZA.**
- Código (resumen):
  - Si `plantilla_id` existe y la plantilla tiene `tipo == "COBRANZA"` y el ítem tiene `contexto_cobranza` (cuotas pendientes, etc.):
    - Se genera `Carta_Cobranza.pdf` con `generar_carta_cobranza_pdf(ctx_pdf, db=db)` (variables por cliente).
    - Ese PDF se añade a `attachments` como primer adjunto: `("Carta_Cobranza.pdf", pdf_bytes)`.
- Para pestañas/tipos que **no** usan una plantilla tipo COBRANZA (p. ej. “5 días antes”, “3 días antes”, “Día de pago”, “Retrasadas”, “Prejudicial”), **no se genera ni se adjunta ningún PDF con variables**. Solo se envía el email de la plantilla.

### 3. Adjuntar PDF fijo (sin variables)

- **Solo se hace cuando la plantilla asignada es de tipo COBRANZA.**
- Se usa `get_adjunto_fijo_cobranza_bytes(db)`, que devuelve **un solo** PDF fijo configurado en BD (clave `adjunto_fijo_cobranza`: nombre_archivo + ruta). Si existe, se añade a `attachments` **después** del PDF de carta de cobranza.
- **Los “Documentos PDF anexos” por caso** (Configuración → Plantillas → Documentos PDF anexos: dias_5, dias_3, dias_1, hoy, mora_90) están en la BD como `adjuntos_fijos_por_caso`. La función `get_adjuntos_fijos_por_caso(db, tipo_caso)` existe en `app/services/adjunto_fijo_cobranza.py`, pero **no se llama en el flujo de envío** de `notificaciones_tabs.py`. Por tanto, esos PDFs por caso **no se adjuntan** en el envío actual.

### 4. Envío

- Se llama a `send_email(to_email, asunto, cuerpo, body_html=body_html, bcc_emails=bcc_list, attachments=attachments)`.
- Orden real en el correo: (1) cuerpo del email (plantilla con variables por cliente), (2) si aplica, `Carta_Cobranza.pdf` (PDF con variables), (3) si aplica, el PDF fijo global de cobranza. No se añaden los PDFs de “Documentos PDF anexos” por caso.

---

## Resumen de coincidencias y diferencias

| Lo que describiste | Código actual |
|--------------------|----------------|
| Cada pestaña toma la plantilla asignada (email con variables por cliente) | **Sí.** `plantilla_id` por tipo y `get_plantilla_asunto_cuerpo(..., item)` con variables por cliente. |
| Luego adjunta PDF con variables específicas | **Solo si la plantilla de ese tipo es COBRANZA.** Para el resto de pestañas no se adjunta ningún PDF con variables. |
| Luego adjunta PDF fijo (sin variables) | **Sí, pero solo cuando la plantilla es COBRANZA**, y solo el **adjunto fijo global** (config `adjunto_fijo_cobranza`). Los PDFs de “Documentos PDF anexos” por caso (dias_5, dias_3, etc.) **no se usan** en el envío. |
| Y envía | **Sí.** `send_email(...)` con asunto, cuerpo y attachments en ese orden. |

---

## Preguntas para alinear con lo que quieres

1. **PDF con variables y PDF fijo en todas las pestañas**  
   Hoy solo se adjuntan cuando la plantilla asignada a esa pestaña es de tipo **COBRANZA**. ¿La idea es que en **todas** las pestañas (5 días antes, 3 días, día de pago, retrasadas, prejudicial, mora 90) se adjunte siempre un PDF con variables + un PDF fijo, o solo en la(s) pestaña(s) que usan plantilla de cobranza?

2. **“PDF fijo”**  
   ¿Debe ser solo el actual adjunto fijo global de cobranza, o también los **Documentos PDF anexos por caso** (los que se suben en Plantillas → Documentos PDF anexos para “5 dias”, “3 dias”, “1 dia”, “Hoy”, “Mora 90+”)? Hoy esos últimos no se adjuntan en el envío.

Cuando aclaremos estos dos puntos, se puede ajustar la lógica en `_enviar_correos_items` (y, si toca, en la config por tipo) para que coincida exactamente con el comportamiento que buscas.
