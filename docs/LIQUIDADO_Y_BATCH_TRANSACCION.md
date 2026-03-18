# Estado LIQUIDADO y transacción única en batch de pagos

## 1. Estado LIQUIDADO en préstamos

Cuando todas las cuotas de un préstamo quedan pagadas (tras aplicar un pago a cuotas), el préstamo se marca automáticamente como **LIQUIDADO**.

- **Dónde:** Al final de `_aplicar_pago_a_cuotas_interno` (pagos.py) se llama a `_marcar_prestamo_liquidado_si_corresponde(prestamo_id, db)`.
- **Condición:** Solo se actualiza si el préstamo está en estado **APROBADO** y todas sus cuotas tienen `total_pagado >= monto` (con tolerancia 0.01).
- **Schemas:** Se añadió `LIQUIDADO` a `PRESTAMO_ESTADOS_VALIDOS` en `app/schemas/prestamo.py` y en `prestamo_estado_validator.py`.
- **Commit:** No hace commit; lo hace el flujo que llamó a `_aplicar_pago_a_cuotas_interno` (crear pago, aplicar-cuotas, batch, cobros).

## 2. Batch de pagos: transacción única por lote

El endpoint **POST /api/v1/pagos/batch** usa una sola transacción por lote:

- **Fase 1 – Validación:** Se validan todos los ítems (documento no duplicado en payload, crédito existe, cliente existe). Si hay algún error, se devuelve la lista de errores por índice y **no se inserta ningún pago** (`ok_count: 0`, `fail_count: N`).
- **Fase 2 – Transacción única:** Si toda la validación pasa, se crean todos los pagos con `db.add` + `db.flush` + `db.refresh`, se aplica a cuotas cada uno con `_aplicar_pago_a_cuotas_interno`, y al final se hace **un solo** `db.commit()`. Si en cualquier paso ocurre una excepción, se hace `db.rollback()` y se responde 500 indicando que ningún pago fue creado.

Ventajas: menos commits por lote y comportamiento “todo o nada” (o se guardan todos los pagos del lote o ninguno).
