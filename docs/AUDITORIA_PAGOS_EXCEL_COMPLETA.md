# Auditoría completa: Pagos (Excel)

**Fecha:** 2025-03-12  
**Alcance:** Flujo completo de carga masiva de pagos desde Excel (dos modos: "Subir y procesar todo" y "Previsualizar y editar"), validadores, persistencia y aplicación a cuotas.

---

## 1. Resumen ejecutivo

Pagos (Excel) ofrece **dos flujos** desde el menú "Cargar datos" → "Pagos desde Excel":

| Modo | Componente | Acción principal | Backend |
|------|------------|------------------|--------|
| **Previsualizar y editar** | `ExcelUploaderPagosUI` + `useExcelUploadPagos` | Usuario ve tabla, edita celdas, guarda filas individuales o envía a Revisar Pagos | `POST /pagos/guardar-fila-editable`, `POST /pagos/con-errores`, etc. |
| **Subir y procesar todo** | `ExcelUploader` | Usuario sube archivo y el servidor procesa todo el Excel de una vez | `POST /pagos/upload` |

En **Subir y procesar todo** el backend hace todo: detección de formato, parseo, validación, inserción en `pagos`, guardado de rechazados en `pagos_con_errores` y aplicación a cuotas. En **Previsualizar y editar** el frontend parsea con ExcelJS, valida con reglas propias y luego guarda fila a fila o envía a Revisar Pagos (tabla `pagos_con_errores`).

---

## 2. Puntos de entrada

- **Menú:** Pagos → "Cargar datos" (popover) → "Pagos desde Excel" → "Previsualizar y editar" **o** "Subir y procesar todo".
- **Archivos:**
  - `frontend/src/components/pagos/CargaMasivaMenu.tsx` – opciones del menú y modales.
  - `frontend/src/components/pagos/ExcelUploaderPagosUI.tsx` – modal Previsualizar.
  - `frontend/src/components/pagos/ExcelUploader.tsx` – modal Subir y procesar.
- **Servicio:** `pagoService.uploadExcel(file)` → `POST /api/v1/pagos/upload`.
- **Backend:** `backend/app/api/v1/endpoints/pagos.py` → `upload_excel_pagos` (líneas ~406–851).

---

## 3. Flujo A: Subir y procesar todo

### 3.1 Frontend (`ExcelUploader.tsx`)

1. Usuario selecciona archivo: se valida con `validateExcelFile` (extensión .xlsx/.xls, tamaño ≤ 10 MB, no vacío, nombre sin caracteres peligrosos).
2. Al hacer clic en "Cargar Pagos" se llama `pagoService.uploadExcel(file)` (timeout 120 s en `api.ts`).
3. Respuesta: `registros_procesados`, `filas_omitidas`, `errores`, `errores_detalle`, `errores_total`, `errores_detalle_total`, `errores_truncados`, `registros_con_error`, `pagos_con_errores` (lista con id, fila_origen, cedula, monto, errores, accion).
4. Se muestran resumen, filas omitidas y tabla de errores (`ErroresDetallados`); se puede descargar CSV de errores.
5. **No** se muestra enlace explícito a "Revisar Pagos" ni se invalida query `pagos-con-errores` cuando hay `registros_con_error > 0` (los errores ya están en BD en `pagos_con_errores`).

### 3.2 Backend (`POST /pagos/upload`)

- **Límites:** archivo ≤ 10 MB, solo .xlsx/.xls, máx. 10.000 filas (recomendado 2.500). Si se supera 10.000 filas se rechaza con 400.
- **Lectura:** openpyxl, `read_only=True`, `data_only=True`, filas desde fila 2 (cabecera en 1).
- **FASE 1 – Parseo por fila:**
  - Se detecta formato por contenido (no por cabeceras):
    - **Formato D (principal):** Cédula, Monto, Fecha, Nº documento (columnas 0–3).
    - **Formato A:** Documento, Cédula, Fecha, Monto.
    - **Formato B:** Fecha, Cédula, Monto, Documento.
    - **Formato C:** Cédula, ID Préstamo, Fecha, Monto, Nº documento.
  - Cédula: `_looks_like_cedula` → `^[VEJ]\d{6,11}$` (sin Z).
  - Monto: `_validar_monto` → float, rango 0.01–999_999_999_999.99; si falla y monto ≠ 0 se añade a `pagos_con_error_list` y se continúa.
  - Fecha: se acepta tal cual para FASE 2; parseo definitivo en inserción con `_parse_fecha` (%d-%m-%Y, %Y-%m-%d, %d/%m/%Y).
  - Documento: `_celda_a_string_documento` (evita notación científica en floats); vacío permitido; si documento vacío se intenta `_extraer_documento_de_fila`.
  - Si cédula vacía o monto ≤ 0 → se añade a `pagos_con_error_list` y no se incluye en `FilasParseadas`.
  - Filas que no coinciden con ningún formato se omiten (no se añaden a errores con mensaje "formato no reconocido").
