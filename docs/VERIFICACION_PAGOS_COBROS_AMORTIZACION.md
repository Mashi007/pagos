# Verificación: pagos por /pagos y /rapicredit-cobros → actualización de amortización

## Objetivo

Comprobar que los pagos ingresados por:
- **Entrada A:** `https://rapicredit.onrender.com/pagos/pagos`
- **Entrada B:** `https://rapicredit.onrender.com/pagos/rapicredit-cobros`

actualizan **inmediata y uniformemente** las tablas de amortización (cuotas) que se muestran en:
- **Salida 1:** `https://rapicredit.onrender.com/pagos/prestamos`
- **Salida 2:** `https://rapicredit.onrender.com/pagos/rapicredit-estadocuenta`

---

## Fuente de datos de las salidas

- **Préstamos** (`/prestamos`): lee de tablas `prestamos` y `cuotas` (backend `prestamos.py`, `get_db`).
- **Estado de cuenta** (`/rapicredit-estadocuenta`): lee de `prestamos`, `cuotas` y `clientes` (estado_cuenta_publico + servicio PDF).  
Ambas salidas usan **los mismos datos de BD**: tablas `cuotas` y `prestamos`. Si un pago actualiza `cuotas` (y `cuota_pagos`), ambas vistas reflejan el mismo estado.

---

## Flujo actual por entrada

### Entrada A: `/pagos/pagos`

- **Backend:** `POST /api/v1/pagos` (crear pago) y `POST /api/v1/pagos/batch` (crear varios).
- **Al crear un pago:**
  1. Se inserta un registro en la tabla **`pagos`**.
  2. Si el pago tiene `prestamo_id` y `monto_pagado > 0`, se llama a **`_aplicar_pago_a_cuotas_interno`** en `pagos.py`.
  3. Esa función aplica el monto a las cuotas del préstamo (FIFO), actualiza **`cuotas`** (total_pagado, estado, fecha_pago, etc.) y **`cuota_pagos`**.
- **Resultado:** Las pantallas de préstamos y estado de cuenta se actualizan de inmediato porque leen las mismas tablas.

### Entrada B: `/rapicredit-cobros`

- **Backend:** El cliente reporta el pago (formulario público) → se crea un **PagoReportado** en `pagos_reportados`. Un analista **aprueba** con `POST .../pagos-reportados/{id}/aprobar`.
- **Al aprobar (antes de la corrección):**
  1. Se actualiza `pagos_reportados.estado = 'aprobado'`.
  2. Se genera recibo PDF y se envía por correo.
  3. **No** se crea ningún registro en la tabla **`pagos`**.
  4. **No** se llama a `_aplicar_pago_a_cuotas_interno`.
- **Resultado:** Las tablas **`cuotas`** y **`cuota_pagos`** no se modifican. Las pantallas de préstamos y estado de cuenta **no** reflejan ese pago.

---

## Conclusión de la verificación

| Entrada              | ¿Crea fila en `pagos`? | ¿Aplica a cuotas (FIFO)? | ¿Prestamos y estado cuenta actualizados? |
|----------------------|------------------------|--------------------------|------------------------------------------|
| **A** (/pagos/pagos) | Sí                     | Sí                       | Sí                                       |
| **B** (cobros aprob.) | No (antes del fix)     | No                       | No                                       |

**No se cumple la actualización uniforme:** el camino de entrada por **rapicredit-cobros** (aprobación) no actualiza las tablas de amortización ni las salidas prestamos/estado cuenta.

---

## Corrección aplicada

Para que **cualquier camino de entrada** actualice las salidas por igual:

1. **Al aprobar un pago reportado** en cobros:
   - Resolver **prestamo_id** a partir de la cédula del reporte (cliente con préstamo APROBADO con cuotas pendientes; criterio: por ejemplo el más reciente).
   - Crear un registro en la tabla **`pagos`** con los mismos datos (cédula, monto, fecha, número de operación como documento, prestamo_id).
   - Llamar a la **misma lógica de aplicación a cuotas** que usa `/pagos/pagos` (`_aplicar_pago_a_cuotas_interno` o servicio compartido), para mantener FIFO y estados coherentes.

2. **Unificación:** Tanto la creación desde `/pagos/pagos` como la aprobación desde `/rapicredit-cobros` terminan:
   - Escribiendo en `pagos`,
   - Aplicando el monto a `cuotas` y `cuota_pagos` con la misma función,
   - De modo que **prestamos** y **rapicredit-estadocuenta** muestran siempre el mismo estado, con independencia del camino de entrada.

---

## Cómo validar después del fix

1. **Por cobros:** Reportar un pago desde el formulario público y aprobarlo en `/rapicredit-cobros`. Comprobar en `/prestamos` y en `/rapicredit-estadocuenta` que la cuota correspondiente aparece pagada/actualizada.
2. **Por pagos:** Crear un pago en `/pagos/pagos` para el mismo préstamo y ver que ambas salidas se actualizan igual.
3. Comparar que, para un mismo préstamo, el estado de la tabla de amortización sea idéntico tanto si el pago entró por pagos como por cobros.
