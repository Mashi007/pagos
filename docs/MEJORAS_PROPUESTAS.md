# Mejoras propuestas – RAPICREDIT (Pagos y Cuotas)

Basado en la auditoría del proceso de ingreso de pagos y en el uso actual del sistema.

---

## Prioridad alta

### 1. Idempotencia al aplicar pago a cuotas

**Problema:** Si por error o reintento se llama dos veces "aplicar a cuotas" sobre el mismo pago, podría duplicarse el `total_pagado` en cuotas.

**Propuesta:**
- Antes de aplicar, comprobar si el pago **ya tiene** registros en `CuotaPago` (o equivalente) que sumen su monto. Si ya está aplicado, retornar sin modificar (o retornar "ya aplicado").
- Alternativa: recalcular siempre desde la tabla de detalle (CuotaPago) en lugar de sumar sobre el estado actual de la cuota, de forma que re-ejecutar sea seguro.

**Beneficio:** Evita doble asignación en reintentos, conciliación o uso manual del endpoint.

---

### 2. Anti-duplicados en cargas masivas (Excel / batch / Cobros)

**Problema:** Mismo documento + mismo préstamo (o misma referencia) podría generar dos pagos en una misma carga o entre Cobros y Pagos.

**Propuesta:**
- En `POST /pagos/batch`: validar que no exista ya un pago con la misma clave de negocio (ej. documento cliente + id préstamo + monto + fecha, o referencia bancaria única) en un intervalo reciente.
- En `POST /pagos/importar-desde-cobros`: no importar reportados que ya generaron un pago (comprobar por id reportado o referencia).
- Opcional: constraint único en BD (ej. `(prestamo_id, referencia_externa, fecha)` o similar) para rechazar duplicados a nivel de datos.

**Beneficio:** Menos pagos duplicados y menos correcciones manuales.

---

### 3. Validación explícita en Excel (mapeo y rangos)

**Problema:** Columnas mal mapeadas o valores fuera de rango pueden crear pagos con préstamo o monto incorrecto.

**Propuesta:**
- En upload/preview: validar que documento, préstamo y monto existan y sean coherentes (préstamo del cliente, monto > 0, cuotas pendientes).
- Devolver por fila: "documento no encontrado", "préstamo no pertenece al cliente", "préstamo ya liquidado", "monto inválido".
- En backend batch: rechazar toda la carga si alguna fila falla validación (o devolver lista de errores por índice y no insertar nada), como ya se hace en parte; asegurar que las mismas reglas apliquen en guardar-fila-editable.

**Beneficio:** Menos pagos erróneos y mejor trazabilidad del origen del error.

---

## Prioridad media

### 4. Marca "ya aplicado a cuotas" en el modelo Pago

**Problema:** No hay señal explícita en el pago de que ya fue aplicado a cuotas, lo que dificulta idempotencia y auditoría.

**Propuesta:**
- Añadir campo booleano `aplicado_a_cuotas` (o `fecha_aplicacion_cuotas`) en `pagos`. Ponerlo en `True` (o guardar fecha) tras `_aplicar_pago_a_cuotas_interno`.
- En "aplicar a cuotas": si `aplicado_a_cuotas` es True, no volver a aplicar (idempotencia simple).

**Beneficio:** Idempotencia clara y consultas SQL sencillas para auditoría (pagos no aplicados).

---

### 5. Unificación de criterio Cobros ↔ Pagos

**Problema:** Riesgo de doble conteo si se usa "Importar reportados" y además se aprueba el mismo reporte desde Cobros.

**Propuesta:**
- Al importar desde Cobros, marcar los reportados importados como "ya convertidos a pago" (o estado equivalente) para que no aparezcan como aprobables de nuevo en Cobros.
- O bien: en "aprobar" en Cobros, comprobar si ese reportado ya tiene un pago asociado y no crear otro.

**Beneficio:** Un solo pago por reporte aprobado; flujo predecible.