- **FASE 2 – Validación e inserción:**
  - Se construye set de documentos del archivo (normalizados) y se precargan documentos ya existentes en `pagos` por lotes de 1.000.
  - Por cada fila en `FilasParseadas`:
    - Duplicado en archivo (mismo documento normalizado ya visto en el lote) → a `pagos_con_error_list`.
    - Duplicado en BD (documento en `documentos_ya_en_bd`) → a `pagos_con_error_list`.
    - Si `prestamo_id` vacío y cédula tiene exactamente un crédito activo (APROBADO/DESEMBOLSADO) → se asigna automáticamente; si tiene más de uno → a `pagos_con_error_list` ("Debe indicar el ID del préstamo").
    - Si pasa: se crea `Pago`, `db.add(p)`, se añade a `pagos_con_prestamo` si tiene `prestamo_id` y monto > 0.
    - Excepción en el `try` de inserción → se añade a `pagos_con_error_list`.
  - Tras el bucle: se hace `db.flush()`; se persisten todos los ítems de `pagos_con_error_list` en `PagoConError` (observaciones="validacion"); luego se aplica pago a cuotas para cada `p` en `pagos_con_prestamo` con `_aplicar_pago_a_cuotas_interno`; finalmente `db.commit()`.
- **Respuesta:** `message`, `registros_procesados`, `registros_con_error`, `cuotas_aplicadas`, `pagos_articulados`, `filas_omitidas`, `pagos_con_errores` (lista desde BD por `fila_origen`), `errores`, `errores_detalle` (truncados a 50/100), `errores_total`, `errores_detalle_total`, `errores_truncados`, `max_filas_recomendado`, `max_filas_permitido`.

### 3.3 Validadores backend (resumen)

| Dato | Regla | Acción si falla |
|------|--------|------------------|
| Archivo | .xlsx/.xls, ≤ 10 MB, ≤ 10.000 filas | 400 |
| Cédula | Opcional en parseo; si vacía junto con monto≤0 → omitir | → pagos_con_errores "Cedula vacia o monto <= 0" |
| Cédula formato | V/E/J + 6–11 dígitos (sin Z) para detectar formato | Fila no matchea formato D/A/B/C → cae en Formato C o se omite |
| Monto | Float, 0.01–999_999_999_999.99 | → pagos_con_error_list (FASE 1) |
| Documento | Cualquier formato; normalizado para comparar | Duplicado en archivo o en BD → pagos_con_error_list |
| Préstamo | 1 activo → auto; 0 → permitido; >1 sin ID → error | → pagos_con_error_list |

---

## 4. Flujo B: Previsualizar y editar

- **Hook:** `useExcelUploadPagos` (lectura con ExcelJS, validación con `pagoExcelValidation` + `excelValidation`).
- **Flujo:** Usuario suelta/selecciona Excel → se parsea en cliente → se muestra tabla editable con columnas Cédula, Fecha, Monto, Documento, Crédito (selector), Observaciones.
- **Validación en frontend:** `validatePagoField` (cedula: V/E/J 6–11 dígitos; fecha: DD/MM/YYYY; monto: >0 y ≤ MAX; numero_documento: duplicados en archivo/BD). Se usan `documentosEnArchivo`, `documentosDuplicadosBD` (si se cargan desde API), `cedulasInvalidas` (si se cargan).
- **Acciones:** Guardar una fila válida → `pagoService.guardarFilaEditable` (crea un pago); "Guardar todos" (solo filas válidas); "Revisar Pagos" (envío a `pagos_con_errores`); "Enviar solo duplicados" a Revisar Pagos.
- Los que cumplen validadores en front se envían a `POST /pagos/guardar-fila-editable`; los que el usuario envía a revisión se crean en `pagos_con_errores` vía API correspondiente.

---

## 5. Tablas y persistencia

| Tabla | Uso en Pagos Excel |
|-------|---------------------|
| **pagos** | Filas que pasan validadores (upload o guardar-fila-editable). `numero_documento` normalizado, único. |
| **pagos_con_errores** | Filas rechazadas en upload (FASE 1 y FASE 2) y filas enviadas a "Revisar Pagos" desde previsualizar. |
| **cuotas** / **cuota_pago** | Tras insertar en `pagos`, si tiene `prestamo_id` y monto > 0 se aplica pago a cuotas (Cascada). |

- Duplicados de documento: comparación siempre con **valor normalizado** (`normalize_documento` en `app/core/documento.py`); en BD se guarda y compara ese valor en `pagos.numero_documento`.

---

## 6. Seguridad y límites

- **Frontend (Subir y procesar):** `validateExcelFile`: extensión, MIME opcional, 10 MB, nombre sin caracteres peligrosos.
- **Backend:** 10 MB, .xlsx/.xls, 10.000 filas; timeout recomendado en proxy/servidor para `/pagos/upload` (p. ej. 120 s).
- **Autenticación:** endpoint con `get_current_user`; sesión BD con `get_db`.

---

## 7. Inconsistencias y riesgos observados

