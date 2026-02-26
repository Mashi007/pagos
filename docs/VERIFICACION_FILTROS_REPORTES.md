# Verificación: Filtros activos tras operar los iconos de reportes

**Fecha:** 2026-02-25  
**Objetivo:** Confirmar que, al hacer clic en cada icono del Centro de Reportes y elegir años/meses (y cédulas en Contable), los filtros se envían al backend y se aplican en la generación del reporte.

---

## Resumen

| Reporte | ¿Abre diálogo de filtros? | Filtros (UI) | Params enviados al API | Backend los usa |
|---------|---------------------------|--------------|------------------------|-----------------|
| Cuentas por cobrar (Cartera) | Sí | Años → Meses | `anos`, `meses_list` | Sí (`_periodos_desde_filtros`) |
| Pagos | Sí | Años → Meses | `anos`, `meses_list` | Sí |
| Vencimiento | Sí | Años → Meses | `anos`, `meses_list` | Sí |
| Pago vencido (Asesores) | Sí | Años → Meses | `anos`, `meses_list` | Sí |
| Contable | Sí (diálogo propio) | Años → Meses → Cédulas | `anos`, `meses`, `cedulas` | Sí |
| Morosidad | No (descarga directa) | — | Solo `fecha_corte` | N/A |
| Por cédula | No (descarga directa) | — | Ninguno | N/A |

**Conclusión:** Los filtros están activos: los reportes que muestran diálogo (Cartera, Pagos, Vencimiento, Asesores, Contable) envían años y meses (y cédulas en Contable) al backend, y el backend usa esos parámetros para restringir los periodos y, en Contable, las cédulas.

---

## Flujo por tipo de reporte

### 1. Reportes con diálogo de años/meses (DialogReporteFiltros)

**Iconos:** Cuentas por cobrar, Pagos, Vencimiento, Pago vencido.

1. Usuario hace clic en el icono → `abrirDialogoReporte(tipo)` → `setReporteSeleccionado(tipo)`, `setDialogAbierto(true)`.
2. Se muestra `DialogReporteFiltros` con:
   - Paso 1: selección de años (ej. 2024, 2023).
   - Paso 2: selección de meses (Ene–Dic).
3. Al pulsar **Descargar** → `handleDescargar()` construye `años = Array.from(añosSeleccionados)`, `meses = Array.from(mesesSeleccionados)` y llama `onConfirm({ años, meses })`.
4. En `Reportes.tsx`, `onConfirm` ejecuta `generarReporte(reporteSeleccionado, filtros)`.
5. Según el tipo:
   - **CARTERA:** `reporteService.exportarReporteCartera('excel', fechaCorte, filtros)`.
   - **PAGOS:** `reporteService.exportarReportePagos('excel', undefined, undefined, 12, filtros)`.
   - **VENCIMIENTO / ASESORES:** `reporteService.exportarReporteMorosidad('excel', fechaCorte, filtros)`.

En `reporteService.ts`:

- Si `filtros?.años?.length` → `params.set('anos', filtros.años.join(','))`.
- Si `filtros?.meses?.length` → `params.set('meses_list', filtros.meses.join(','))`.

Backend (cartera, pagos, morosidad, asesores):

- Recibe `anos` y `meses_list` (Query).
- Llama `_periodos_desde_filtros(anos, meses_list, meses)` → genera lista de `(año, mes)` y filtra datos por esos periodos.

Por tanto, los filtros de años y meses **sí están activos** para Cartera, Pagos, Vencimiento y Pago vencido (Asesores).

---

### 2. Reporte Contable (DialogReporteContableFiltros)

1. Usuario hace clic en Contable → `setReporteSeleccionado('CONTABLE')`, `setDialogAbierto(true)`.
2. Se muestra `DialogReporteContableFiltros` con:
   - Paso 1: años.
   - Paso 2: meses.
   - Paso 3: cédulas (buscar/seleccionar o “Todas”).
3. Al pulsar **Descargar** → `onConfirm({ años, meses, cedulas })` → `generarReporteContable(filtros)`.
4. `generarReporteContable` llama `reporteService.exportarReporteContable(filtros.años, filtros.meses, cedulas)`.

En `reporteService.ts` (exportarReporteContable):

- `params.set('anos', años.join(','))` si hay años.
- `params.set('meses', meses.join(','))` si hay meses.
- `params.set('cedulas', cedulas.join(','))` si hay cédulas y no es “todas”.

Backend `exportar_contable`:

- Recibe `anos`, `meses`, `cedulas` (Query).
- Construye `anos_list`, `meses_list`, `cedulas_list` y llama `get_reporte_contable_desde_cache(db, anos=..., meses=..., cedulas=...)`.

Los filtros de años, meses y cédulas **están activos** en el reporte Contable.

---

### 3. Reportes sin diálogo (descarga directa)

- **Morosidad:** clic → `generarReporte('MOROSIDAD', { años: [], meses: [] })` → descarga sin filtros de periodo (usa fecha de corte actual).
- **Por cédula:** clic → `generarReporte('CEDULA', { años: [], meses: [] })` → descarga sin filtros.

No se muestran filtros por diseño; no hay bug.

---

## Cadena frontend → backend

| Paso | Frontend | Backend |
|------|----------|---------|
| 1 | Diálogo devuelve `{ años: [2024,2023], meses: [1,2,3] }` | — |
| 2 | `reporteService` arma query: `anos=2024,2023&meses_list=1,2,3` | — |
| 3 | GET `/api/v1/reportes/exportar/cartera?formato=excel&anos=2024,2023&meses_list=1,2,3` | Recibe `anos`, `meses_list` |
| 4 | — | `_periodos_desde_filtros(anos, meses_list, 12)` → `[(2024,1),(2024,2),(2024,3),(2023,1),...]` |
| 5 | — | Genera Excel solo para esos (año, mes) |

La corrección previa en `reporteService.ts` (enviar el query param `anos` en lugar de `años`) asegura que el backend reciba los años; con eso, los filtros quedan activos de extremo a extremo.

---

## Comprobaciones realizadas

1. **DialogReporteFiltros:** Paso 1 (años) y paso 2 (meses); al Descargar se llama `onConfirm({ años, meses })` con los valores seleccionados.
2. **DialogReporteContableFiltros:** Tres pasos (años, meses, cédulas); al Descargar se llama `onConfirm({ años, meses, cedulas })`.
3. **Reportes.tsx:** `onConfirm` de ambos diálogos invoca `generarReporte` / `generarReporteContable` pasando esos filtros.
4. **reporteService.ts:** Todas las exportaciones que aceptan filtros envían `anos` y `meses_list` (o `meses` en Contable) y, en Contable, `cedulas`.
5. **Backend:** Endpoints de exportación reciben `anos`, `meses_list` (o `meses` en contable) y usan `_periodos_desde_filtros` o equivalente para filtrar por periodo; Contable además filtra por cédulas.

---

## Conclusión

Los filtros **están activos** después de operar los iconos: la selección de años y meses (y cédulas en Contable) se envía correctamente al backend y se aplica en la generación de cada reporte correspondiente.
