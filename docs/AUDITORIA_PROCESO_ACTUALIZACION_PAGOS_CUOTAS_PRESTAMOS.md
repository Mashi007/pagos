# Auditoría: proceso de actualización pagos → cuotas → préstamos

## 1. Alcance

Proceso que actualiza el estado de amortización cuando se registra un pago:
- **Tablas:** `pagos`, `cuotas`, `cuota_pagos`. La vista de **préstamos** y **estado de cuenta** leen de `prestamos` + `cuotas` (no se escribe en `prestamos` al aplicar pagos).

## 2. Tablas involucradas

| Tabla          | Rol en el proceso |
|----------------|-------------------|
| **pagos**      | Origen: cada pago tiene `prestamo_id`, `monto_pagado`, `fecha_pago`, `estado`. Tras aplicar a cuotas, `estado` pasa a `PAGADO`. |
| **cuotas**     | Destino: se actualizan `total_pagado`, `fecha_pago`, `estado`, `dias_mora`, `pago_id` (último pago que tocó la cuota). |
| **cuota_pagos**| Historial: cada aplicación pago→cuota genera una fila (cuota_id, pago_id, monto_aplicado, orden_aplicacion, es_pago_completo). |
| **prestamos**  | Solo lectura en este flujo: no se actualiza al aplicar pagos (no existe campo “saldo” ni estado LIQUIDADO en el modelo actual). |

## 3. Flujos de entrada

### 3.1 Entrada desde /pagos/pagos

- **Crear un pago (POST):**
  1. Validar documento (no duplicado), préstamo y cliente.
  2. `db.add(Pago)`, `db.commit()`, `db.refresh(row)`.
  3. Si `prestamo_id` y monto > 0: `_aplicar_pago_a_cuotas_interno(row, db)`.
  4. Si aplica bien: `row.estado = "PAGADO"`, `db.commit()`.
  5. Si aplica mal: `db.rollback()` (solo el segundo commit); el pago queda en BD con estado PENDIENTE (aplicación manual luego).

- **Crear lote (POST /batch):** Misma idea por cada pago: commit del pago y luego aplicar; si falla la aplicación se hace rollback de esa parte.

- **Aplicar cuotas (POST /{pago_id}/aplicar-cuotas):** Lee el pago, llama `_aplicar_pago_a_cuotas_interno`, marca PAGADO y hace un solo `commit`.

### 3.2 Entrada desde /rapicredit-cobros (aprobación)

- Al aprobar un pago reportado:
  1. Se actualiza `pagos_reportados` (estado, PDF, correo, historial) y se hace `db.commit()`.
  2. Se llama `_crear_pago_desde_reportado_y_aplicar_cuotas(db, pr, usuario_email)`:
     - Resuelve cliente por cédula y préstamo APROBADO (el de id más reciente).
     - Crea un `Pago` en tabla `pagos`.
     - **Optimización:** una sola transacción: `flush` para obtener `pago.id`, aplicar a cuotas, marcar PAGADO y un solo `commit`. Si algo falla, `rollback` y no se crea el pago.

## 4. Lógica de aplicación a cuotas (`_aplicar_pago_a_cuotas_interno`)

- **Ubicación:** `backend/app/api/v1/endpoints/pagos.py`. No hace `commit`; la hace el llamador.
- **Orden:** Cascada por `numero_cuota` (cuotas con menor número primero).
- **Criterio de cuotas:** `prestamo_id` del pago, `fecha_pago IS NULL`, y `total_pagado IS NULL` o `total_pagado < monto`.
- **Por cada cuota:** reparte el monto restante; actualiza `total_pagado`, `pago_id`, `fecha_pago` (si se completa), `estado` (PAGADO / PAGO_ADELANTADO / VENCIDO / MORA / PENDIENTE), `dias_mora`; inserta fila en `cuota_pagos`.
- **Estados de cuota:** PAGADO (100 %), PAGO_ADELANTADO (parcial futuro), VENCIDO/MORA/PENDIENTE según días de mora.

## 5. Hallazgos y mejoras aplicadas

### 5.1 Consistencia

- **Pagos desde /pagos:** Se persiste primero el pago y luego se intenta aplicar. Si la aplicación falla, el pago queda PENDIENTE; es un diseño aceptado (aplicación manual posterior).
- **Cobros:** Antes se hacía un `commit` del pago y luego aplicar; si la aplicación fallaba podía quedar un pago en BD sin cuotas actualizadas. **Mejora:** una sola transacción (flush + aplicar + commit); si falla, rollback y no se crea el pago.

### 5.2 Transacciones

- **Cobros:** Un único `commit` al final del flujo “crear pago + aplicar cuotas”, usando `flush()` para obtener `pago.id` antes de aplicar.
- **Pagos (crear/batch):** Se mantiene el comportamiento actual (commit del pago y luego aplicar) para no cambiar el criterio de “siempre guardar el pago y permitir aplicar después”.

### 5.3 Rendimiento

- Una sola consulta para cargar cuotas pendientes del préstamo (ordenadas por `numero_cuota`).
- Actualizaciones por cuota en el mismo request; no hay N+1 de lecturas.
- En cobros se evitan dos commits por aprobación (antes: commit pago + commit aplicación).

### 5.4 Código único para aplicar

- La aplicación a cuotas está centralizada en `_aplicar_pago_a_cuotas_interno` (pagos.py). Cobros la reutiliza vía import. Misma regla Cascada y mismos estados en ambos flujos.

### 5.5 Préstamos

- La tabla `prestamos` no se modifica al aplicar pagos (no hay campo de saldo ni estado LIQUIDADO en el modelo). Las pantallas de préstamos y estado de cuenta se basan en `cuotas` y `prestamos` en solo lectura.

## 6. Resumen

- **Tablas tocadas al actualizar por un pago:** `pagos` (estado), `cuotas` (total_pagado, fecha_pago, estado, dias_mora, pago_id), `cuota_pagos` (inserciones).
- **Flujos unificados:** /pagos/pagos y /rapicredit-cobros usan la misma lógica de aplicación; las salidas (prestamos, estado de cuenta) se actualizan de forma uniforme.
- **Optimización aplicada:** En cobros, creación de pago + aplicación a cuotas en una sola transacción (flush + apply + commit; rollback en error).

## 7. Recomendaciones futuras

- **Estado LIQUIDADO en prestamos:** Si se agrega un estado \LIQUIDADO\ al modelo de pr�stamo, considerar actualizar \prestamos.estado\ cuando todas las cuotas del pr�stamo est�n PAGADAS (por ejemplo al final de \_aplicar_pago_a_cuotas_interno\ o en un job).
- **Servicio compartido:** Extraer \_aplicar_pago_a_cuotas_interno\ y helpers de mora a un m�dulo \pp.services.articulacion_pago\ para que pagos y cobros importen desde un �nico lugar y facilitar pruebas unitarias.
- **Batch en /pagos:** Valorar procesar el lote en una sola transacci�n (flush por pago, aplicar todos, commit al final) para reducir commits; hoy se prioriza que cada pago quede guardado aunque falle la aplicaci�n del siguiente.
