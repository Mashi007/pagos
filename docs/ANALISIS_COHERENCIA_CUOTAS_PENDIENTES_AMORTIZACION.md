# Análisis integral: coherencia entre Cuotas pendientes y Tabla de amortización

## 1. Análisis de tablas y reglas de negocio

### 1.1 Modelo de datos (BD)

| Tabla | Columnas relevantes para cuotas/pagos |
|-------|--------------------------------------|
| **cuotas** | `id`, `prestamo_id`, `pago_id`, `numero_cuota`, `fecha_vencimiento`, `fecha_pago`, `monto` (monto_cuota), `saldo_capital_inicial`, `saldo_capital_final`, `total_pagado`, `dias_mora`, `estado` |
| **pagos** | `id`, `prestamo_id`, `fecha_pago`, `monto_pagado`, `estado`, ... |
| **cuota_pagos** | `cuota_id`, `pago_id`, `monto_aplicado`, `orden_aplicacion`, `es_pago_completo` |

- **Saldo por cuota**: no hay columna “saldo pendiente”; se deriva de `monto - total_pagado` cuando `fecha_pago` es NULL (cuota no cerrada).
- **Estado de cuota**: PENDIENTE | VENCIDO | MORA | PAGADO | PAGO_ADELANTADO. Se actualiza en BD solo cuando se **aplica un pago** en `_aplicar_pago_a_cuotas_interno` (pagos.py).
- **fecha_pago** en cuota: se setea solo cuando la cuota queda **totalmente pagada** (`nuevo_total >= monto_cuota - 0.01`). Con pago parcial, `fecha_pago` sigue NULL.

### 1.2 Dónde se construyen “Cuotas pendientes” y “Tabla de amortización”

| Fuente | Cuotas pendientes | Tabla de amortización |
|--------|-------------------|------------------------|
| **estado_cuenta_publico.py** | `_obtener_datos_pdf()` y flujo solicitar/verificar: `Cuota.fecha_pago.is_(None)`; suma `total_pendiente += monto` (monto completo); estado = `getattr(c, "estado", None) or "PENDIENTE"` | `_obtener_amortizacion_prestamo()`: todas las cuotas del préstamo; saldo = `saldo_capital_final` (cronograma); pago conc. = `total_pagado`; estado = de BD |
| **prestamos.py** | — | `get_cuotas_prestamo()`: lista cuotas con `saldo_capital_*`, `total_pagado`, `estado` de BD |
| **pagos.py** (aplicar pago) | “Cuotas pendientes” para Cascada: `fecha_pago.is_(None)` **y** `(total_pagado.is_(None) or total_pagado < monto)` | — |

### 1.3 Reglas de negocio ya implementadas (pagos.py)

- **Orden de aplicación de pagos (regla prioritaria)**: Al realizar un pago, **independientemente de la fecha del pago**, el monto se carga **de atrás hacia delante**: se cubre al 100% la **última** cuota que aún no está cubierta al 100%, luego la anterior, y así sucesivamente. Orden: `numero_cuota` **DESC** (ej. cuota 12, 11, 10, …). Lógica: **monto inicial (del pago) menos lo aplicado a cada cuota = saldo a la fecha**; las cuotas se cubren **en orden** (última primero), sin saltar al azar. *(Actualmente el código usa `order_by(Cuota.numero_cuota)` = ascendente = 1, 2, 3…; debe corregirse a DESC.)*
- **Criterio de cuotas a aplicar**: `fecha_pago is None` y `(total_pagado is None or total_pagado < monto)`.
- **Estado al aplicar**: si cuota queda cubierta → PAGADO y `fecha_pago`; si no → `_estado_cuota_por_cobertura(...)` → VENCIDO/MORA/PENDIENTE.
- **Mora**: `_calcular_dias_mora(fecha_vencimiento)`; VENCIDO (1–90 días), MORA (>90).

---

## 2. Diagnóstico: qué falla y por qué no hay coherencia

### 2.1 Cuotas pendientes: monto y total pendiente incorrectos con pagos parciales

