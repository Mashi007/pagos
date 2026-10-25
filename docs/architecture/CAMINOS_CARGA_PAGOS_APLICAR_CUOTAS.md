# Caminos de carga de pagos y aplicación automática a cuotas

En [RapiCredit - Pagos](https://rapicredit.onrender.com/pagos/pagos) los pagos se cargan por **varios caminos**. En todos ellos, cuando el pago tiene `prestamo_id` y `monto_pagado > 0`, el sistema debe **aplicar el pago a cuotas** (Cascada, tabla `cuota_pagos` y actualización de `cuotas.total_pagado` / `cuotas.pago_id`) para que la tabla de amortización y el estado de cuenta muestren el pago.

Este documento lista **todos los caminos** y confirma que la aplicación a cuotas está automatizada en cada uno.

---

## 1. Carga masiva (Excel) — `POST /api/v1/pagos/upload`

- **Origen:** Pantalla Pagos → Cargar Excel (columnas: cédula, monto, fecha, nº documento; opcional prestamo_id).
- **Proceso:** Parsea filas, crea registros en `pagos`; si la fila tiene `prestamo_id` y monto > 0, el pago se añade a `pagos_con_prestamo` y tras el `flush` se llama `_aplicar_pago_a_cuotas_interno(p, db)` para cada uno.
- **Aplicar a cuotas:** ✅ Automático (mismo commit).

---

## 2. Importar desde Cobros — `POST /api/v1/pagos/importar-desde-cobros`

- **Origen:** Importar datos desde Cobros (Excel o datos revisados).
- **Proceso:** Crea registros en `pagos` desde los datos importados; recopila los creados en `pagos_creados` y para cada uno llama `_aplicar_pago_a_cuotas_interno(p, db)`.
- **Aplicar a cuotas:** ✅ Automático (mismo commit).

---

## 3. Guardar fila editable (validar y guardar) — `POST /api/v1/pagos/guardar-fila-editable`

- **Origen:** Preview de pagos → usuario corrige y guarda una fila que cumple validadores.
- **Proceso:** Crea un solo `Pago` con `conciliado=True`; si `prestamo_id` y monto > 0, llama `_aplicar_pago_a_cuotas_interno(pago, db)` antes del commit.
- **Aplicar a cuotas:** ✅ Automático.

---

## 4. Conciliación (upload Excel) — `POST /api/v1/pagos/conciliacion/upload`

- **Origen:** Archivo Excel con nº de documento (y opcional fecha); marca como conciliados los pagos encontrados por documento.
- **Proceso:** Busca cada documento en `pagos`, asigna `conciliado=True` y si el pago tiene `prestamo_id` y monto > 0 lo añade a `pagos_para_aplicar`; luego para cada uno llama `_aplicar_pago_a_cuotas_interno(pago, db)`.
- **Aplicar a cuotas:** ✅ Automático (mismo commit).

---

## 5. Crear pago (uno) — `POST /api/v1/pagos`

- **Origen:** Formulario crear pago (crédito, cédula, monto, fecha, documento, conciliado, etc.).
- **Proceso:** Crea un `Pago`; si `row.prestamo_id` y monto > 0, llama `_aplicar_pago_a_cuotas_interno(row, db)` y marca `estado="PAGADO"` antes del commit.
- **Aplicar a cuotas:** ✅ Automático.

---

## 6. Crear pagos en lote (batch) — `POST /api/v1/pagos/batch` (o equivalente con lista)

- **Origen:** Creación de varios pagos en una sola petición.
- **Proceso:** Por cada ítem del payload crea un `Pago`; tras cada `flush`/`refresh`, si `row.prestamo_id` y monto > 0 llama `_aplicar_pago_a_cuotas_interno(row, db)`.
- **Aplicar a cuotas:** ✅ Automático (misma transacción).

---

## 7. Actualizar pago (edición) — `PUT /api/v1/pagos/{pago_id}`

- **Origen:** Edición de un pago desde la lista (cambios parciales: conciliado, prestamo_id, monto, etc.).
- **Proceso:** Aplica los campos enviados al registro existente, hace `commit` y `refresh`; después, si `row.prestamo_id` y `row.monto_pagado > 0`, llama `_aplicar_pago_a_cuotas_interno(row, db)` y hace un segundo commit.
- **Aplicar a cuotas:** ✅ Automático en cualquier canal (conciliado, prestamo_id, etc.).

---

## 8. Mover de pagos con error a pagos — `POST /api/v1/pagos-con-errores/mover-a-pagos`

- **Origen:** Revisión de pagos con error → usuario corrige y mueve a la tabla normal de pagos.
- **Proceso:** Crea un `Pago` desde el registro de `pagos_con_errores`; si `pago.prestamo_id` y monto > 0, llama `_aplicar_pago_a_cuotas_interno(pago, db)` antes de borrar el registro con error y hacer commit.
- **Aplicar a cuotas:** ✅ Automático.

---

## 9. Cobros: aprobar pago reportado — `POST /api/v1/cobros/pagos-reportados/{pago_id}/aprobar`

- **Origen:** Módulo Cobros → aprobar un pago reportado por el cliente.
- **Proceso:** `_crear_pago_desde_reportado_y_aplicar_cuotas` crea el `Pago` en la tabla `pagos` y llama `_aplicar_pago_a_cuotas_interno(row, db)` antes del commit.
- **Aplicar a cuotas:** ✅ Automático.

---

## 10. Generación de cuotas (cualquier flujo)

- **Origen:** Generar amortización, aprobar manual, PATCH préstamo que crea cuotas, crear préstamo desde Excel, etc.
- **Proceso:** Tras `_generar_cuotas_amortizacion(...)` se llama `aplicar_pagos_pendientes_prestamo(prestamo_id, db)` para aplicar a cuotas los pagos conciliados de ese préstamo que aún no tenían enlaces en `cuota_pagos` (p. ej. pagos creados antes de que existieran las cuotas).
- **Aplicar a cuotas:** ✅ Automático para pagos pendientes de aplicar.

---

## 11. Revisión manual: saldo cero — confirmar en Revisión Manual

- **Origen:** Revisión Manual → se confirma “saldo cero” (total abonos = total préstamo).
- **Proceso:** `_aplicar_saldo_cero_si_corresponde` marca todos los pagos del préstamo como `conciliado=True`; luego llama `aplicar_pagos_pendientes_prestamo(prestamo.id, db)` para aplicar cualquier pago que aún no tuviera enlaces en `cuota_pagos`, y finalmente marca todas las cuotas como PAGADO.
- **Aplicar a cuotas:** ✅ Automático (pagos pendientes de aplicar).

---

## Resumen

| # | Camino                         | Endpoint / flujo                          | Aplicar a cuotas |
|---|--------------------------------|-------------------------------------------|------------------|
| 1 | Carga masiva Excel             | `POST /pagos/upload`                      | ✅               |
| 2 | Importar desde Cobros          | `POST /pagos/importar-desde-cobros`       | ✅               |
| 3 | Guardar fila editable          | `POST /pagos/guardar-fila-editable`       | ✅               |
| 4 | Conciliación upload            | `POST /pagos/conciliacion/upload`         | ✅               |
| 5 | Crear pago (uno)               | `POST /pagos`                             | ✅               |
| 6 | Crear pagos en lote            | `POST /pagos/batch`                       | ✅               |
| 7 | Actualizar pago                | `PUT /pagos/{id}`                         | ✅               |
| 8 | Mover con error → pagos        | `POST /pagos-con-errores/mover-a-pagos`   | ✅               |
| 9 | Cobros: aprobar reportado      | `POST /cobros/pagos-reportados/{id}/aprobar` | ✅            |
|10 | Generar cuotas                 | Varios (prestamos)                        | ✅ pendientes    |
|11 | Revisión manual saldo cero    | Confirmar en Revisión Manual              | ✅ pendientes    |

**Aplicación manual adicional:** `POST /api/v1/pagos/{pago_id}/aplicar-cuotas` — para corregir o forzar la aplicación de un pago concreto (p. ej. datos ya existentes que quedaron sin enlaces).

---

## Dónde se ven las cuotas (tabla de amortización)

Las **mismas cuotas** (y el monto “Pago conciliado” por cuota) se leen de la tabla **`cuotas`** en todos estos lugares:

| Lugar | URL / ruta | Fuente de datos |
|-------|------------|------------------|
| **Estado de cuenta (público)** | [rapicredit-estadocuenta](https://rapicredit.onrender.com/pagos/rapicredit-estadocuenta) | `POST /api/v1/estado-cuenta/public/solicitar-estado-cuenta` → `_obtener_amortizacion_prestamo` (tabla `cuotas`) |
| **Informes (estado de cuenta)** | [informes](https://rapicredit.onrender.com/pagos/informes) | Mismo endpoint con `origen: "informes"`; mismo PDF con tablas de amortización |
| **Detalle del préstamo (interno)** | /prestamos → Amortización | `GET /api/v1/prestamos/{id}/cuotas` (tabla `cuotas` + `cuota_pagos`) |

Cuando un pago se **aplica a cuotas** (cualquiera de los caminos del cuadro anterior), se actualiza `cuotas.total_pagado`, `cuotas.pago_id`, `cuotas.fecha_pago` y `cuotas.estado`. La siguiente vez que se genere el PDF en **rapicredit-estadocuenta** o **informes**, las tablas de amortización mostrarán ya el “Pago conc.” y el estado correctos (y el enlace “Ver recibo” cuando la cuota esté PAGADA).

---

*Última revisión: verificación de todos los caminos de carga y procesos de aplicación a cuotas; visibilidad de cuotas en estado de cuenta e informes.*
