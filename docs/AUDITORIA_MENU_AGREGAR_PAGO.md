# Auditoría: funciones del menú "Agregar pago" (https://rapicredit.onrender.com/pagos/pagos)

Referencia para preguntas específicas. Cada función del dropdown está auditada: flujo, APIs, backend y archivos clave.

---

## Ubicación del menú

- **Componente:** `frontend/src/components/pagos/PagosList.tsx`
- **Estado:** `agregarPagoOpen` controla el `Popover`; al abrir se refresca `gmailStatus` con `pagoService.getGmailStatus()`.
- **Texto del botón:** "+ Agregar pago" (Plus + ChevronDown).

---

## 1. Estado de sincronización (línea informativa arriba del menú)

**Qué muestra:** "Última sync: 13/3, 2:52 AM – 1 correos, 3 archivos" (o "Última sync Gmail falló" / "Sin sync Gmail aún").

**Origen de datos:**
- Estado: `gmailStatus` (hook `useGmailPipeline` + `pagoService.getGmailStatus()`).
- Al abrir el popover se llama de nuevo a `getGmailStatus()` (useEffect con `agregarPagoOpen`).

**API:** `GET /api/v1/pagos/gmail/status`

**Backend:** `backend/app/api/v1/endpoints/pagos_gmail.py` — `status()` (líneas ~140–157). Devuelve: `last_run`, `last_status`, `last_emails`, `last_files`, `last_error`, `next_run_approx`, `latest_data_date`. Datos desde tabla `PagosGmailSync` (último registro por `started_at`).

**Formato de fecha:** `frontend/src/utils/index.ts` — `formatLastSyncDate(isoString)`: "Hoy, h:mm a" | "Ayer, h:mm a" | "d/M, h:mm a" (locale es).

---

## 2. Registrar un pago (Formulario)

**Acción:** Abre el modal de registro/edición de un pago manual.

**Flujo en UI:**
- Click → `setShowRegistrarPago(true)` y `setAgregarPagoOpen(false)`.
- Se renderiza `RegistrarPagoForm` con `onClose`, `onSuccess`, `pagoInicial` (opcional), `pagoId` (edición), `modoGuardarYProcesar`, `esPagoConError`.

**Componente:** `frontend/src/components/pagos/RegistrarPagoForm.tsx`

**Validaciones (frontend):**
- Cédula requerida; crédito debe ser uno de la lista por cédula (usePrestamosByCedula).
- Cédula del pago debe coincidir con la del préstamo seleccionado.
- Monto > 0 y ≤ 1.000.000; número de documento requerido; normalización de notación científica (7.4e+14 → entero).
- Fecha de pago no futura.

**APIs usadas:**
- Crear: `POST /api/v1/pagos` (body: PagoCreate).
- Actualizar (pago normal): `PUT /api/v1/pagos/{id}`.
- Actualizar (pago con error): `PUT /api/v1/pagos/con-errores/{id}`.
- Lectura: `GET /api/v1/prestamos/cedula/{cedula}` (hook usePrestamosByCedula), `GET /api/v1/prestamos/{id}` (usePrestamo).

**Backend crear/actualizar:** `backend/app/api/v1/endpoints/pagos.py` — `crear_pago`, `actualizar_pago`. Validación de monto con `_validar_monto`, duplicados por `numero_documento` (409), existencia de préstamo y cliente; si `conciliado=true` y hay `prestamo_id` se aplica pago a cuotas (FIFO).

---

## 3. Pagos (Excel)

**Acción:** Carga masiva desde archivo Excel (previsualizar, editar celdas, guardar por fila o en lote, enviar filas con error a Revisar Pagos).

**Flujo en UI:**
- Click → `setShowCargaMasivaPagos(true)` y cierre del popover.
- Se renderiza `ExcelUploaderPagosUI` (fullscreen modal).

**Componente:** `frontend/src/components/pagos/ExcelUploaderPagosUI.tsx`  
**Lógica/hook:** `frontend/src/hooks/useExcelUploadPagos.ts`

**Formatos de columnas soportados (comentario en ExcelUploaderPagosUI):**
- D) Cédula | Monto | Fecha | Documento (recomendado).
- A) Documento | Cédula | Fecha | Monto.
- B) Fecha | Cédula | Monto | Documento.
- C) Cédula | ID Préstamo | Fecha | Monto | Documento.
- Opcionales: ID Préstamo, Conciliación (Sí/No). Máx. 10 MB.

