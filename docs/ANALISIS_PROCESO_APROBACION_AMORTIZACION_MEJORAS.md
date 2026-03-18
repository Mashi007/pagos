# Análisis del proceso: aprobación, fechas y amortización — mejoras posibles

## 1. Resumen del proceso actual

### 1.1 Flujos que generan o usan fecha de aprobación

| Origen | Acción | fecha_aprobacion | Coherencia (≥ fecha_requerimiento) |
|--------|--------|------------------|-------------------------------------|
| **Modal Nuevo Préstamo** | Crear (DRAFT) | No se asigna | N/A |
| **Aprobar manual** | `POST /{id}/aprobar-manual` | Payload; validación ≥ req | ✅ |
| **Asignar fecha** | `POST /{id}/asignar-fecha-aprobacion` | Payload; validación ≥ req | ✅ |
| **Aplicar condiciones** | `POST /{id}/aplicar-condiciones-aprobacion` | Si null → fecha_base_calculo o hoy; validación ≥ req | ✅ |
| **Carga masiva** | Create con `aprobado_por_carga_masiva` | = fecha_registro | Asumido coherente |
| **Revisión Manual** | PUT préstamo | Body (string YYYY-MM-DD) | ✅ Validación antes de commit |
| **PUT préstamo (API)** | `PUT /prestamos/{id}` | No se envía aquí; solo fecha_requerimiento | ✅ Validación si se cambia req |

### 1.2 Regla obligatoria de amortización

- **Tabla de amortización**: se calcula **únicamente con `fecha_aprobacion`**.
- No se usa `fecha_base_calculo` ni `fecha_requerimiento` como base de fechas de vencimiento.
- Si no hay `fecha_aprobacion`, no se generan cuotas (salvo scripts/endpoints que la asignan antes).

### 1.3 Puntos donde se generan cuotas

| Punto | Condición para generar | Base de fechas |
|-------|-------------------------|----------------|
| `create_prestamo` (modal nuevo) | Solo si hay `fecha_aprobacion` (carga masiva sí; DRAFT no) | `_fecha_aprobacion_para_amortizacion` |
| `POST /{id}/generar-amortizacion` | 400 si no hay fecha aprobación | `_fecha_aprobacion_para_amortizacion` |
| `POST /{id}/asignar-fecha-aprobacion` | Tras asignar fecha | Payload |
| `POST /{id}/aprobar-manual` | Tras aprobar con fecha | Payload |
| `POST /{id}/aplicar-condiciones-aprobacion` | Si no hay cuotas y hay fecha aprobación | `_fecha_aprobacion_para_amortizacion` |
| `PUT /prestamos/{id}` | Si estado=APROBADO, 0 cuotas y hay fecha aprobación | `_fecha_aprobacion_para_amortizacion` |
| `POST /generar-cuotas-aprobados-sin-cuotas` | Solo APROBADO sin cuotas; omite sin fecha_aprobacion | `_fecha_aprobacion_para_amortizacion` |
| Script `actualizar_amortizacion_mensual.py` | Solo MENSUAL con fecha_aprobacion | fecha_aprobacion (ya alineado) |
| Script `generar_cuotas_prestamos_sin_cuotas.py` | Sin cuotas; omite sin fecha_aprobacion | fecha_aprobacion |

---

## 2. Coherencia fecha_aprobacion ≥ fecha_requerimiento

- **Revisión Manual**: validación tras aplicar todos los campos; 400 si aprobación &lt; requerimiento.
- **PUT préstamo**: si se envía `fecha_requerimiento`, se valida que no sea posterior a `fecha_aprobacion`; 400 en caso contrario.
- **asignar-fecha-aprobacion / aprobar-manual / aplicar-condiciones**: validan antes de guardar.

Frontend (modales): valor por defecto de la fecha de aprobación = `fecha_requerimiento` cuando existe, para reducir errores.

---

## 3. Mejoras ya implementadas (resumen)

1. Validación de coherencia en **Revisión Manual** (revision_manual.py).
2. **PUT préstamo**: aplicación de `fecha_requerimiento` y validación frente a `fecha_aprobacion`.
3. **Modales** Asignar fecha y Aprobar manual: default de fecha = `fecha_requerimiento` si existe.
4. **actualizar_amortizacion_mensual.py**: detección de préstamos desactualizados solo con `fecha_aprobacion` (sin fallback a `fecha_base_calculo`).

---

## 4. Mejoras posibles (recomendaciones)

### 4.1 Regeneración de cuotas al cambiar condiciones (prioridad media)

