# Auditoría: actualización de estado de cuenta y tabla de amortización al ingresar pagos

## Objetivo

Garantizar que **cualquier** medio de ingreso de pagos actualice de forma uniforme:

- **Estado de cuenta** (público): [rapicredit-estadocuenta](https://rapicredit.onrender.com/pagos/rapicredit-estadocuenta)
- **Préstamos / tabla de amortización**: [prestamos](https://rapicredit.onrender.com/pagos/prestamos)

Ambas pantallas leen de las tablas **`cuotas`** y **`prestamos`**. Para que un pago se refleje en estado de cuenta y amortización, es necesario:

1. Insertar (o tener) un registro en **`pagos`** con `prestamo_id` y `monto_pagado > 0`.
2. Llamar a **`_aplicar_pago_a_cuotas_interno`**, que aplica el monto a las cuotas del préstamo (Cascada), actualizando `cuotas` (total_pagado, estado, fecha_pago, pago_id) y `cuota_pagos`.

---

## Fuentes de datos de las salidas

| Salida | Backend | Datos |
|--------|--------|--------|
| Préstamos | `prestamos.py` | `prestamos`, `cuotas` (conteos, saldos, mora) |
| Estado de cuenta | `estado_cuenta_publico.py` + `estado_cuenta_pdf.py` | `prestamos`, `cuotas` (amortización por préstamo), `clientes` |

Si un pago no se aplica a cuotas, las vistas **no** muestran ese pago en la tabla de amortización ni en el estado de cuenta.

---

## Puntos de entrada de pagos (auditados)

| # | Medio de ingreso | Endpoint / flujo | Crea en `pagos` | Aplica a cuotas | Estado tras auditoría |
|---|------------------|-------------------|-----------------|------------------|------------------------|
| 1 | **Pagos → Crear pago** | `POST /api/v1/pagos` (`crear_pago`) | Sí | Sí (misma transacción) | OK (corregido: un solo commit) |
| 2 | **Pagos → Guardar todos (batch)** | `POST /api/v1/pagos/batch` | Sí | Sí (misma transacción) | OK |
| 3 | **Pagos → Carga masiva (Excel)** | `POST /api/v1/pagos/upload` | Sí | Sí (tras flush, antes de commit) | OK |
| 4 | **Pagos → Importar desde Cobros** | `POST /api/v1/pagos/importar-desde-cobros` | Sí | Sí | OK |
| 5 | **Pagos → Guardar fila editable** | `POST /api/v1/pagos/guardar-fila-editable` | Sí | Sí | OK |
| 6 | **Pagos → Conciliación (upload Excel)** | `POST /api/v1/pagos/conciliacion/upload` | No (actualiza existentes) | Sí (marca conciliado + aplica) | OK |
| 7 | **Pagos → Aplicar a cuotas** | `POST /api/v1/pagos/{id}/aplicar-cuotas` | No | Sí (sobre pago existente) | OK |
| 8 | **Cobros → Aprobar pago reportado** | `POST /api/v1/cobros/pagos-reportados/{id}/aprobar` | Sí | Sí (misma transacción que aprobado) | OK (corregido previamente) |
| 9 | **Pagos con errores → Mover a pagos** | `POST /api/v1/pagos-con-errores/mover-a-pagos` | Sí | Sí | OK (corregido en esta auditoría) |

---

## Correcciones aplicadas en esta auditoría

### 1. `mover_a_pagos_normales` (pagos_con_errores)

- **Problema:** Al mover un pago de “pagos con errores” a la tabla `pagos`, no se llamaba a `_aplicar_pago_a_cuotas_interno`, por lo que las cuotas no se actualizaban y estado de cuenta / préstamos no reflejaban el pago.
- **Solución:** Tras crear el `Pago`, hacer `flush`/`refresh` y, si tiene `prestamo_id` y monto > 0, llamar a `_aplicar_pago_a_cuotas_interno` y marcar `estado = "PAGADO"` antes del `commit`. La respuesta incluye `cuotas_aplicadas`.

### 2. `crear_pago` (POST /pagos)

- **Problema:** Se hacía un primer `commit` del pago y luego, en un segundo paso, se aplicaba a cuotas con otro `commit`. Si el segundo paso fallaba, el pago quedaba guardado pero las cuotas no se actualizaban (estado de cuenta y amortización desactualizados).
- **Solución:** Una sola transacción: crear pago, `flush`/`refresh`, aplicar a cuotas si aplica, y un único `commit`. Si falla la aplicación a cuotas, se hace rollback y no se persiste el pago.

### 3. Cobros aprobar (auditoría previa)

- Aprobación y creación de pago + aplicación a cuotas en la misma transacción; errores visibles (HTTP 400) si no hay cliente o préstamo APROBADO.

---

## Cómo validar

1. **Por cada medio de ingreso:** Crear o aprobar un pago con `prestamo_id` y monto > 0.
2. **Préstamos:** En [prestamos](https://rapicredit.onrender.com/pagos/prestamos), abrir el préstamo y comprobar que la tabla de amortización muestra la cuota pagada / aplicada.
3. **Estado de cuenta:** En [rapicredit-estadocuenta](https://rapicredit.onrender.com/pagos/rapicredit-estadocuenta), consultar por cédula y verificar que el PDF/amortización refleja el mismo pago.

---

## Resumen

- Todas las entradas de pago que crean o actualizan registros en `pagos` y deben impactar amortización/estado de cuenta llaman a `_aplicar_pago_a_cuotas_interno` en la misma transacción (o en un flujo que garantice un solo commit atómico).
- Los flujos corregidos (crear pago único, mover desde pagos con errores, aprobar en Cobros) aseguran que estado de cuenta y préstamos se actualicen de forma consistente al ingresar pagos por cualquiera de los medios auditados.