1. **Flujo "Subir y procesar":** Tras subir, si hay `registros_con_error > 0` no se muestra enlace ni aviso tipo "Ver Revisar Pagos" en el mismo modal; el usuario puede no saber que esos registros están en Revisar Pagos.
2. **Filas que no matchean ningún formato:** Se omiten sin sumar a `filas_omitidas` ni a `pagos_con_error_list`; no hay feedback "fila X no reconocida".
3. **Doble validación (Previsualizar):** Reglas de cédula/fecha/monto/documento en frontend pueden no ser idénticas al backend (p. ej. rangos de fecha, normalización de documento); si el usuario corrige solo en front, el backend puede seguir rechazando al guardar.
4. **Descarga Excel Revisar Pagos:** El botón "Descargar Excel en revisión pagos" (post-import Cobros) no elimina registros de `pagos_con_errores`; el botón "Descargar Excel" dentro de la vista Revisar Pagos sí los elimina (comportamiento desigual).
5. **Instrucciones en ExcelUploader:** El texto del modal "Subir y procesar" describe orden Cédula, ID Préstamo, Fecha, Monto, Documento (Formato C); el backend acepta varios formatos (D, A, B, C) por detección automática. Puede generar confusión si el usuario tiene columnas en otro orden pero válido.
6. **Truncado de errores:** Se devuelven hasta 50 mensajes y 100 detalles; el frontend no indica que puede descargar el Excel de Revisar Pagos para ver el 100% de los rechazados.

---

## 8. Mejoras propuestas

### Prioridad alta

1. **Enlace a Revisar Pagos tras "Subir y procesar"**  
   Cuando `registros_con_error > 0`, en el modal de resultado mostrar un botón o enlace "Ver X pagos en Revisar Pagos" que cierre el modal y lleve a la pestaña/listado de Revisar Pagos (o abra el filtro correspondiente).

2. **Unificar comportamiento al descargar Excel de pagos_con_errores**  
   Hacer que "Descargar Excel en revisión pagos" (post-import Cobros) también llame a `eliminarPorDescarga(ids)` tras descargar, igual que "Descargar Excel" en la vista Revisar Pagos, para que en ambos casos la lista se vacíe tras exportar (o documentar explícitamente por qué uno vacía y el otro no).

### Prioridad media

3. **Contabilizar y reportar filas no reconocidas**  
   En FASE 1, si una fila tiene datos pero no matchea D/A/B/C, sumarla a un contador `filas_no_reconocidas` y añadirla a `pagos_con_error_list` con mensaje "Formato de fila no reconocido. Use Cédula | Monto | Fecha | Documento (o los formatos soportados)." para que aparezcan en Revisar Pagos y en el resumen.

4. **Ajustar texto del modal "Subir y procesar"**  
   Indicar que se aceptan varios órdenes de columnas (D: Cédula|Monto|Fecha|Documento; A: Documento|Cédula|Fecha|Monto; B: Fecha|Cédula|Monto|Documento; C: Cédula|ID Préstamo|Fecha|Monto|Documento) y que el sistema detecta el formato automáticamente.

5. **Mensaje cuando hay errores truncados**  
   Si `errores_truncados === true`, además del texto actual, añadir: "Los registros con error están guardados en Revisar Pagos. Puede descargar el Excel desde allí para ver el listado completo."

### Prioridad baja

6. **Sincronizar normalización documento front/back**  
   Revisar que la función de normalización de número de documento en frontend (pagoExcelValidation / excelValidation) sea equivalente a `normalize_documento` del backend para evitar que una fila pase en previsualizar y falle al guardar por duplicado.

7. **Límite de filas en Previsualizar**  
   Si el hook/UI de Previsualizar no limita ya a 2.500/10.000 filas antes de parsear, añadir aviso o rechazo al superar el mismo límite que el backend para evitar timeouts o lentitud.

---

## 9. Referencia rápida de archivos

| Área | Archivo |
|------|---------|
| Menú y modales | `frontend/src/components/pagos/CargaMasivaMenu.tsx` |
| Subir y procesar (UI) | `frontend/src/components/pagos/ExcelUploader.tsx` |
| Previsualizar (UI) | `frontend/src/components/pagos/ExcelUploaderPagosUI.tsx` |
| Hook previsualizar | `frontend/src/hooks/useExcelUploadPagos.ts` |
| Validación pagos (front) | `frontend/src/utils/pagoExcelValidation.ts` |
| Validación archivo/datos | `frontend/src/utils/excelValidation.ts` |
| Servicio pagos | `frontend/src/services/pagoService.ts` (uploadExcel, guardarFilaEditable) |
| Upload backend | `backend/app/api/v1/endpoints/pagos.py` (upload_excel_pagos, ~406–851) |
| Normalización documento | `backend/app/core/documento.py` (normalize_documento) |
| Aplicar a cuotas | `backend/app/api/v1/endpoints/pagos.py` (_aplicar_pago_a_cuotas_interno) |

---

*Documento generado en el marco de la auditoría del flujo Pagos (Excel). Para más contexto ver AUDITORIA_PAGOS_PAGOS.md y AUDITORIA_MENU_AGREGAR_PAGO.md.*
