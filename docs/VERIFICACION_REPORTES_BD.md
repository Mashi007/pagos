# Verificación: Reportes conectados a BD (tablas y campos)

**URL:** https://rapicredit.onrender.com/pagos/reportes  
**Fecha:** 2026-02-25  
**Objetivo:** Confirmar que todos los reportes del Centro de Reportes usan datos reales desde la base de datos (tablas y campos identificados).

---

## Resumen

| Reporte (UI) | Endpoint(s) backend | Tablas BD | Conectado a BD |
|--------------|---------------------|-----------|----------------|
| Resumen KPIs | `GET /reportes/dashboard/resumen` | clientes, prestamos, cuotas | Sí |
| Cuentas por cobrar (Cartera) | `GET /reportes/cartera`, `/reportes/exportar/cartera` | clientes, prestamos, cuotas | Sí |
| Morosidad | `GET /reportes/morosidad/clientes`, `/reportes/exportar/morosidad-clientes` | clientes, prestamos, cuotas | Sí |
| Vencimiento / Pago vencido | `GET /reportes/morosidad`, `/reportes/morosidad/por-mes`, `/reportes/exportar/morosidad` | clientes, prestamos, cuotas | Sí |
| Pagos | `GET /reportes/pagos`, `/reportes/pagos/por-mes`, `/reportes/exportar/pagos` | clientes, prestamos, cuotas; **pagos** | Sí* |
| Contable | `GET /reportes/contable/cedulas`, `/reportes/exportar/contable` | clientes, prestamos, cuotas, pagos; **reporte_contable_cache** | Sí |
| Por cédula | `GET /reportes/por-cedula`, `/reportes/exportar/cedula` | prestamos, pagos, cuotas, clientes | Sí |
| Asesores (Pago vencido) | `GET /reportes/asesores`, `/reportes/asesores/por-mes` | clientes, prestamos, cuotas | Sí |

\* Ver nota en sección Pagos: filtro por cliente activo en JSON; Excel por mes usa solo tabla `pagos`.

---

## Tablas y modelos utilizados

| Tabla (BD) | Modelo | Uso en reportes |
|------------|--------|------------------|
| **clientes** | `Cliente` | Filtro estado ACTIVO; cedula, nombres en varios reportes |
| **prestamos** | `Prestamo` | Filtro estado APROBADO; cedula, nombres, total_financiamiento, numero_cuotas, analista, concesionario |
| **cuotas** | `Cuota` | monto, fecha_vencimiento, fecha_pago, estado, total_pagado, prestamo_id, numero_cuota, pago_id |
| **pagos** | `Pago` | Reporte Pagos (por mes/día); Reporte Contable (fecha_pago real); Por cédula (total abono) |
| **reporte_contable_cache** | `ReporteContableCache` | Reporte Contable (exportación desde cache; cache alimentado desde Cuota+Prestamo+Pago) |

---

## 1. Resumen dashboard (KPIs)

- **Archivo:** `reportes_dashboard.py`
- **Endpoint:** `GET /reportes/dashboard/resumen`
- **Dependencia:** `Depends(get_db)`, `get_current_user`

**Tablas y campos:**

| Tabla | Campos usados |
|-------|----------------|
| **clientes** | id, estado |
| **prestamos** | id, cliente_id, estado |
| **cuotas** | id, prestamo_id, monto, fecha_pago, fecha_vencimiento |

**Lógica:** Cuenta clientes ACTIVOS; préstamos APROBADOS con cliente ACTIVO; cuotas con/sin fecha_pago; cartera = suma de cuotas pendientes; mora = préstamos con cuotas vencidas 90+ días; pagos_mes = suma de cuotas con fecha_pago en el mes actual.

---

## 2. Cuentas por cobrar (Cartera)