**APIs usadas:**
- Validación batch: `POST /api/v1/pagos/validar-filas-batch` (cédulas y documentos).
- Guardar una fila (preview corregida): `POST /api/v1/pagos/guardar-fila-editable`.
- Crear un pago: `POST /api/v1/pagos`.
- Crear pago con error (Revisar Pagos): `POST /api/v1/pagos/con-errores`.
- Guardar todos válidos: `POST /api/v1/pagos/batch` (máx. 500 ítems).

**Backend:** `pagos.py`: `validar_filas_batch`, `guardar_fila_editable`, `crear_pago`, `crear_pagos_batch`; `pagos_con_errores.py`: `crear_pago_con_error`. Reglas: documento único en sistema, cédula con crédito activo (APROBADO/DESEMBOLSADO), monto validado; duplicados/errores → `pagos_con_errores`.

**Cierre y éxito:** `onSuccess` invalida/refetch queries `pagos`, `pagos-kpis`, `pagos-ultimos` y muestra toast. Opción de ir a "Revisar Pagos" (`/pagos?revisar=1`).

---

## 4. Conciliación (Carga)

**Acción:** Subir un Excel de conciliación (2 columnas: Fecha de Depósito, Número de Documento) para marcar pagos existentes como conciliados y aplicar a cuotas.

**Flujo en UI:**
- Click → `setShowConciliacion(true)` y cierre del popover.
- Se renderiza `ConciliacionExcelUploader`.

**Componente:** `frontend/src/components/pagos/ConciliacionExcelUploader.tsx`

**Validación de archivo:** Antes de aceptar el file se usa `validateExcelFile` desde `../../utils/excelValidation` (tipo, tamaño, extensiones).

**Formato esperado:** 2 columnas — Fecha de Depósito (YYYY-MM-DD o DD/MM/YYYY), Número de Documento (coincidencia exacta con pago existente). El backend normaliza documento con `normalize_documento`.

**API:** `POST /api/v1/pagos/conciliacion/upload` (multipart, campo `file`).  
**Servicio frontend:** `pagoService.uploadConciliacion(file)`.

**Backend:** `backend/app/api/v1/endpoints/pagos.py` — `upload_conciliacion` (líneas ~1194–1268). Lee Excel (openpyxl), por cada fila busca pago por `numero_documento` normalizado; si existe marca `conciliado=True`, `fecha_conciliacion=ahora` y, si tiene `prestamo_id` y monto > 0, aplica a cuotas con `_aplicar_pago_a_cuotas_interno`. Respuesta: `pagos_conciliados`, `cuotas_aplicadas`, `pagos_no_encontrados`, `documentos_no_encontrados`, `errores`, `errores_detalle`.

**onSuccess:** Invalida listado de pagos y cierra modal; toasts según resultado (éxito, no encontrados, errores).

---

## 5. Generar Excel desde Gmail

**Acción:** Ejecutar el pipeline Gmail (correos no leídos con adjuntos → extracción → datos en Sheets/BD) y, al terminar, permitir descargar Excel o confirmar/borrar día.

**Flujo en UI:**
- Click → `handleGenerarExcelDesdeGmail()`: cierra popover y llama `runGmail()` del hook.
- Hook: `pagoService.runGmailNow()` → polling a `getGmailStatus()` cada 5 s hasta `last_status` ∈ { success, error } o timeout (25 min).
- Si éxito (o datos previos): se abre `ConfirmarBorrarDiaDialog` (`showConfirmarBorrar`), donde el usuario puede descargar Excel y elegir si borrar o no los datos del día.

**Hook:** `frontend/src/hooks/useGmailPipeline.ts`  
**Servicio:** `pagoService.runGmailNow(force)`, `pagoService.getGmailStatus()`, `pagoService.downloadGmailExcel(fecha?)`, `pagoService.confirmarDiaGmail(confirmado, fecha?)`.

**APIs:**
- `POST /api/v1/pagos/gmail/run-now?force=true` — inicia pipeline en background; responde de inmediato con `sync_id`, `status: "running"`.
- `GET /api/v1/pagos/gmail/status` — última ejecución, conteos, `latest_data_date`.
- `GET /api/v1/pagos/gmail/download-excel?fecha=YYYY-MM-DD` (opcional) — Excel del día (o acumulado según implementación).
- `POST /api/v1/pagos/gmail/confirmar-dia` — body `{ confirmado, fecha? }`; si `confirmado=true` borra datos del día (o todo si no se envía fecha).

