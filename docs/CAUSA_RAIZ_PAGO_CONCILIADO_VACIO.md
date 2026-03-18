# Causa raíz: "Pago conciliado" y "Recibo" en — en la Tabla de Amortización

## Síntoma

En [Préstamos → Detalles del Préstamo → Tabla de Amortización](https://rapicredit.onrender.com/pagos/prestamos) las columnas **Pago conciliado** y **Recibo** aparecen con guión (—) aunque en la base de datos existe un pago conciliado asociado al préstamo (ej. pago 56944, préstamo 4390).

## Causa raíz

El pago está registrado en la tabla **`pagos`** con `prestamo_id` y `conciliado = true`, pero **nunca se ejecutó la aplicación a cuotas**. Eso implica:

1. **No hay filas en `cuota_pagos`** que vinculen ese pago a ninguna cuota.
2. En **`cuotas`**, los campos `total_pagado`, `pago_id` y `fecha_pago` siguen vacíos o en 0.

La UI obtiene "Pago conciliado" y el monto desde:

- `cuotas.total_pagado` (y vínculos en `cuota_pagos` / `cuotas.pago_id`),

por tanto, si el pago no se aplicó a cuotas, la tabla muestra "—".

### Por qué ocurrió

- El pago se creó o se marcó conciliado por un flujo que en su momento **no** llamó a "aplicar a cuotas" (p. ej. actualización directa, conciliación por otro canal, o cuotas generadas después del pago).
- O las cuotas se generaron después del pago y en ese momento no se ejecutó la aplicación de pagos pendientes.

## Solución aplicada

En **`GET /api/v1/prestamos/{prestamo_id}/cuotas`** (endpoint que alimenta la Tabla de Amortización):

1. **Antes** de construir la respuesta, se llama a **`aplicar_pagos_pendientes_prestamo(prestamo_id, db)`**.
2. Esa función busca pagos del préstamo con `conciliado = true`, `monto_pagado > 0` y **sin** filas en `cuota_pagos`, y les aplica el monto a las cuotas (FIFO), actualizando `cuotas.total_pagado`, `cuotas.pago_id`, `cuota_pagos`, etc.
3. Si se aplicó al menos un pago, se hace **commit** y se **vuelven a cargar las cuotas** para devolver datos ya actualizados.

Efecto: al abrir o refrescar la Tabla de Amortización, cualquier pago conciliado que aún no estuviera aplicado se aplica y la tabla muestra de inmediato el "Pago conciliado" y el enlace "Ver recibo" cuando corresponda.

## Comprobación

- Para el préstamo **#4390** (Pablo Enrique Urbano Gonzalez): abrir Detalles del Préstamo → pestaña Tabla de Amortización y pulsar **Refrescar**. El pago 56944 (si existe y está conciliado) se aplicará a la primera cuota y se verá el monto y el recibo.
- A nivel BD: pagos con `prestamo_id` no nulo, conciliados y con monto > 0 deben terminar teniendo filas en `cuota_pagos` y `cuotas.total_pagado` / `pago_id` rellenados tras cargar la tabla.

## Prevención

- Todos los caminos de **creación/actualización de pagos** con `prestamo_id` y monto llaman a **aplicar a cuotas** (ver `docs/CAMINOS_CARGA_PAGOS_APLICAR_CUOTAS.md`).
- Al **generar cuotas** de un préstamo se llama a **`aplicar_pagos_pendientes_prestamo`** para ese préstamo.
- La aplicación automática al **cargar GET cuotas** corrige los casos históricos donde el pago ya existía pero no estaba aplicado.