- **Archivo:** `reportes_cartera.py`
- **Endpoints:** `GET /reportes/cartera`, `GET /reportes/cartera/por-mes`, `GET /reportes/exportar/cartera`
- **Dependencia:** `Depends(get_db)`, `get_current_user`

**Tablas y campos:**

| Tabla | Campos usados |
|-------|----------------|
| **clientes** | id, estado |
| **prestamos** | id, cliente_id, estado |
| **cuotas** | id, prestamo_id, monto, fecha_pago, fecha_vencimiento |

**Lógica:** Solo clientes ACTIVOS y préstamos APROBADOS. Cartera = cuotas sin fecha_pago; distribuciones por monto y por rango de mora; por-mes = cuotas por día de vencimiento en cada mes.

---

## 3. Morosidad (clientes 90+ días)

- **Archivo:** `reportes_morosidad.py`
- **Endpoints:** `GET /reportes/morosidad/clientes`, `GET /reportes/exportar/morosidad-clientes`
- **Dependencia:** `Depends(get_db)`, `get_current_user`

**Tablas y campos:**

| Tabla | Campos usados |
|-------|----------------|
| **clientes** | id, nombres, cedula, estado |
| **prestamos** | id, cliente_id, estado |
| **cuotas** | id, prestamo_id, monto, fecha_pago, fecha_vencimiento |

**Lógica:** Cuotas sin pagar con fecha_vencimiento &lt; (fecha_corte - 89 días); agrupado por cliente (nombre, cédula, cantidad cuotas, total USD).

---

## 4. Vencimiento / Pago vencido (informe por mes y por rangos)

- **Archivo:** `reportes_morosidad.py`
- **Endpoints:** `GET /reportes/morosidad`, `GET /reportes/morosidad/por-mes`, `GET /reportes/morosidad/por-rangos`, `GET /reportes/exportar/morosidad`
- **Dependencia:** `Depends(get_db)`, `get_current_user`

**Tablas y campos:**

| Tabla | Campos usados |
|-------|----------------|
| **clientes** | id, estado |
| **prestamos** | id, cliente_id, estado, cedula, nombres, total_financiamiento, analista, concesionario |
| **cuotas** | id, prestamo_id, monto, fecha_pago, fecha_vencimiento, total_pagado |

**Lógica:** Préstamos con cuotas impagas y vencidas; totales por analista; detalle por préstamo; por-rangos = 1-14, 15-29, 30-59, 60-89, 90+ días; por-mes = fecha de corte fin de mes con morosidad por cédula.

---

## 5. Pagos

- **Archivo:** `reportes_pagos.py`
- **Endpoints:** `GET /reportes/pagos`, `GET /reportes/pagos/por-mes`, `GET /reportes/pagos/por-dia-mes`, `GET /reportes/exportar/pagos`
- **Dependencia:** `Depends(get_db)`, `get_current_user`

**Tablas y campos:**

| Origen | Tabla | Campos usados |
|--------|--------|----------------|
| JSON (get_reporte_pagos) | **clientes** | id, estado |
| | **prestamos** | id, cliente_id, estado |
| | **cuotas** | id, prestamo_id, monto, fecha_pago |
| Excel por mes / por-dia-mes | **pagos** | id, fecha_pago, prestamo_id, cedula_cliente, monto_pagado, numero_documento |
| Excel por mes (nombres) | **prestamos** | id, nombres |
| | **clientes** | cedula, nombres |

**Nota:** El reporte JSON por rango de fechas filtra por Cliente.estado ACTIVO y Prestamo.estado APROBADO. El Excel “por mes” (una hoja por mes) se construye desde la tabla **pagos** sin filtrar por estado de cliente/préstamo; por tanto incluye todos los registros de `pagos` en ese período. Si se desea restringir a clientes activos y préstamos aprobados también en el Excel de pagos por mes, habría que añadir join a Prestamo y Cliente y aplicar los mismos filtros.

---

## 6. Contable

