# Reglas de negocio: aplicación de pagos a cuotas

## Flujo de aplicación

1. **Se recibe un pago** → se aplica a la **última cuota anterior** (por orden de `numero_cuota`) que **no está cubierta al 100%**.

2. **Solo cuando una cuota se cubre al 100%** → se pasa a cargar el resto del pago a la siguiente cuota.

3. **Orden de aplicación**: siempre por `numero_cuota` ascendente (cuota 1, 2, 3...).

---

## Estados de la cuota

| Estado | Condición |
|--------|-----------|
| **PAGADO** | La cuota está cubierta al 100% (`total_pagado >= monto_cuota`). Tiene `fecha_pago` y `pago_id` del último pago que la completó. |
| **PAGO_ADELANTADO** | La cuota tiene cobertura parcial (`0 < total_pagado < monto_cuota`) **y** `fecha_vencimiento` está en el futuro (fecha_vencimiento > hoy). |
| **PENDIENTE** | La cuota no está pagada o tiene pago parcial **y** `fecha_vencimiento` ya venció (fecha_vencimiento <= hoy). |
| **MORA** | *(Completar según tu criterio: p.ej. pago parcial + vencida + X días de atraso)* |

---

## Resumen

- **100% cubierta** → `estado = PAGADO`, `fecha_pago` asignada.
- **Parcial + vencimiento futuro** → `estado = PAGO_ADELANTADO`.
- **Parcial + vencimiento pasado** → `estado = PENDIENTE` (o MORA según regla de días).

---

## Campo `total_pagado`

La cuota tiene `total_pagado` (acumulado de lo que se ha pagado). Cuando `total_pagado >= monto_cuota`, la cuota pasa a PAGADO.

---

---

## Implementación actual

- **Backend**: `POST /api/v1/pagos/{pago_id}/aplicar-cuotas` aplica pagos (totales y parciales) siguiendo estas reglas.
- **Respuesta**: `cuotas_completadas` (100% cubiertas) y `cuotas_parciales` (PAGO_ADELANTADO o PENDIENTE).
