# Auditoría integral: Carga masiva de pagos desde Excel

**Alcance:** Flujo completo desde la opción "Pagos (Excel)" en la UI (Cargar datos → Pagos (Excel)) hasta la persistencia en BD y aplicación a cuotas.  
**Fecha:** 2025-03-09

---

## 1. Puntos de entrada en la UI

| Ubicación | Componente | Descripción |
|-----------|------------|-------------|
| **Cargar datos → Pagos (Excel)** | `CargaMasivaMenu.tsx` → `ExcelUploaderPagosUI` | Modal de carga con previsualización, tabla editable y guardado fila a fila o en lote. |
| **PagosList** (pestaña/acción) | `ExcelUploaderPagosUI` | Mismo flujo: previsualización + edición + guardar. |
| **ExcelUploader** (pagos) | `ExcelUploader.tsx` | Flujo alternativo: sube el archivo completo al backend (POST /pagos/upload) sin previsualización. No está enlazado desde el menú "Pagos (Excel)" actual. |

La opción de la imagen **"Pagos (Excel)"** corresponde al flujo **ExcelUploaderPagosUI** (parse en navegador + tabla editable + guardar por filas o “Guardar todos”).

---

## 2. Flujos de carga

### 2.1 Flujo A: Previsualización y guardado desde tabla (actual en menú)

