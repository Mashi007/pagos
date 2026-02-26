# Análisis: Reportes y uso de datos reales de BD

Este documento verifica que **todos los reportes** usan únicamente **campos reales** de las tablas de la base de datos, sin mock data ni campos inventados. Los modelos están alineados con las tablas reales (`app/models/`).

---

## Resumen por reporte

| Reporte | Archivo | Fuente de datos | Estado |
|---------|---------|-----------------|--------|
| Contable | `reportes_contable.py` | cuotas, pagos, prestamos, reporte_contable_cache | OK |
| Asesores | `reportes_asesores.py` | Cuota, Prestamo, Cliente | OK |
| Cartera | `reportes_cartera.py` | Cuota, Prestamo, Cliente | OK |
| Por cédula | `reportes_cedula.py` | Prestamo, Pago, Cuota, Cliente | OK |
| Cliente (PDF) | `reportes_cliente.py` | Cliente, Prestamo, Cuota | OK |
| Dashboard | `reportes_dashboard.py` | Cliente, Prestamo, Cuota | OK |
| Financiero | `reportes_financiero.py` | Cuota, Prestamo, Cliente | OK |
| Morosidad | `reportes_morosidad.py` | Cuota, Prestamo, Cliente | OK |
| Pagos | `reportes_pagos.py` | Cuota, Pago, Prestamo, Cliente | OK |
| Productos | `reportes_productos.py` | Prestamo, Cliente, Cuota | OK |

---

## 1. Reporte Contable (`reportes_contable.py`)

- **Tablas/Modelos:** `Cuota`, `Pago`, `Prestamo`, `ReporteContableCache` (solo cache/cedulas; exportación usa consulta viva).
- **Campos usados:**
  - **Cuota:** `id`, `prestamo_id`, `pago_id`, `numero_cuota`, `fecha_vencimiento`, `fecha_pago`, `monto` (col. `monto_cuota`), `total_pagado`.
  - **Pago:** `fecha_pago`, `monto_pagado` (alias `fecha_pago_real`, `monto_pagado_real`).
  - **Prestamo:** `cedula`, `nombres`.
- **Valores derivados (lógica de negocio, no mock):** `tipo_documento` ("Cuota N"/"Abono"/"no pago"), `moneda_documento` "USD", `moneda_local` "Bs.", `tasa` desde API/config, `importe_md`/`importe_ml` calculados.
- **Conclusión:** Sin mock; todo sale de BD y reglas de negocio.

---

## 2. Reporte Asesores (`reportes_asesores.py`)

- **Tablas/Modelos:** `Cuota`, `Prestamo`, `Cliente`.
- **Campos usados:**
  - **Prestamo:** `analista`, `id`, `cliente_id`, `estado`.
  - **Cuota:** `prestamo_id`, `monto`, `fecha_pago`, `fecha_vencimiento`.
  - **Cliente:** `estado`, `id`.
- **Filtros:** `Cliente.estado == "ACTIVO"`, `Prestamo.estado == "APROBADO"`.
- **Respuesta:** `desempeno_mensual` y `clientes_por_analista` se devuelven como listas vacías (estructura preparada para futuro uso; no son datos falsos de reporte).
- **Conclusión:** Datos 100% desde BD.

---

## 3. Reporte Cartera (`reportes_cartera.py`)

- **Tablas/Modelos:** `Cuota`, `Prestamo`, `Cliente`.
- **Campos usados:**
  - **Cuota:** `monto`, `fecha_pago`, `fecha_vencimiento`, `prestamo_id`, `id`.
  - **Prestamo:** `prestamo_id`, `cliente_id`.
  - **Cliente:** `estado`, `id`.
- **Estructuras fijas (solo etiquetas/rangos):** `distribucion_por_monto` (rangos "0 - 5.000", etc.) y `distribucion_por_mora` (rangos de días); los valores `cantidad` y `monto`/`monto_total` provienen de agregaciones sobre `Cuota`.
- **Conclusión:** Sin mock; números reales desde BD.

---

## 4. Reporte por cédula (`reportes_cedula.py`)

- **Tablas/Modelos:** `Prestamo`, `Pago`, `Cuota`, `Cliente`.
- **Campos usados:**
  - **Prestamo:** `id`, `estado`, `cedula`, `nombres`, `cliente_id`, `total_financiamiento`, `numero_cuotas`.
  - **Pago:** `prestamo_id`, `monto_pagado`.
  - **Cuota:** `prestamo_id`, `estado`, `monto`.
  - **Cliente:** `cedula`, `nombres` (fallback si Prestamo no tiene cedula/nombres).
- **Conclusión:** Todo desde BD. Cuota.estado existe en modelo (PAGADO / no PAGADO).

---

## 5. Reporte Cliente – PDF pendientes y amortización (`reportes_cliente.py`)

- **Tablas/Modelos:** `Cliente`, `Prestamo`, `Cuota`.
- **Campos usados:**
  - **Cliente:** `cedula`, `nombres`, `id`.
  - **Prestamo:** `cliente_id`, `id`.
  - **Cuota:** `prestamo_id`, `numero_cuota`, `fecha_vencimiento`, `fecha_pago`, `monto`, `estado`.
- **Conclusión:** Datos reales; sin mock.

---

## 6. Reporte Dashboard (`reportes_dashboard.py`)