- **Criterio de inclusión**: se usan cuotas con `fecha_pago.is_(None)`. Eso incluye bien cuotas sin pago y con **pago parcial** (porque el parcial no setea `fecha_pago`).
- **Problema**: para cada fila se usa **monto** (monto de la cuota) y `total_pendiente` es la suma de esos montos. No se usa **saldo pendiente** = `monto - total_pagado`.
- **Efecto**: si la cuota 5 tiene 88 pagado de 96, en “Cuotas pendientes” debería aparecer con monto **8** y el total pendiente debería restar 88; en cambio se muestra 96 y se suma 96. El total pendiente queda **sobrestimado** y no coincide con lo que realmente falta por pagar. Además, si en otro flujo se excluyeran cuotas con `total_pagado > 0`, la cuota 5 podría no aparecer y se **subestimaría** lo pendiente.

**Conclusión**: La lista debe mostrar **monto pendiente** por cuota (`monto - total_pagado`) y **Total pendiente** = suma de esos montos pendientes.

### 2.2 Estado de cuota: no se actualiza con el tiempo (solo al aplicar pago)

- El **estado** se escribe en BD solo dentro de `_aplicar_pago_a_cuotas_interno`. Las cuotas que nunca han recibido un pago (ej. 8, 9, 10, 11, 12) quedan con estado inicial **PENDIENTE**.
- No hay ningún proceso (job ni cálculo al leer) que pase a **VENCIDO** cuando `fecha_vencimiento < hoy` y la cuota sigue sin pagar.
- **Efecto**: En “Cuotas pendientes” y en “Tabla de amortización” la cuota 8 (vencida 28/02) aparece como PENDIENTE cuando ya debería ser VENCIDO. Incoherencia entre “qué se debe” y “estado mostrado”.

**Conclusión**: El estado mostrado en reportes (cuotas pendientes y tabla de amortización) debe **recalcularse al momento de la consulta** cuando la cuota no está pagada: si `fecha_vencimiento < hoy` y `total_pagado < monto` → VENCIDO o MORA según días, aunque en BD siga PENDIENTE.

### 2.3 Tabla de amortización: saldo teórico vs realidad con pagos parciales

- La tabla usa **saldo_capital_final** del cronograma (teórico). No se ajusta por pagos parciales.
- **Efecto**: En una cuota con “Pago conc. 88” y Total 96, el “Saldo” sigue siendo el del cronograma (ej. 672), como si se hubieran pagado 96. Da la impresión de que el saldo ya contempla el pago completo.
- **Decisión de diseño**: El “Saldo” en la tabla de amortización puede mantenerse como **saldo teórico del cronograma** (documentación del plan de pagos). La coherencia con “cuotas pendientes” se logra en el otro bloque: que “Cuotas pendientes” y “Total pendiente” usen **saldo vivo** (monto pendiente por cuota y suma de esos montos). Opcionalmente se puede añadir en la tabla una columna “Pendiente” = `monto - total_pagado` cuando `total_pagado < monto` para que cuadre con la sección de cuotas pendientes.

### 2.4 Resumen de incoherencias

| Problema | Dónde se ve | Causa |
|----------|-------------|--------|
| Total pendiente mayor al real; monto por cuota pendiente incorrecto cuando hay parciales | Cuotas pendientes (PDF estado de cuenta) | Se usa `monto` en vez de `monto - total_pagado` y se suma el monto completo |
| Cuotas vencidas mostradas como PENDIENTE | Cuotas pendientes y Tabla de amortización | Estado solo se actualiza al aplicar pago; no se recalcula por fecha_vencimiento vs hoy |
| Saldo en tabla no refleja pagos parciales | Tabla de amortización | Saldo = saldo_capital_final (cronograma); no se ajusta por total_pagado |

---

## 3. Plan de acción (a implementar tras tu OK)

### 3.1 Regla única de “cuota pendiente” y monto pendiente