1. Usuario abre **Cargar datos** → **Pagos (Excel)**.
2. **Frontend** (`ExcelUploaderPagosUI` + `useExcelUploadPagos`):
   - Selecciona o arrastra archivo `.xlsx`/`.xls`.
   - Valida archivo con `validateExcelFile()` (tamaño ≤ 10 MB, extensión, MIME opcional) — `frontend/src/utils/excelValidation.ts`.
   - Parsea el Excel en el navegador (ExcelJS/u equivalente en el hook), construye filas con columnas: Cédula, Fecha pago, Monto, Documento, ID Préstamo (opcional), Conciliación.
   - Llama a **POST /api/v1/pagos/validar-filas-batch** con listas de cédulas y documentos para obtener:
     - `cedulas_existentes`: cédulas que existen en tabla `clientes`.
     - `documentos_duplicados`: documentos que ya existen en tabla `pagos` (considerados duplicados).
   - Marca filas con errores (`_hasErrors`, `_validation`) y rellena `prestamosPorCedula` (desde **GET /api/v1/prestamos/cedula/{cedula}` o batch).
3. Usuario ve la **tabla editable** (`TablaEditablePagos`): puede corregir cédula, fecha, monto, documento, crédito (selector si hay varios préstamos) y conciliación.
4. Guardado:
   - **Guardar** (una fila): **POST /api/v1/pagos** (`pagoService.createPago`) con el cuerpo del pago. No se usa `guardar-fila-editable` en este flujo.
   - **Guardar todos**: se recorren las filas válidas y se llama `createPago` por cada una (en secuencia o con control de concurrencia).
   - Si el backend responde **409** (documento duplicado): el frontend puede enviar la fila a **Revisar Pagos** vía `pagoConErrorService.create` (tabla `pagos_con_errores`).
5. Tras guardar, se invalida caché/lista de pagos y se puede redirigir a `/pagos` o a Revisar Pagos.

**Endpoints utilizados en este flujo:**  
`POST /api/v1/pagos/validar-filas-batch`, `GET /api/v1/prestamos/cedula/{cedula}` (o similar para créditos por cédula), `POST /api/v1/pagos` (crear pago), `POST /api/v1/pagos/con-errores` (crear pago con error para Revisar Pagos).

### 2.2 Flujo B: Subida directa (archivo completo al backend)

1. Usuario usa el componente **ExcelUploader** (pagos) — si está expuesto en la app.
2. Selecciona archivo; se valida con `validateExcelFile()` (mismo límite 10 MB).
3. **POST /api/v1/pagos/upload** con `multipart/form-data` (campo `file`).
4. **Backend** (`upload_excel_pagos` en `backend/app/api/v1/endpoints/pagos.py`):
   - Comprueba extensión `.xlsx`/`.xls` y tamaño ≤ 10 MB.
   - Límite de filas: 10 000 (rechazo si se supera); recomendado 2 500 (solo log de advertencia).
   - Lee el Excel con `openpyxl` (solo primera hoja, desde fila 2).
   - Detecta formato de columnas (Formato D: Cédula, Monto, Fecha, Documento; Formato A: Documento, Cédula, Fecha, Monto; Formato B: Fecha, Cédula, Monto, Documento; Formato C: Cédula, ID Préstamo, Fecha, Monto, Documento).
   - Por cada fila: normaliza cédula/documento, valida monto (`_validar_monto`), descarta cédula vacía o monto ≤ 0 (y opcionalmente las registra en `pagos_con_error_list`).
   - Fase 2: comprueba duplicados de documento en el archivo y en BD (consulta en chunks a `pagos.numero_documento`). Si la cédula tiene más de un préstamo y no se indicó `prestamo_id`, rechaza la fila.
   - Inserta en tabla `pagos` (estado PENDIENTE, `usuario_registro` desde JWT).
   - Persiste filas con error de validación en tabla **`pagos_con_errores`** (`PagoConError`: cedula, prestamo_id, fecha_pago, monto_pagado, numero_documento, errores_descripcion, observaciones, fila_origen).
   - Para cada pago insertado con `prestamo_id` y monto > 0, llama a **`_aplicar_pago_a_cuotas_interno`** (aplica monto a cuotas del préstamo, actualiza estado a PAGADO si aplicó).
   - `db.commit()` y devuelve resumen: `registros_procesados`, `registros_con_error`, `cuotas_aplicadas`, `pagos_articulados`, `errores`, `errores_detalle`, `pagos_con_errores` (para revisión).

**Endpoints:** solo **POST /api/v1/pagos/upload**.

---

## 3. Endpoints implicados

| Método | Ruta | Uso en carga masiva |
|--------|------|----------------------|
| POST | `/api/v1/pagos/upload` | Flujo B: subida de archivo completo; parse y persistencia en backend. |
| POST | `/api/v1/pagos/validar-filas-batch` | Flujo A: validar cédulas (existen en `clientes`) y documentos (duplicados en `pagos`). |
| POST | `/api/v1/pagos` | Flujo A: crear un pago (por fila) desde la tabla editable. |
| POST | `/api/v1/pagos/guardar-fila-editable` | Guardar una fila ya validada (formato DD-MM-YYYY, conciliado=True); no usado por el modal actual de "Pagos (Excel)". |
| GET  | `/api/v1/prestamos/cedula/{cedula}` (o batch) | Flujo A: obtener préstamos activos por cédula para el selector de crédito. |
| POST | `/api/v1/pagos/con-errores` | Flujo A: enviar fila a Revisar Pagos (duplicados/errores). |

---

## 4. Validaciones

### 4.1 Frontend

- **Archivo:** `validateExcelFile()` — extensión `.xlsx`/`.xls`, tamaño ≤ 10 MB, no vacío, nombre sin caracteres peligrosos.
- **Filas (hook):** Cédula (existencia en clientes vía validar-filas-batch), documento (duplicado en archivo o en BD), fecha, monto, crédito (obligatorio si la cédula tiene más de un préstamo), conciliación.
- **Guardar:** Solo filas sin `_hasErrors`; si hay 409 se ofrece enviar a Revisar Pagos.

### 4.2 Backend (upload y crear pago)

- **Upload:** Extensión y tamaño (10 MB); máximo 10 000 filas (rechazo); recomendado 2 500.
- **Cédula:** Formato tipo V/E/J/Z + 6–11 dígitos; en upload, si cédula tiene >1 préstamo y no hay `prestamo_id` → rechazo.
- **Monto:** > 0 y ≤ 999_999_999_999.99; detección de fechas Excel mal interpretadas como monto.
- **Documento:** Cualquier formato; normalización en `app.core.documento.normalize_documento`. Regla única: **no duplicados** (ni en archivo ni en BD). Longitud ≤ 100 caracteres.
- **Crear pago (POST /pagos):** Mismas reglas de negocio; 409 si `numero_documento` ya existe.

---

## 5. Tablas y persistencia

| Tabla | Uso en carga masiva |
|-------|----------------------|
| **pagos** | Inserción de cada pago válido (upload o createPago). FK `prestamo_id` (opcional). |
| **pagos_con_errores** | Filas con error de validación (upload) o filas enviadas a “Revisar Pagos” (duplicados/422 desde el frontend). |
| **cuotas** / **cuota_pagos** | Tras insertar pago con `prestamo_id`, `_aplicar_pago_a_cuotas_interno` aplica el monto a cuotas (FIFO) y crea/actualiza `cuota_pagos`. |
| **clientes** | Solo lectura: validar que la cédula exista (validar-filas-batch y lógica de préstamos por cédula). |
| **prestamos** | Solo lectura: contar préstamos por cédula (upload) y listar créditos activos para el selector (flujo A). |

---

## 6. Concatenación de datos (JOINs)

- **Upload:** Para “cédula con más de un préstamo” se hace `Prestamo JOIN Cliente` por `Cliente.cedula`. Para aplicar a cuotas se usan `Pago`, `Cuota`, `CuotaPago` y relaciones por `prestamo_id`/`pago_id`/`cuota_id`.
- **Validar-filas-batch:** Consultas a `Clientes.cedula` y `Pago.numero_documento` (sin JOIN entre sí).
- **Crear pago:** Inserción en `pagos`; si el endpoint de creación aplica a cuotas, se usa la misma lógica interna que en upload.

---

## 7. Seguridad y buenas prácticas

- **Autenticación:** El router de pagos tiene `dependencies=[Depends(get_current_user)]`, por lo que todos los endpoints (upload, validar-filas-batch, guardar-fila-editable, crear pago) exigen usuario autenticado.
- **Límites:** Tamaño 10 MB y 10 000 filas evitan abusos; 2 500 filas recomendado para evitar timeouts.
- **Documento:** Normalización única y rechazo de duplicados reducen inconsistencias.
- **Errores:** Filas fallidas se guardan en `pagos_con_errores` para trazabilidad y revisión manual.

---

## 8. Riesgos e inconsistencias detectadas

1. **Dos flujos sin unificación:** El menú “Pagos (Excel)” solo usa el flujo con previsualización (createPago fila a fila). El flujo de upload directo (ExcelUploader + POST /upload) no está accesible desde ese menú; si se quiere ofrecer “subir y procesar todo”, habría que enlazarlo o unificar criterios (p. ej. mismo formato de columnas y mismas reglas de error).
2. **Formato A/B/C en upload (corregido):** Se ha actualizado el backend para que, cuando el monto es inválido en los formatos A, B o C, la fila se añada a `pagos_con_error_list` y quede registrada en `pagos_con_errores`.
3. **Respuesta `pagos_con_errores` en upload:** La respuesta construye la lista de `pagos_con_errores` con una query por `fila_origen`; si hay muchas filas con error, asegurarse de que la query no falle por límite de parámetros IN (p. ej. chunking o límite de ítems devueltos).
4. **Guardar todos (flujo A):** Si hay muchas filas, muchas llamadas secuenciales a POST /pagos pueden provocar timeouts o lentitud; valorar batch en backend (p. ej. endpoint que acepte un array de pagos) o mantener solo “Guardar” por fila y recomendar upload directo para lotes grandes.
5. **Validar-filas-batch:** Ya está protegido por el mismo `get_current_user` del router (dependencia global del router de pagos).

---

## 9. Recomendaciones

1. **Unificar criterio de “Pagos (Excel)”:** Decidir si el menú debe ofrecer solo previsualización + guardado por filas, solo upload directo, o ambas con etiquetas claras (“Previsualizar y editar” vs “Subir y procesar todo”).
2. **Registrar todos los errores de validación en upload:** Hecho: los formatos A, B y C ya añaden a `pagos_con_error_list` cuando el monto es inválido (y Formato D ya lo hacía).
3. **Validar-filas-batch:** Ya protegido por dependencia global del router; no requiere cambio.
4. **Batch de creación (opcional):** Para “Guardar todos”, valorar un endpoint tipo `POST /api/v1/pagos/batch` que reciba un array de pagos y devuelva éxitos/errores por índice, para reducir rondas y timeouts.
5. **Documentar formatos de Excel:** En la UI (tooltip o ayuda) y en el código (docstrings), dejar explícitos los órdenes de columna soportados (D, A, B, C) y el recomendado (p. ej. Cédula | Fecha | Monto | Documento | ID Préstamo opcional | Conciliación).
6. **Timeout de upload:** El proxy/frontend ya tiene timeouts mayores para `/pagos/upload`; asegurar que el backend no corte la request antes (p. ej. límite de tiempo en uvicorn/gunicorn). *Implementado:* docstring de `POST /pagos/upload` documenta que en producción debe configurarse timeout del servidor (uvicorn/gunicorn o proxy) suficientemente alto (p. ej. 120 s).

---

## 10. Resumen

- **Entrada principal “Pagos (Excel)”:** Abre **ExcelUploaderPagosUI**: parse en cliente, validación con **validar-filas-batch** y préstamos por cédula, tabla editable, guardado con **POST /pagos** por fila (o “Guardar todos” en bucle). Duplicados/errores pueden enviarse a **Revisar Pagos** (tabla `pagos_con_errores`).
- **Flujo alternativo:** **ExcelUploader** + **POST /pagos/upload**: todo en backend (openpyxl, validación, inserción, aplicación a cuotas, registro de errores en `pagos_con_errores`).
- **Validaciones:** Cédula, monto, documento (sin duplicados), préstamo obligatorio cuando hay más de un crédito por cédula; límites de archivo y filas en backend.
- **BD:** Inserción en `pagos`; errores en `pagos_con_errores`; aplicación a `cuotas`/`cuota_pagos` vía `_aplicar_pago_a_cuotas_interno`.
- **Mejoras sugeridas:** Registrar siempre filas con error en upload en `pagos_con_errores`, proteger validar-filas-batch, unificar o clarificar los dos flujos de carga y valorar un endpoint batch para “Guardar todos”.