---

### 6. Pipeline "Generar Excel desde email"

**Problema:** Si el Excel generado desde email tiene errores de mapeo o formato, esos errores llegan a "Pagos desde Excel".

**Propuesta:**
- Documentar el mapeo esperado (columnas, formatos de fecha y número).
- Si hay código/servicio que genera el Excel: validar fechas, montos y documento antes de escribir el archivo; log de filas omitidas o con warning.
- Opcional: versión de solo lectura o "vista previa" del Excel generado antes de descargar.

**Beneficio:** Menos errores en la cadena email → Excel → Pagos.

---

## Prioridad baja / operativas

### 7. Scripts SQL de verificación en cron/CI

**Problema:** Las comprobaciones (todos conciliados, todos con cuotas, etc.) se ejecutan solo bajo demanda.

**Propuesta:**
- Dejar los SQL actuales (`verificar_pagos_conciliados.sql`, `verificar_prestamos_con_cuotas.sql`) en un directorio estándar (ej. `sql/verificaciones/`) y documentarlos en el README o en `docs/`.
- Opcional: job programado (cron o tarea en Render) que ejecute estos scripts y envíe un resumen por correo o a un canal si algo falla (ej. `todos_conciliados = false` o `prestamos_sin_cuotas > 0`).

**Beneficio:** Detección temprana de inconsistencias.

---

### 8. Logging y trazabilidad

**Problema:** Ante un pago duplicado o un error de aplicación a cuotas, es difícil saber qué flujo lo creó.

**Propuesta:**
- Al crear un pago, guardar origen: `origen_creacion` (ej. "formulario", "batch_excel", "importar_cobros", "cobros_aprobar") en el modelo o en una tabla de auditoría.
- En logs (INFO): "Pago creado id=X, origen=Y, prestamo_id=Z".
- Opcional: tabla `auditoria_pagos` (pago_id, evento, usuario, timestamp, payload resumido).

**Beneficio:** Auditoría y depuración más rápidas.

---

### 9. Conciliación: no re-aplicar si ya aplicado

**Problema:** El upload de conciliación puede volver a aplicar a cuotas; si la lógica no es idempotente, hay riesgo de doble aplicación.

**Propuesta:**
- Implementar idempotencia en `_aplicar_pago_a_cuotas_interno` (ver punto 1) y/o usar la marca "aplicado a cuotas" (punto 4).
- En el flujo de conciliación: si el pago ya está aplicado a cuotas, solo actualizar `conciliado = true` y no llamar de nuevo a aplicar.

**Beneficio:** Conciliación segura aunque se suba dos veces el mismo archivo.

---

### 10. Documentación y onboarding

**Propuesta:**
- En `docs/`: un flujo resumido (diagrama o lista) de las 4 opciones de la pantalla Pagos y qué endpoint usa cada una.
- README o runbook con: "Cómo verificar que todos los pagos están conciliados" y "Cómo verificar que todos los préstamos tienen cuotas", enlazando a los SQL.
- Breve guía para soporte: "Si un cliente dice que su pago no se reflejó en cuotas", pasos a revisar (pago existe, aplicado_a_cuotas, CuotaPago, etc.).

**Beneficio:** Menor dependencia de una sola persona y respuestas más rápidas a incidencias.

---

## Resumen por prioridad

| Prioridad | Mejoras |
|-----------|---------|
| **Alta** | Idempotencia aplicar a cuotas, anti-duplicados en batch/Cobros, validación robusta Excel |
| **Media** | Flag "aplicado a cuotas" en Pago, unificación Cobros↔Pagos, revisión pipeline email→Excel |
| **Baja/Operativa** | Scripts SQL en cron/alertas, logging por origen, conciliación idempotente, documentación y runbook |

Implementar en este orden maximiza la reducción de riesgos (duplicados y doble aplicación) con el menor esfuerzo inicial.