- **Definición**: Cuota pendiente = `fecha_pago is None` **o** `total_pagado is None` **o** `total_pagado < monto`.
- **Monto pendiente por cuota**: `max(0, monto - (total_pagado or 0))`.
- **Total pendiente**: suma de “monto pendiente” de todas las cuotas que cumplan la definición (por el/los préstamos del contexto: cliente, estado de cuenta, etc.).


### 3.0 Orden de aplicación de pagos (prioridad)

- **Regla**: Al realizar un pago, **independientemente de la fecha**, el monto se aplica **de atrás hacia delante**: primero se cubre al 100% la **última** cuota que no esté cubierta al 100%, luego la anterior, etc. **Lógica**: monto inicial (del pago) menos lo aplicado a cada cuota = saldo a la fecha; las cuotas se cubren **en orden** (última primero), sin saltar al azar.
- **Implementación**: En `_aplicar_pago_a_cuotas_interno` (pagos.py) usar **orden DESC** por `numero_cuota`: `.order_by(Cuota.numero_cuota.desc())`. Así la primera cuota procesada es la de mayor número (ej. 12), luego 11, 10, …
- **Verificación**: Confirmar que el bucle aplica `a_aplicar = min(monto_restante, monto_necesario)` y reduce `monto_restante`; que no se filtra ni salta ninguna cuota con saldo pendiente; y que el orden de la consulta (DESC) es el que determina la secuencia.

### 3.2 Cambios en backend

0. **pagos.py - _aplicar_pago_a_cuotas_interno**
   - Cambiar orden de cuotas pendientes a **descendente**: `.order_by(Cuota.numero_cuota.desc())` (de atrás hacia delante).
   - Actualizar docstring/comentarios: aplicación "de atrás hacia delante"; `monto_restante` = saldo a la fecha.
   - (Opcional) Test que verifique que las cuotas se cubren en orden DESC.

1. **estado_cuenta_publico.py**  
   - En `_obtener_datos_pdf()` y en el flujo de **solicitar-estado-cuenta** (donde se arma `cuotas_pendientes`):
     - Incluir en la lista solo cuotas con **monto pendiente > 0**: `(monto or 0) - (total_pagado or 0) > 0` (o equivalente con `fecha_pago is None` y luego filtrar por monto pendiente).
     - Por cada cuota: guardar **monto_pendiente** = `max(0, monto - (total_pagado or 0))` y usarlo como “monto” en la tabla de “Cuotas pendientes” y en la suma.
     - **Total pendiente**: sumar `monto_pendiente` de esas cuotas, no el monto completo.
     - **Estado mostrado**: no usar solo el de BD; para cuotas no pagadas (monto_pendiente > 0) calcular estado en tiempo de consulta: misma lógica que `_estado_cuota_por_cobertura(total_pagado, monto_cuota, fecha_vencimiento)` (reutilizando o importando desde pagos.py, o duplicando la lógica mínima: días mora y clasificación PENDIENTE/VENCIDO/MORA). Así las cuotas vencidas se muestran como VENCIDO/MORA aunque en BD sigan PENDIENTE.

2. **estado_cuenta_publico.py – _obtener_amortizacion_prestamo()**  
   - Para cada cuota, al armar el dict que se envía al PDF: si la cuota no está pagada (`total_pagado < monto`), calcular **estado** en tiempo de consulta (misma regla que arriba) en lugar de usar solo `getattr(cu, "estado", None)`. Así la tabla de amortización y la lista de cuotas pendientes comparten la misma regla de estado.

3. **prestamos.py – get_cuotas_prestamo()**  
   - Para cada cuota devuelta (tabla de amortización en detalle de préstamo): si `fecha_pago is None` y `(total_pagado or 0) < monto`, calcular **estado** en tiempo de consulta (misma función o misma lógica que en pagos/estado_cuenta) y devolver ese estado en la respuesta, para que el frontend muestre VENCIDO/MORA cuando corresponda.

