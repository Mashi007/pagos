# Verificación: Proceso de Carga de Datos (Individual y Masivo)

**Fecha:** 18 de febrero de 2025  
**Alcance:** Carga individual de pagos, carga masiva Excel y conciliación.

---

## 1. Resumen

| Proceso | Frontend | Backend | Estado |
|---------|----------|---------|--------|
| **Carga individual** | RegistrarPagoForm | POST /pagos | ✅ Verificado |
| **Carga masiva** | ExcelUploader | POST /pagos/upload | ✅ Verificado |
| **Conciliación** | ConciliacionExcelUploader | POST /pagos/conciliacion/upload | ✅ Verificado |

---

## 2. Carga Individual (Registrar Pago)

### 2.1 Flujo

1. Usuario abre modal "Registrar Pago" desde PagosList.
2. Ingresa cédula → se buscan préstamos por cédula (GET /prestamos/cedula/{cedula}).
3. Selecciona crédito (opcional si hay préstamos; obligatorio si hay).
4. Ingresa fecha, monto, número de documento, institución bancaria, notas.
5. Envía → POST /pagos (crear) o PUT /pagos/{id} (editar).

### 2.2 Validaciones frontend

| Campo | Validación |
|-------|------------|
| Cédula | Obligatoria |
| ID Crédito | Obligatorio si hay préstamos para la cédula |
| Cédula vs préstamo | Debe coincidir con la cédula del préstamo seleccionado |
| Monto | > 0 y ≤ 1.000.000 |
| Nº documento | Obligatorio; normalización de formato científico (7.4E+14 → 740087...) |
| Fecha | Obligatoria; no puede ser futura |

### 2.3 Validaciones backend

- Nº documento único (409 si ya existe).
- Pydantic valida tipos (fecha, monto Decimal, etc.).

### 2.4 Observaciones

- ✅ Auto-selección de préstamo si solo hay uno.
- ✅ Indicador visual de coincidencia cédula pago vs préstamo.
- ⚠️ `console.log` en handleSubmit (líneas 142-148, 154) — considerar eliminar en producción.

---

## 3. Carga Masiva (Excel)

### 3.1 Flujo

1. Usuario selecciona archivo (.xlsx, .xls).
2. Frontend valida con `validateExcelFile`: extensión, MIME, tamaño ≤10 MB, no vacío.
3. Usuario hace clic en "Cargar Pagos".
4. POST /pagos/upload con FormData.
5. Backend procesa filas desde la 2 (fila 1 = encabezados).
6. Respuesta: registros_procesados, filas_omitidas, errores, errores_detalle, errores_total, errores_truncados.

### 3.2 Formatos aceptados (backend)

**Formato estándar** (columnas en orden):
1. Cédula (obligatorio)
2. ID Préstamo (opcional)
3. Fecha de pago
4. Monto pagado (> 0)
5. Número de documento

**Formato alternativo** (detección automática):
1. Fecha
2. Cédula
3. Cantidad (monto)
4. Documento

### 3.3 Reglas de procesamiento

- Filas omitidas: cédula vacía o monto ≤ 0.
- Nº documento: no puede repetirse en el archivo ni en BD.
- Cédula: regex `^[VJ]\d{7,9}$` para formato alternativo.
- Fechas: `%d-%m-%Y`, `%Y-%m-%d`, `%d/%m/%Y`.

### 3.4 Validación frontend (excelValidation.ts)

| Validación | Límite |
|------------|--------|
| Extensión | .xlsx, .xls |
| Tamaño | 10 MB |
| Archivo vacío | Rechazado |
| Nombre archivo | Caracteres peligrosos → warning |

### 3.5 Respuesta y UI

- Muestra registros procesados, filas omitidas, errores.
- Tabla de errores detallados con descarga CSV.
- Aviso de truncamiento si hay > 50 errores o > 100 detalles.

### 3.6 Observaciones

- ✅ Backend valida Nº documento único en archivo y BD.
- ✅ Transacción: commit al final; rollback en excepción.
- ⚠️ Backend no limita tamaño de archivo ni número de filas (el frontend limita a 10 MB; validateWorkbookStructure existe pero no se usa antes del upload).

---

## 4. Conciliación (Excel)

### 4.1 Flujo

1. Usuario selecciona archivo Excel.
2. Misma validación `validateExcelFile` que carga masiva.
3. POST /pagos/conciliacion/upload.
4. Backend espera 2 columnas: Fecha de Depósito, Número de Documento.
5. Por cada Nº documento: busca pago en BD; si existe, marca conciliado y fecha_conciliacion.

### 4.2 Formato esperado

| Columna 1 | Columna 2 |
|-----------|-----------|
| Fecha de Depósito | Número de Documento |

### 4.3 Respuesta

- pagos_conciliados
- pagos_no_encontrados (documentos_no_encontrados)
- errores, errores_detalle

### 4.4 Observaciones

- ✅ Marca pagos como conciliados con fecha en zona America/Caracas.
- ✅ Muestra documentos no encontrados en la UI.

---

## 5. Checklist de verificación

- [ ] Carga individual: crear pago con datos válidos.
- [ ] Carga individual: editar pago existente.
- [ ] Carga individual: validación cédula vs préstamo.
- [ ] Carga individual: error 409 si Nº documento duplicado.
- [ ] Carga masiva: archivo formato estándar (Cédula, ID, Fecha, Monto, Doc).
- [ ] Carga masiva: archivo formato alternativo (Fecha, Cédula, Cantidad, Doc).
- [ ] Carga masiva: filas omitidas (cédula vacía, monto ≤ 0).
- [ ] Carga masiva: error por Nº documento duplicado en archivo.
- [ ] Carga masiva: error por Nº documento ya existente en BD.
- [ ] Carga masiva: descarga CSV de errores.
- [ ] Conciliación: marcar pagos como conciliados.
- [ ] Conciliación: mostrar documentos no encontrados.
