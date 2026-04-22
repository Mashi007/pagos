# Cobros: enfoques, actualizaciones y archivos (2026)

Documento de referencia para los cambios y decisiones alrededor del módulo **Cobros / pagos reportados**, rendimiento del listado y aprobación masiva en UI.

---

## 1. Envío de recibo por correo al aprobar

### Enfoque

- Objetivo: **aligerar** la aprobación desde el **listado** evitando SMTP en la misma petición (PDF grande + correo sumaba mucha latencia).
- Comportamiento fijo: **`PATCH /api/v1/cobros/pagos-reportados/{id}/estado`** con `estado: "aprobado"` **genera y guarda** el PDF del recibo y **no envía** correo al cliente (sin variable de entorno).
- **`POST /api/v1/cobros/pagos-reportados/{id}/aprobar`** (detalle, “Aprobar” final) **sí** intenta enviar el recibo por correo si el servicio Cobros está activo, como antes.
- **No cambia** rechazos, `POST .../enviar-recibo` manual ni otros correos.

### Archivos

| Archivo | Cambio |
|---------|--------|
| `backend/app/api/v1/endpoints/cobros/routes.py` | `cambiar_estado_pago` (aprobado): solo PDF persistido; sin SMTP en este endpoint. `POST .../aprobar` conserva envío de recibo. |

### Operación

No requiere configuración en el servidor para omitir correo en el listado: es el comportamiento por defecto del PATCH.

---

## 2. Rendimiento de `GET .../pagos-reportados/listado-y-kpis`

### Enfoque

El listado de la cola manual **recorre en Python** todas las filas que cumplen el `WHERE` para calcular `total`, KPIs (cuando aplica) y la página: el coste es **O(toda la cola)** por petición.

Mejoras aplicadas **sin cambiar la semántica** del listado:

1. **`include_financial_fields` en `_pago_reportado_list_items_from_rows`**  
   - En el **barrido masivo** (`include_financial_fields=False`): no se llama a `obtener_tasas_por_fechas` / `tasa_y_equivalente_usd_excel` por fila; solo se arma lo necesario para observación / Gemini y `_item_falla_validadores_cobros_excel`.  
   - Las filas de la **página actual** se vuelven a hidratar **una vez** con `include_financial_fields=True` para devolver tasa y equivalente USD en JSON como antes.

2. **Lote de escaneo**  
   - Constante `_COBROS_LISTADO_SCAN_BATCH` = **1200** (antes 400) en el bucle del listado y en el barrido de KPIs cuando no se reutilizan conteos del listado.

3. **Cache de mapas “primer”**  
   - `_PRIMER_MAPS_CACHE_TTL_SEC` de **30 s** a **90 s** para reducir recomputaciones del triple (normas documento, primer `numero_operacion`, presencia en `pagos`).

### Archivos

| Archivo | Cambio |
|---------|--------|
| `backend/app/api/v1/endpoints/cobros/routes.py` | Parámetro `include_financial_fields`; barrido con `False`; re-hidratación de página por IDs; batch 1200; TTL cache primer; export Excel y demás callers con default `True`. |

### Límites conocidos

Si la cola crece mucho, el cuello sigue siendo el **barrido completo** para `total` exacto. Siguiente escalón posible (no implementado aquí): conteos aproximados, materialización o acotar por fecha por defecto.

---

## 3. Columna Q (CONCILIACIÓN) y fechas (referencia de análisis)

### Enfoque (resumen)

- Sync Sheets usa **`UNFORMATTED_VALUE`**: fechas con formato de celda llegan como **serial numérico**, evitando confusión M/D vs D/M del texto formateado.
- Tabla `drive`: `col_q` se persiste como **texto** (`str` del valor); serial queda como cadena numérica.
- Comparación Q vs `fecha_aprobacion`: `comparar_fecha_entrega_q_aprobacion_service` — `_parse_fecha_celda_hoja` (serial + texto; texto ambiguo `dd/mm` con ambos ≤12 se interpreta en convención **VE** documentada en código).
- Carga masiva / candidatos: `parse_fecha_q_iso_y_ambigua` y validadores; fechas **ambigüas** en slash pueden **bloquearse** hasta ISO.

### Archivos de referencia (sin cambios en esa conversación)

- `backend/app/services/conciliacion_sheet_sync.py`
- `backend/app/services/comparar_fecha_entrega_q_aprobacion_service.py`
- `backend/app/services/prestamo_candidatos_drive_normalizacion.py`
- `backend/app/services/prestamo_candidatos_drive_guardar.py`
- `backend/app/models/drive.py`

---

## 4. Aprobación masiva en listado (checkboxes)

### Enfoque

- En **Pagos reportados** (`/cobros/pagos-reportados`): columna **Sel.**, selección solo **pendiente** / **en revisión** (alineado al “Aprobar” por fila).
- Cabecera: marcar/desmarcar **toda la página** seleccionable; estado indeterminado si hay selección parcial.
- Barra: **Aprobar seleccionados** (confirmación) → llamadas **secuenciales** a `cambiarEstadoPago(id, 'aprobado')` (misma API que el desplegable).
- Limpieza de selección al cambiar página o filtros; toasts de resumen (éxitos / fallos).

### Archivos

| Archivo | Cambio |
|---------|--------|
| `frontend/src/pages/CobrosPagosReportadosPage.tsx` | Columna checkbox, estado `selectedIds` / `bulkApproving`, barra de acción, `COBROS_REPORTADOS_COL_COUNT` = 11 y anchos por defecto, memos y handlers. |

### Notas UX

- Los fallos por fila (duplicado, sin tasa Bs., etc.) se acumulan en el resumen sin detener el resto del lote (orden secuencial).

---

## 5. Resumen de archivos tocados en código

| Ruta | Tema |
|------|------|
| `backend/app/api/v1/endpoints/cobros/routes.py` | PATCH aprobado sin SMTP listado; listado/KPIs rendimiento, items sin tasa en barrido. |
| `frontend/src/pages/CobrosPagosReportadosPage.tsx` | Aprobación masiva con checkboxes. |
| `docs/COBROS_ENFOQUES_Y_ACTUALIZACIONES.md` | Este documento. |

---

## 6. Pruebas recomendadas

1. **Correo recibo**: aprobar desde listado (PATCH) no envía correo; aprobar desde detalle (POST) sí intenta enviar si corresponde; `enviar-recibo` sigue disponible.
2. **Listado**: primera carga y cambio de página con cola grande; comparar tiempos antes/después en logs `elapsed_ms` de `listado-y-kpis`.
3. **Masivo**: seleccionar 2–3 pendientes, aprobar, verificar filas que salen de la vista y toasts; probar un caso que falle (p. ej. duplicado) y revisar mensaje de resumen.