4. **Centralizar cálculo de “estado a mostrar”**  
   - Opción A: en `pagos.py` exponer una función helper, p. ej. `estado_cuota_para_mostrar(cuota)` o `estado_cuota_por_cobertura(total_pagado, monto_cuota, fecha_vencimiento)` (ya existe; solo hay que usarla desde estado_cuenta y prestamos con los mismos parámetros).  
   - Opción B: en un módulo compartido (ej. `app.core.conceptos` o `app.services.cuota_estado`) una función que, dado total_pagado, monto_cuota, fecha_vencimiento (y opcionalmente fecha de referencia = hoy), devuelva PENDIENTE | VENCIDO | MORA | PAGADO.  
   - Que **estado_cuenta_publico** y **prestamos** usen esa misma función al construir listas y tablas, para que “Cuotas pendientes” y “Tabla de amortización” siempre muestren el mismo criterio de estado.

### 3.3 Cambios en frontend (si aplica)

- Si el estado de cuenta público se genera solo en backend (PDF), no hace falta cambio en frontend para ese flujo.
- Si hay una pantalla de “cuotas pendientes” o “tabla de amortización” que consuma `get_cuotas_prestamo` o un endpoint que devuelva cuotas pendientes: asegurarse de usar el **estado** y, si se muestra, el **monto pendiente** que ya vendrán correctos desde el backend tras los cambios anteriores.

### 3.4 Tabla de amortización: saldo teórico vs pendiente (opcional)

- Mantener la columna “Saldo” como saldo teórico del cronograma (`saldo_capital_final`).
- Opcional: añadir columna “Pendiente” (o “Por pagar”) = `max(0, monto_cuota - total_pagado)` cuando la cuota no esté pagada, para que el usuario vea explícitamente lo que falta y coincida con la sección “Cuotas pendientes”. Esto puede ser una segunda fase si se desea.

### 3.5 Otros puntos a revisar (sin cambiar lógica de negocio)

- **notificacion_service.get_cuotas_pendientes_con_cliente**: usa `Cuota.fecha_pago.is_(None)`. Si se desea que las notificaciones consideren “pendiente” solo cuando hay saldo por pagar, filtrar también por `total_pagado < monto` y usar monto pendiente en el mensaje. Si se prefiere notificar “tiene cuotas no cerradas” (incluyendo parciales), se puede dejar el criterio y solo ajustar textos/montos a “monto pendiente” donde se muestre.
- **pagos.py – get_stats / cuotas_pendientes / cuotas_atrasadas**: las definiciones actuales (fecha_pago is None, fecha_vencimiento < hoy) son coherentes; solo asegurarse de que cualquier listado que muestre “monto” use monto pendiente cuando haya parciales.

---

## 4. Resumen ejecutivo

- **Orden de aplicación**: El pago se debe aplicar **de atrás hacia delante** (última cuota no cubierta al 100% primero; `numero_cuota DESC`). Monto inicial menos lo aplicado = saldo a la fecha; cubrir cuotas en orden, sin saltos. Hoy el código usa orden ascendente; corregir a DESC.
- **Cuotas pendientes**: hoy se usa monto completo y no saldo pendiente → total pendiente incorrecto con pagos parciales. **Solución**: monto pendiente = `monto - total_pagado`, total = suma de esos.
- **Estado**: se actualiza solo al aplicar pago → cuotas vencidas siguen como PENDIENTE. **Solución**: recalcular estado al leer (fecha_vencimiento vs hoy y total_pagado vs monto) en estado_cuenta y en get_cuotas_prestamo, reutilizando la misma regla (p. ej. `_estado_cuota_por_cobertura`).
- **Tabla de amortización**: saldo teórico es correcto como diseño; la coherencia con “cuotas pendientes” se logra corrigiendo monto/total y estado en el bloque “Cuotas pendientes” y, opcionalmente, añadiendo “Pendiente” por cuota en la tabla.

Tras tu OK se implementan los puntos 3.1, 3.2 (1–4) y, si lo apruebas, 3.4 (columna Pendiente). Opcionalmente 3.3 y 3.5 según dónde se muestren cuotas pendientes y notificaciones.