- **Problema**: Si en **Revisión Manual** o en **PUT préstamo** se cambian `numero_cuotas`, `total_financiamiento`, `modalidad_pago` o `tasa_interes`, las cuotas ya existentes no se regeneran. La tabla de amortización puede quedar desalineada (ej.: préstamo con 24 cuotas y solo 12 en BD).
- **Opciones**:
  - **A**: Al guardar préstamo (Revisión Manual o PUT), si cambian esos campos y ya existen cuotas, devolver aviso tipo: *“Se modificaron condiciones que afectan la tabla de amortización. Para regenerar cuotas use [Asignar fecha / Generar amortización] o contacte a administración.”*
  - **B**: Endpoint o acción “Regenerar tabla de amortización” (borrar cuotas existentes y volver a generarlas con `fecha_aprobacion` y condiciones actuales), solo para admin o flujo controlado, con confirmación y posible impacto en pagos ya aplicados.

### 4.2 Aplicar condiciones: origen de fecha cuando no hay fecha_aprobacion (prioridad baja)

- **Situación**: En `aplicar-condiciones-aprobacion`, si `p.fecha_aprobacion` es `None`, se usa `payload.fecha_base_calculo` o `p.fecha_base_calculo` o `date.today()`. La amortización sigue calculándose con la fecha que se guarda en `fecha_aprobacion`, así que la regla “solo fecha_aprobacion” se cumple.
- **Mejora opcional**: Documentar en el contrato/OpenAPI que, cuando no hay fecha de aprobación, ese endpoint la fija con esa prioridad y que debe ser ≥ fecha de requerimiento.

### 4.3 Tests automatizados (prioridad alta para regresiones)

- Tests para:
  - Revisión Manual: 400 cuando `fecha_aprobacion` &lt; `fecha_requerimiento`.
  - PUT préstamo: 400 cuando `fecha_requerimiento` &gt; `fecha_aprobacion`.
  - `generar-amortizacion`: 400 si no hay `fecha_aprobacion`.
  - Creación DRAFT: no se generan cuotas; creación APROBADO con fecha: sí.

### 4.4 UX en Editar Revisión Manual

- Mostrar **min** del campo fecha de aprobación = `fecha_requerimiento` (como en los modales de asignar/aprobar), para evitar elegir una fecha anterior en el formulario.

### 4.5 Script / job para datos legacy (opcional)

- Si en el futuro aparecieran préstamos con `fecha_aprobacion` &lt; `fecha_requerimiento`, un script podría:
  - Listarlos y/o
  - Ajustar (ej. `fecha_aprobacion = fecha_requerimiento`) con confirmación o solo en entorno controlado.

### 4.6 Documentación API (OpenAPI)

- En los esquemas y descripciones de endpoints que tocan `fecha_aprobacion` / `fecha_requerimiento`, indicar explícitamente la regla “fecha_aprobacion ≥ fecha_requerimiento” y que la amortización se calcula solo con `fecha_aprobacion`.

---

## 5. Diagrama de flujo simplificado

```
[Nuevo Préstamo]
  → DRAFT (sin fecha_aprobacion) → no cuotas
  → Aprobar manual / Asignar fecha / Aplicar condiciones
       → validar fecha_aprobacion ≥ fecha_requerimiento
       → guardar fecha_aprobacion
       → generar cuotas con fecha_aprobacion

[Revisión Manual]
  → Editar préstamo (fechas, numero_cuotas, total, etc.)
       → validar fecha_aprobacion ≥ fecha_requerimiento antes de commit
       → (hoy no se regeneran cuotas al cambiar numero_cuotas/total)

[PUT /prestamos/{id}]
  → Actualizar campos (incl. fecha_requerimiento)
       → validar fecha_requerimiento ≤ fecha_aprobacion si ambas existen
       → si APROBADO y 0 cuotas y hay fecha_aprobacion → generar cuotas
```

---

## 6. Archivos clave revisados

| Ámbito | Archivo |
|--------|---------|
| Backend – préstamos | `backend/app/api/v1/endpoints/prestamos.py` |
| Backend – revisión manual | `backend/app/api/v1/endpoints/revision_manual.py` |
| Schemas | `backend/app/schemas/prestamo.py` |
| Script amortización mensual | `backend/actualizar_amortizacion_mensual.py` |
| Script cuotas sin cuotas | `backend/scripts/generar_cuotas_prestamos_sin_cuotas.py` |
| Frontend – modales | `AsignarFechaAprobacionModal.tsx`, `AprobarPrestamoManualModal.tsx` |
| Frontend – edición revisión | `frontend/src/pages/EditarRevisionManual.tsx` |
| Doc coherencia | `docs/MEJORAS_COHERENCIA_FECHAS_APROBACION.md` |

Este documento complementa `MEJORAS_COHERENCIA_FECHAS_APROBACION.md` con el análisis end-to-end y la lista de mejoras posibles.