**Backend:** `backend/app/api/v1/endpoints/pagos_gmail.py`.  
- `run_now`: comprueba que no haya otra sync en curso (409), opcionalmente intervalo mínimo (429), credenciales OAuth (503); crea `PagosGmailSync` en "running", lanza `_run_pipeline_background(sync_id)`.  
- Pipeline real: `app/services/pagos_gmail/pipeline.py` (Gmail → Drive → Gemini → Sheets / BD).  
- `status`: último `PagosGmailSync`, `latest_data_date` desde ítems.  
- `download-excel`: genera Excel desde `PagosGmailSyncItem` (por fecha o acumulado).  
- `confirmar-dia`: borra ítems por `sheet_name` (fecha) o todos.

**Diálogo post-sync:** `ConfirmarBorrarDiaDialog` en PagosList; al elegir opción se llama `downloadGmailExcel` y luego `confirmarDiaGmail(borrar, fecha)`.

---

## 6. Importar reportados aprobados (Cobros)

**Acción:** Importar a la tabla `pagos` (y a Revisar Pagos los que no cumplan reglas) todos los pagos reportados del módulo Cobros que estén en estado "aprobado".

**Flujo en UI:**
- Click → `handleImportarDesdeCobros()`: cierra popover, `setIsImportingCobros(true)`, llama `pagoService.importarDesdeCobros()`.
- Respuesta: `registros_procesados`, `registros_con_error`, `mensaje`; se guarda en `lastImportCobrosResult` y se muestran toasts. Si hay errores se sugiere "Descargar Excel en revisión pagos".
- Invalidación de queries: `pagos`, `pagos-kpis`, `pagos-con-errores`.

**API:** `POST /api/v1/pagos/importar-desde-cobros` (sin body).

**Backend:** `backend/app/api/v1/endpoints/pagos.py` — `importar_reportados_aprobados_a_pagos` (líneas ~811–1017).  
- Origen: tabla `PagoReportado` con `estado == "aprobado"`.  
- Por cada registro: normaliza cédula y documento; rechaza si documento ya existe en `pagos` o duplicado en el lote; busca cliente por cédula; exige 1 crédito activo (APROBADO/DESEMBOLSADO); si hay 0 o >1 préstamos activos va a `PagoConError` con observaciones "Cobros (reportados aprobados)". Los que cumplen se insertan en `pagos` y se aplica a cuotas si aplica.  
- Respuesta: `registros_procesados`, `registros_con_error`, `errores_detalle`, `ids_pagos_con_errores`, `cuotas_aplicadas`, `mensaje`.

---

## Resumen de endpoints por función

| Función                         | Método y ruta                                    | Auth |
|---------------------------------|--------------------------------------------------|------|
| Estado sync                     | GET /api/v1/pagos/gmail/status                   | Sí   |
| Registrar un pago               | POST /api/v1/pagos, PUT /api/v1/pagos/{id}       | Sí   |
| Pagos (Excel)                   | POST validar-filas-batch, guardar-fila-editable, /pagos, /pagos/batch, /pagos/con-errores | Sí   |
| Conciliación                    | POST /api/v1/pagos/conciliacion/upload            | Sí   |
| Generar Excel desde Gmail       | POST run-now, GET status, GET download-excel, POST confirmar-dia | Sí   |
| Importar reportados (Cobros)    | POST /api/v1/pagos/importar-desde-cobros         | Sí   |

---

## Archivos clave (referencia rápida)

| Función        | Frontend principal                          | Backend principal                    |
|----------------|---------------------------------------------|--------------------------------------|
| Estado sync    | PagosList.tsx, useGmailPipeline.ts, utils/index.ts (formatLastSyncDate) | pagos_gmail.py (status)              |
| Registrar pago | RegistrarPagoForm.tsx, PagosList.tsx        | pagos.py (crear_pago, actualizar_pago) |
| Pagos Excel    | ExcelUploaderPagosUI.tsx, useExcelUploadPagos.ts | pagos.py, pagos_con_errores.py       |
| Conciliación   | ConciliacionExcelUploader.tsx               | pagos.py (upload_conciliacion)       |
| Gmail          | useGmailPipeline.ts, PagosList.tsx, ConfirmarBorrarDiaDialog | pagos_gmail.py, services/pagos_gmail/pipeline.py |
| Importar Cobros| PagosList.tsx (handleImportarDesdeCobros)   | pagos.py (importar_reportados_aprobados_a_pagos) |

Con esta referencia se puede responder con precisión preguntas concretas sobre cualquiera de las funciones del menú "Agregar pago".
