# Análisis del reporte Contable – Funcionamiento total

**Página:** [https://rapicredit.onrender.com/pagos/reportes](https://rapicredit.onrender.com/pagos/reportes)  
**Elemento:** tarjeta "Contable" (icono calculadora azul).

---

## 1. Flujo de usuario (UX)

1. **Entrada:** El usuario hace clic en la tarjeta **Contable** en el Centro de Reportes.
2. **Diálogo en 3 pasos** (`DialogReporteContableFiltros`):
   - **Paso 1:** Selección de **años** (actual y hasta 4 anteriores). Obligatorio al menos uno.
   - **Paso 2:** Selección de **meses** (Ene–Dic). Obligatorio al menos uno.
   - **Paso 3:** Filtro por **cédulas**:
     - Opción "Todas las cédulas", o
     - Búsqueda por cédula/nombre (llamada a `GET /reportes/contable/cedulas?q=...`) y selección de una o varias.
3. **Descarga:** Al pulsar "Descargar" se llama al backend para generar Excel y se descarga `reporte_contable_YYYY-MM-DD.xlsx`.
4. **Feedback:** Toast de carga ("Preparando descarga de Contable..."), luego éxito o aviso si el reporte viene vacío (`X-Reporte-Contable-Vacio: 1`).

No hay vista previa en pantalla: el único resultado es el archivo Excel.

---

## 2. Frontend

### 2.1 Página Reportes (`Reportes.tsx`)

- La tarjeta Contable tiene `value: 'CONTABLE'` e `icon: Calculator`.
- Al hacer clic en Contable no se usa el diálogo genérico `DialogReporteFiltros`; se abre solo `DialogReporteContableFiltros` cuando `reporteSeleccionado === 'CONTABLE'`.
- Al confirmar filtros se ejecuta `generarReporteContable(filtros)` (no `generarReporte`).

### 2.2 Diálogo Contable (`DialogReporteContableFiltros.tsx`)

- **Estado:** años/meses como `Set<number>`, cédulas como `Set<string>` o "todas".
- **Búsqueda de cédulas:** En paso 3, con debounce 300 ms, llama a `reporteService.buscarCedulasContable(busquedaCedula)`.
- **Confirmación:** `onConfirm({ años, meses, cedulas })` con `cedulas` en formato `number[]`, `number[]` y `string[] | 'todas'`.

### 2.3 Servicio (`reporteService.ts`)

- **`buscarCedulasContable(q?: string)`**  
  - `GET /reportes/contable/cedulas?q=...`  
  - Devuelve `{ cedulas: Array<{ cedula, nombre }> }`.

- **`exportarReporteContable(años, meses, cedulas?)`**  
  - Parámetros enviados en query: **`anos`** (sin tilde), **`meses`**, **`cedulas`** (opcional, separadas por coma).  
  - `GET /reportes/exportar/contable?anos=...&meses=...&cedulas=...`  
  - `responseType: 'blob'`, timeout 180 s.  
  - Lee el header `X-Reporte-Contable-Vacio` para avisar si no hay datos.

La API espera el parámetro **`anos`** (el backend acepta también `años` por compatibilidad).

---

## 3. Backend

### 3.1 Endpoints (prefix `/reportes`)

| Método | Ruta | Función | Uso |
|--------|------|---------|-----|
| GET | `/contable/cedulas` | `buscar_cedulas_contable` | Búsqueda para filtro en paso 3 |
| GET | `/exportar/contable` | `exportar_contable` | Genera y devuelve Excel |

No existe un `GET /contable` que devuelva JSON (solo exportación Excel).

### 3.2 Datos y cache

- **Origen:** Cuotas con pago en el rango de fechas (clientes ACTIVO, préstamos APROBADO, `Cuota.fecha_pago` no nula).
- **Tabla de cache:** `reporte_contable_cache` (por `cuota_id`, cédula, nombre, tipo_documento, fechas, importes MD/ML, tasa, monedas).
- **Política de cache:**
  - Si la cache está vacía → `sync_reporte_contable_completo(db)` (histórico desde 2000-01-01 hasta hoy).
  - Si ya hay datos → `refresh_cache_ultimos_7_dias(db)`: se borran y reinsertan solo los últimos 7 días (deduplicado por `cuota_id` para evitar UniqueViolation).
- **Tasa USD→Bs:** Por fecha de pago se usa `_obtener_tasa_usd_bs(fecha)` (API configurada o `TASA_USD_BS_DEFAULT`), y se guarda en la fila del cache.

### 3.3 Exportación Excel (`exportar_contable`)

1. Asegura que exista la tabla cache (`create(..., checkfirst=True)`).
2. Actualiza cache (completa o últimos 7 días).
3. Parsea query: `anos`, `meses`, `cedulas`. Si `anos` no viene por nombre estándar, se lee también `años` de `request.query_params` (evita 500 por parámetro con tilde).
4. Obtiene datos con `get_reporte_contable_desde_cache(db, anos=..., meses=..., cedulas=...)`.
5. Genera Excel con `_generar_excel_contable(data)` (openpyxl): cabecera "Reporte Contable", período, columnas Cédula, Nombre, Tipo documento, Fechas, Importe MD, Moneda documento, Tasa, Importe ML, Moneda local.
6. Responde con `Content-Disposition: attachment; filename=reporte_contable_YYYY-MM-DD.xlsx` y, si no hay filas, header `X-Reporte-Contable-Vacio: 1`.

### 3.4 Permisos y BD

- Router con `dependencies=[Depends(get_current_user)]`.
- Todos los endpoints usan `db: Session = Depends(get_db)` y consultas reales a la BD.

---

## 4. Resumen del flujo de datos

```
[Usuario] → Clic "Contable"
    → Reportes.tsx: setReporteSeleccionado('CONTABLE'), setDialogAbierto(true)
    → DialogReporteContableFiltros (paso 1: años, paso 2: meses, paso 3: cédulas)
    → Paso 3: reporteService.buscarCedulasContable(q) → GET /reportes/contable/cedulas
    → Usuario pulsa "Descargar"
    → generarReporteContable(filtros)
    → reporteService.exportarReporteContable(años, meses, cedulas)
    → GET /reportes/exportar/contable?anos=...&meses=...&cedulas=...
    → Backend: actualiza cache → get_reporte_contable_desde_cache() → _generar_excel_contable()
    → Response blob + headers
    → descargarBlob() → toast éxito o "reporte vacío"
```

---

## 5. Comprobaciones realizadas

- **Filtros:** Años, meses y cédulas se envían correctamente y se aplican en backend (periodos por año/mes, opcional filtro por cédula).
- **Parámetro `anos`:** Frontend envía `anos`; backend acepta además `años` en la URL para evitar 500.
- **Cache:** Deduplicación por `cuota_id` y borrado antes de reinsertar en `refresh_cache_ultimos_7_dias` para evitar UniqueViolation.
- **Excel:** Siempre se devuelve un .xlsx; si no hay datos, el archivo incluye mensaje explicativo y se envía `X-Reporte-Contable-Vacio: 1`.
- **Permisos:** Solo usuarios autenticados; permisos por reporte vía `canAccessReport('CONTABLE')` en frontend.

---

## 6. Posibles mejoras (opcionales)

1. **Vista previa:** Añadir un `GET /reportes/contable` que devuelva `{ items, fecha_inicio, fecha_fin }` en JSON para mostrar una tabla en pantalla antes de descargar.
2. **Validación de período:** Avisar en el diálogo que solo habrá datos en meses pasados (cuotas ya pagadas).
3. **Límite de período:** Si el usuario elige muchos años/meses, considerar límite o aviso de tiempo de generación (timeout ya está en 180 s en frontend).
4. **Mensaje de reporte vacío:** El toast actual ya advierte; se podría refinar el texto según si no hay datos en el período o no hay cache aún.

---

**Conclusión:** El reporte Contable en `/pagos/reportes` funciona de extremo a extremo: clic en la tarjeta → diálogo de filtros (años, meses, cédulas) → descarga Excel con datos desde la BD vía cache, con parámetros y cache corregidos (anos/años, UniqueViolation). No hay vista previa en pantalla; el resultado es únicamente el archivo Excel descargado.
