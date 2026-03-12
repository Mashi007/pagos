# Verificación: Cómo se guarda la plantilla PDF y se adjunta al email

## Resumen

La plantilla del PDF de cobranza (pestaña "Plantilla anexo PDF") se **guarda en la base de datos** en la tabla `configuracion` con clave **`plantilla_pdf_cobranza`**. Cuando se produce el envío de una notificación de tipo COBRANZA, el backend **lee esa misma plantilla**, genera un PDF por cada email y lo adjunta al correo.

---

## 1. Guardado de la plantilla (persistencia)

### Frontend
- **Componente:** `PlantillaAnexoPdf.tsx` (pestaña "Plantilla anexo PDF" en Plantillas).
- **Al hacer clic en "Guardar plantilla PDF":**
  - Llama a `notificacionService.updatePlantillaPdfCobranza({ ciudad_default, cuerpo_principal, clausula_septima })`.
- **Servicio:** `notificacionService.ts`
  - `updatePlantillaPdfCobranza(data)` → **PUT** `/api/v1/notificaciones/plantilla-pdf-cobranza` con body JSON.

### Backend
- **Endpoint:** `notificaciones.py` → `update_plantilla_pdf_cobranza` (PUT `/plantilla-pdf-cobranza`).
- **Qué hace:**
  1. Recibe `ciudad_default`, `cuerpo_principal`, `clausula_septima` (opcionales).
  2. Busca o crea la fila en la tabla **`configuracion`** con **`clave = "plantilla_pdf_cobranza"`**.
  3. Guarda en **`valor`** un JSON con esas tres claves.
  4. Ejecuta **`db.commit()`** → la plantilla queda persistida en BD.

```text
Tabla: configuracion
  clave  = "plantilla_pdf_cobranza"
  valor  = '{"ciudad_default":"Guacara","cuerpo_principal":"...","clausula_septima":"..."}'
```

---

## 2. Uso al producir la notificación (adjunto al email)

### Cuándo se usa
- Al enviar notificaciones desde las pestañas (previas, día pago, retrasadas, prejudicial, mora 90) **si** el tipo de notificación tiene asignada una **plantilla de tipo COBRANZA** y la configuración de envíos tiene **`incluir_pdf_anexo`** activo (por defecto sí).

### Backend – flujo por cada email
- **Archivo:** `notificaciones_tabs.py` → función `_enviar_correos_items`.
- Para cada ítem (cliente/cuota) con plantilla COBRANZA y `contexto_cobranza`:
  1. **Generar PDF:**  
     `pdf_bytes = generar_carta_cobranza_pdf(item["contexto_cobranza"], db=db)`
  2. **Adjuntar:**  
     `attachments.append(("Carta_Cobranza.pdf", pdf_bytes))`
  3. **Enviar correo:**  
     `send_email(..., attachments=attachments)`

### De dónde sale el contenido del PDF
- **Archivo:** `carta_cobranza_pdf.py`
- **Función:** `generar_carta_cobranza_pdf(contexto_cobranza, db, logo_path)`:
  1. Llama a **`_get_plantilla_pdf_config(db)`**, que:
     - Lee la fila de **`configuracion`** con **`clave = "plantilla_pdf_cobranza"`**.
     - Parsea `valor` como JSON y devuelve `{ ciudad_default, cuerpo_principal, clausula_septima }`.
  2. Con esa plantilla y el `contexto_cobranza` (datos del cliente/cuotas), llama a **`build_pdf_bytes(...)`** y devuelve los bytes del PDF.
- **Conclusión:** El PDF que se adjunta al email se genera **siempre** con la plantilla guardada en `configuracion` bajo la clave **`plantilla_pdf_cobranza`** (la misma que se actualiza al guardar desde la pestaña 2).

---

## 3. Cadena completa (misma clave)

| Paso | Dónde | Clave / Acción |
|------|--------|-----------------|
| Guardar plantilla | `notificaciones.py` → `update_plantilla_pdf_cobranza` | Escribe en `configuracion` con **clave = "plantilla_pdf_cobranza"** |
| Generar PDF al enviar | `carta_cobranza_pdf.py` → `_get_plantilla_pdf_config(db)` | Lee de `configuracion` con **clave = "plantilla_pdf_cobranza"** |
| Adjuntar al email | `notificaciones_tabs.py` → `_enviar_correos_items` | Llama a `generar_carta_cobranza_pdf(..., db=db)` y pasa los bytes a `send_email(..., attachments=...)` |

---

## 4. Comprobaciones rápidas

1. **Guardado:** Tras "Guardar plantilla PDF", revisar en BD que existe una fila en `configuracion` con `clave = 'plantilla_pdf_cobranza'` y `valor` con JSON válido.
2. **Vista previa:** El botón "Vista previa (datos de ejemplo)" usa la misma función `generar_carta_cobranza_pdf(..., db=db)`; si la vista previa muestra el contenido esperado, la plantilla guardada es la que se usará al enviar.
3. **Envío:** Al disparar el envío de notificaciones con plantilla COBRANZA y `incluir_pdf_anexo` activo, cada correo debe llevar adjunto `Carta_Cobranza.pdf` generado con la plantilla actual de `plantilla_pdf_cobranza`.