- **Archivo:** `reportes_contable.py`
- **Endpoints:** `GET /reportes/contable/cedulas`, `GET /reportes/exportar/contable`
- **Dependencia:** `Depends(get_db)`, `get_current_user`

**Tablas y campos:**

| Tabla | Campos usados |
|-------|----------------|
| **clientes** | id, estado |
| **prestamos** | id, cliente_id, cedula, nombres, estado |
| **cuotas** | id, prestamo_id, numero_cuota, fecha_vencimiento, fecha_pago, monto, total_pagado, pago_id |
| **pagos** | id, fecha_pago (como fecha_pago_real cuando Cuota.pago_id existe) |
| **reporte_contable_cache** | cuota_id, cedula, nombre, tipo_documento, fecha_vencimiento, fecha_pago, importe_md, moneda_documento, tasa, importe_ml, moneda_local |

**Lógica:** Datos vivos desde Cuota + Prestamo + Cliente (+ Pago opcional) para alimentar el cache; exportación lee desde `reporte_contable_cache` filtrado por años, meses y opcionalmente cédulas. Búsqueda de cédulas usa cache o, si está vacío, Prestamo/Cuota/Cliente.

---

## 7. Por cédula

- **Archivo:** `reportes_cedula.py`
- **Endpoints:** `GET /reportes/por-cedula`, `GET /reportes/exportar/cedula`
- **Dependencia:** `Depends(get_db)`, `get_current_user`

**Tablas y campos:**

| Tabla | Campos usados |
|-------|----------------|
| **prestamos** | id, cliente_id, cedula, nombres, total_financiamiento, numero_cuotas |
| **pagos** | prestamo_id, monto_pagado |
| **cuotas** | prestamo_id, estado, monto |
| **clientes** | id, cedula, nombres (fallback si Prestamo no tiene cedula/nombres) |

**Lógica:** Lista de préstamos APROBADOS; por préstamo: total abono desde Pago, cuotas pagadas/atrasadas y monto atrasado desde Cuota; cedula/nombre desde Prestamo o Cliente.

---

## 8. Asesores (Pago vencido por analista)

- **Archivo:** `reportes_asesores.py`
- **Endpoints:** `GET /reportes/asesores`, `GET /reportes/asesores/por-mes`
- **Dependencia:** `Depends(get_db)`, `get_current_user`

**Tablas y campos:**

| Tabla | Campos usados |
|-------|----------------|
| **clientes** | id, estado |
| **prestamos** | id, cliente_id, estado, analista |
| **cuotas** | id, prestamo_id, monto, fecha_pago, fecha_vencimiento |

**Lógica:** Solo clientes ACTIVOS y préstamos APROBADOS; resumen por analista (cartera, morosidad, cobrado, porcentajes); por-mes = cuotas con vencimiento en el mes y sin pagar, agrupadas por analista.

---

## Conclusión

- **Todos los reportes** del Centro de Reportes (resumen KPIs, Cartera, Morosidad, Vencimiento/Pago vencido, Pagos, Contable, Por cédula, Asesores) están **conectados a la base de datos** mediante los modelos `Cliente`, `Prestamo`, `Cuota`, `Pago` y, en Contable, `ReporteContableCache`.
- No se usan stubs ni datos fijos para los datos de negocio; todos los endpoints inyectan `get_db` y ejecutan consultas sobre las tablas indicadas.
- **Única observación:** En el reporte de **Pagos** exportado a Excel “por mes”, los datos provienen solo de la tabla **pagos** sin filtrar por cliente activo ni préstamo aprobado. El resto de reportes que deben restringir a cartera vigente aplican filtros sobre Cliente y Prestamo.

Si se desea que el Excel de Pagos por mes refleje únicamente clientes ACTIVOS y préstamos APROBADOS, habría que modificar `_pagos_por_dia_periodos` en `reportes_pagos.py` para unir `Pago` con `Prestamo` y `Cliente` y aplicar esos filtros.