- **Tablas/Modelos:** `Cliente`, `Prestamo`, `Cuota`.
- **Campos usados:**
  - **Cliente:** `estado`, `id`.
  - **Prestamo:** `cliente_id`, `estado`, `id`.
  - **Cuota:** `prestamo_id`, `monto`, `fecha_pago`, `fecha_vencimiento`.
- **KPIs:** Conteos y sumas sobre estas tablas; moroso = vencido 90+ días (regla de negocio).
- **Conclusión:** Todo desde BD.

---

## 7. Reporte Financiero (`reportes_financiero.py`)

- **Tablas/Modelos:** `Cuota`, `Prestamo`, `Cliente`.
- **Campos usados:**
  - **Cuota:** `monto`, `fecha_pago`, `fecha_vencimiento`, `prestamo_id`.
  - **Prestamo:** `prestamo_id`, `cliente_id`, `total_financiamiento`.
  - **Cliente:** `estado`, `id`.
- **Agregaciones:** `func.date_trunc("month", Cuota.fecha_pago)` y por `fecha_vencimiento`; `to_char` para etiqueta de mes. Flujo de caja = ingresos menos egresos programados (calculado).
- **Conclusión:** Datos reales; solo cálculos de negocio.

---

## 8. Reporte Morosidad (`reportes_morosidad.py`)

- **Tablas/Modelos:** `Cuota`, `Prestamo`, `Cliente`.
- **Campos usados:**
  - **Cliente:** `id`, `nombres`, `cedula`, `estado`.
  - **Prestamo:** `id`, `cliente_id`, `analista`, `cedula`, `nombres`, `total_financiamiento`, `concesionario`, `estado`.
  - **Cuota:** `prestamo_id`, `fecha_vencimiento`, `fecha_pago`, `monto`, `total_pagado`.
- **RANGOS_ATRASO:** Definición de rangos de días (1–14, 15–29, etc.); los ítems por rango se rellenan con datos de BD (prestamos, cuotas, montos).
- **Conclusión:** Sin mock; solo reglas de rangos y datos reales.

---

## 9. Reporte Pagos (`reportes_pagos.py`)

- **Tablas/Modelos:** `Cuota`, `Pago`, `Prestamo`, `Cliente`.
- **Campos usados:**
  - **Cuota:** `monto`, `fecha_pago`, `prestamo_id` (reporte por rango de fechas).
  - **Pago:** `id`, `fecha_pago`, `prestamo_id`, `cedula_cliente` (col. `cedula`), `monto_pagado`, `numero_documento` (por-mes y por-día).
  - **Prestamo:** `nombres` (outer join).
  - **Cliente:** `cedula`, `nombres` (outer join por `Pago.cedula_cliente == Cliente.cedula`).
- **Conclusión:** Todo desde BD. `pagos_por_metodo` se devuelve vacío (estructura; no datos falsos).

---

## 10. Reporte Productos (`reportes_productos.py`)

- **Tablas/Modelos:** `Prestamo`, `Cliente`, `Cuota`.
- **Campos usados:**
  - **Prestamo:** `modelo_vehiculo`, `total_financiamiento`, `fecha_aprobacion`, `fecha_registro`, `producto`, `concesionario`, `cliente_id`, `estado`.
  - **Cliente:** `estado`, `id`.
  - **Cuota:** `monto`, `fecha_pago`, `fecha_vencimiento`, `prestamo_id`.
- **Valor activo:** `valor_activo = total_financiamiento * 0.70` (regla de negocio, no mock).
- **Conclusión:** Datos reales; solo fórmulas de negocio.

---

## Modelos verificados (columnas usadas)

- **Cliente:** `id`, `cedula`, `nombres`, `estado`.
- **Prestamo:** `id`, `cliente_id`, `cedula`, `nombres`, `estado`, `analista`, `total_financiamiento`, `numero_cuotas`, `producto`, `concesionario`, `modelo_vehiculo`, `fecha_aprobacion`, `fecha_registro`.
- **Cuota:** `id`, `prestamo_id`, `pago_id`, `numero_cuota`, `fecha_vencimiento`, `fecha_pago`, `monto` (monto_cuota), `total_pagado`, `estado`.
- **Pago:** `id`, `prestamo_id`, `cedula_cliente` (col. cedula), `fecha_pago`, `monto_pagado`, `numero_documento`.
- **ReporteContableCache:** usado solo para cache y búsqueda de cédulas; la exportación contable usa consulta viva a cuotas/pagos/prestamos.

---

## Conclusión general

- **No hay mock data** en los reportes: todas las cifras y listados provienen de consultas a la BD usando los modelos anteriores.
- **No hay campos inventados:** los nombres usados en código coinciden con los modelos y, según documentación de estos, con las tablas reales.
- **Valores “fijos” aceptables:** etiquetas (USD, Bs., rangos de días, rangos de monto), reglas (70% valor activo, 90 días moroso, tasa USD/BS) y estructuras vacías (`desempeno_mensual`, `clientes_por_analista`, `pagos_por_metodo`, `tendencia_mensual`) son diseño/negocio, no datos falsos.

Si se añaden nuevos reportes o columnas, conviene mantener esta convención: solo modelos y columnas existentes en BD y cálculos/reglas explícitos de negocio.
