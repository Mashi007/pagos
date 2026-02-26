# Verificación: Todos los reportes se descargan en Excel

**Fecha:** 2026-02-25  
**Objetivo:** Confirmar que cada reporte del Centro de Reportes (https://rapicredit.onrender.com/pagos/reportes) se descarga en formato Excel (.xlsx).

---

## Resumen

| Reporte (icono) | Llamada frontend | Parámetro formato | Backend devuelve | Nombre archivo |
|-----------------|------------------|--------------------|------------------|----------------|
| Cuentas por cobrar (Cartera) | `exportarReporteCartera('excel', ...)` | `formato=excel` | Excel (spreadsheetml) | `reporte_cartera_YYYY-MM-DD.xlsx` |
| Pagos | `exportarReportePagos('excel', ...)` | `formato=excel` | Excel | `reporte_pagos_YYYY-MM-DD.xlsx` |
| Morosidad | `exportarReporteMorosidadClientes(...)` | — | Excel (único formato) | `reporte_morosidad_YYYY-MM-DD.xlsx` |
| Vencimiento | `exportarReporteMorosidad('excel', ...)` | `formato=excel` | Excel | `informe_vencimiento_pagos_YYYY-MM-DD.xlsx` |
| Pago vencido (Asesores) | `exportarReporteMorosidad('excel', ...)` | `formato=excel` | Excel | `reporte_pago_vencido_YYYY-MM-DD.xlsx` |
| Contable | `exportarReporteContable(...)` | — | Excel (único formato) | `reporte_contable_YYYY-MM-DD.xlsx` |
| Por cédula | `exportarReporteCedula()` | — | Excel (único formato) | `reporte_por_cedula_YYYY-MM-DD.xlsx` |

**Conclusión:** Los siete reportes que ofrece la página se descargan en Excel (.xlsx). El frontend usa siempre `ext = 'xlsx'` para el nombre del archivo y, en los endpoints que admiten Excel/PDF, envía `formato=excel`. El backend responde con `media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"` y genera el contenido con `openpyxl`.

---

## Detalle por reporte

### 1. Cuentas por cobrar (Cartera)

- **Frontend:** `reporteService.exportarReporteCartera('excel', fechaCorte, filtros)` → query `formato=excel`.
- **Backend:** `exportar_cartera(formato=Query("excel", pattern="^(excel|pdf)$"), ...)`. Si `formato == "excel"` → `_generar_excel_cartera_por_mes` → `Response(..., media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=reporte_cartera_*.xlsx)`.
- **Resultado:** Descarga en Excel.

### 2. Pagos

- **Frontend:** `reporteService.exportarReportePagos('excel', undefined, undefined, 12, filtros)` → query `formato=excel`.
- **Backend:** `exportar_pagos(formato=Query("excel", ...), ...)`. Si `formato == "excel"` → `_generar_excel_pagos_por_mes` → `Response(..., spreadsheetml.sheet, filename=reporte_pagos_*.xlsx)`.
- **Resultado:** Descarga en Excel.

### 3. Morosidad

- **Frontend:** `reporteService.exportarReporteMorosidadClientes(fechaCorte)` (sin parámetro formato).
- **Backend:** `exportar_morosidad_clientes` solo genera Excel con `openpyxl` → `Response(..., spreadsheetml.sheet, filename=reporte_morosidad_*.xlsx)`.
- **Resultado:** Descarga en Excel.

### 4. Vencimiento

- **Frontend:** `reporteService.exportarReporteMorosidad('excel', fechaCorte, filtros)` → query `formato=excel`.
- **Backend:** `exportar_morosidad(formato=Query("excel", ...), ...)`. Si `formato != "pdf"` (por tanto excel) → `_generar_excel_morosidad_por_mes` → `Response(..., spreadsheetml.sheet, filename=informe_vencimiento_pagos_*.xlsx)`.
- **Resultado:** Descarga en Excel.

### 5. Pago vencido (Asesores)

- **Frontend:** Mismo endpoint que Vencimiento: `reporteService.exportarReporteMorosidad('excel', fechaCorte, filtros)`.
- **Backend:** Igual que Vencimiento; solo cambia el nombre del archivo en el frontend: `reporte_pago_vencido_*.xlsx`.
- **Resultado:** Descarga en Excel.

### 6. Contable

- **Frontend:** `reporteService.exportarReporteContable(filtros.años, filtros.meses, cedulas)` (sin formato).
- **Backend:** `exportar_contable` solo genera Excel → `_generar_excel_contable` → `Response(..., spreadsheetml.sheet, filename=reporte_contable_*.xlsx)`.
- **Resultado:** Descarga en Excel.

### 7. Por cédula

- **Frontend:** `reporteService.exportarReporteCedula()` (sin formato).
- **Backend:** `exportar_cedula` solo genera Excel → `_generar_excel_por_cedula` → `Response(..., spreadsheetml.sheet, filename=reporte_por_cedula_*.xlsx)`.
- **Resultado:** Descarga en Excel.

---

## Frontend: extensión y tipo de contenido

- En `Reportes.tsx`, dentro de `generarReporte`, se define `const ext = 'xlsx'` y se usa en todos los nombres de archivo (salvo Contable, que ya usa `.xlsx` explícito).
- Todas las descargas usan `descargarBlob(blob, nombre)` con nombre terminado en `.xlsx`.
- Los servicios que admiten Excel/PDF reciben siempre el primer argumento `'excel'`, por lo que la petición al backend incluye `formato=excel` y el backend devuelve Excel.

---

## Backend: medios y generación

- Endpoints que solo devuelven Excel (sin opción PDF): **morosidad-clientes**, **contable**, **cedula**. Usan `openpyxl` y `media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"`.
- Endpoints que aceptan `formato=excel|pdf` (cartera, pagos, morosidad/vencimiento): cuando `formato=excel` (o no es `"pdf"` en morosidad) devuelven Excel con el mismo `media_type` y archivos `.xlsx`.

No hay ningún reporte de la página que, con el flujo actual, se descargue en PDF; todos se descargan en Excel.
