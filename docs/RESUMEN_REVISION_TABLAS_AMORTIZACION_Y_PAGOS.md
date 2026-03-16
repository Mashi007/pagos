# Resumen: revisión de tablas de amortización y pagos aplicados a cuotas

## 1. ¿Qué se revisó?

Se revisaron **ambos**:

- **Todas las tablas de amortización** (lugares donde se construye o muestra la tabla de cuotas con estado/saldo).
- **La aplicación de pagos a cuotas** (un solo flujo central que aplica el monto del pago a las cuotas).

---

## 2. Tablas de amortización – revisadas

| Ubicación | Qué hace | Revisión |
|-----------|----------|----------|
| **estado_cuenta_publico.py** – `_obtener_amortizacion_prestamo()` | Arma la tabla de amortización para el PDF de estado de cuenta (público). | ✅ Estado calculado en lectura con `estado_cuota_para_mostrar()` (PENDIENTE/VENCIDO/MORA/PAGADO según fecha de vencimiento y total pagado). |
| **estado_cuenta_publico.py** – `_obtener_datos_pdf()` y flujo **solicitar-estado-cuenta** | Lista “Cuotas pendientes” y total pendiente para el mismo PDF. | ✅ Solo cuotas con monto pendiente > 0; monto = `monto_pendiente` (monto - total_pagado); total = suma de montos pendientes; estado con `estado_cuota_para_mostrar()`. |
| **prestamos.py** – `get_cuotas_prestamo()` | Devuelve la tabla de amortización del préstamo (detalle en frontend). | ✅ Estado calculado en lectura con `estado_cuota_para_mostrar()` (líneas ~799–801, 819). |
| **prestamos.py** – `_obtener_cuotas_para_export()` | Arma cuotas para export Excel/PDF “Tabla de Amortización”. | ✅ Estado calculado con `estado_cuota_para_mostrar()` (líneas ~881–895). |

**Conclusión:** Todas las tablas de amortización que se encontraron en el backend **sí se revisaron**: usan estado calculado en tiempo de lectura y, donde aplica (estado de cuenta), monto pendiente y total pendiente correctos.

---

## 3. Pagos aplicados a cuotas – revisado

| Ubicación | Qué hace | Revisión |
|-----------|----------|----------|
| **pagos.py** – `_aplicar_pago_a_cuotas_interno()` | Aplica el monto del pago a las cuotas del préstamo (FIFO de atrás hacia delante). | ✅ Orden **DESC** por `numero_cuota` (última cuota no cubierta al 100% primero). Criterio: `fecha_pago is None` y `(total_pagado is None or total_pagado < monto)`. Actualiza `total_pagado`, `fecha_pago`, `estado`, `dias_mora` y registra en `cuota_pagos`. |

Este es el **único lugar** donde se aplican pagos a cuotas. Se llama desde:

- Crear/actualizar pago (cuando tiene `prestamo_id` y se marca conciliado o se aplica).
- Endpoint `POST /{pago_id}/aplicar-cuotas`.

**Conclusión:** Todos los pagos que se aplican a cuotas pasan por esta función; **sí se revisó** y aplica correctamente (orden de atrás hacia delante y reglas de negocio).

---

## 4. Otros puntos relacionados (no son “tabla de amortización” ni “aplicar pago”)

| Ubicación | Qué hace | ¿Revisado? | Nota |
|-----------|----------|------------|------|
| **notificacion_service.py** – `get_cuotas_pendientes_con_cliente()` | Lista cuotas con `fecha_pago is None` para notificaciones. | No | Incluye cuotas parcialmente pagadas; el “monto” mostrado es el de la cuota, no el saldo pendiente. Opcional: alinear con monto pendiente y/o estado calculado. |
| **pagos.py** – `get_stats` | Cuenta cuotas_pagadas, cuotas_pendientes, cuotas_atrasadas. | No (definición) | “Pendiente” = `fecha_pago is None` (cuenta cuotas, no suma montos). Coherente para KPIs; no es una tabla de amortización. |
| **plantilla_cobranza** | Genera HTML de cuotas desde contexto (`CUOTAS.VENCIMIENTOS` / `TOTAL_ADEUDADO`). | Depende del caller | Quien arma el contexto debe pasar monto pendiente si se quiere coherencia con estado de cuenta. |

---

## 5. Respuesta directa

- **¿Se revisaron todas las tablas de amortización?**  
  **Sí.** Las que existen en backend (estado de cuenta público, detalle de préstamo, export Excel/PDF) usan estado calculado y, en estado de cuenta, monto y total pendiente correctos.

- **¿Se revisaron todos los pagos aplicados correctamente en las cuotas?**  
  **Sí.** Hay un solo flujo que aplica pagos a cuotas (`_aplicar_pago_a_cuotas_interno`), y ese flujo fue revisado y corregido (orden de atrás hacia delante y paréntesis corregido).

Si quieres, el siguiente paso puede ser alinear notificaciones y plantilla de cobranza con monto pendiente y estado calculado.
