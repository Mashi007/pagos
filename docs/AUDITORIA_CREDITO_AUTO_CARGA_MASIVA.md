# Auditoría: Crédito no se carga automáticamente en previsualización Excel

## Problema

En la previsualización de carga masiva de pagos (Excel), la columna **Crédito** queda vacía aunque exista un único crédito activo para la cédula de la fila. El usuario debe seleccionar manualmente "Crédito #1" en el desplegable.

## Flujo esperado

1. Usuario sube Excel con columnas: Cédula, Fecha pago, Monto, Documento, (opcional) Crédito, Conciliación.
2. Se muestra la tabla de previsualización con las filas leídas.
3. Para cada cédula única se consultan los préstamos activos (APROBADO, DESEMBOLSADO).
4. Si una cédula tiene **exactamente un** crédito activo y la fila no tiene crédito elegido, se **asigna automáticamente** ese crédito a la fila (columna Crédito rellenada).

## Causas identificadas

### 1. Delay de 350 ms antes de pedir préstamos

- El `useEffect` que dispara la petición de préstamos usaba `setTimeout(..., 350)`.
- Si el efecto se volvía a ejecutar (p. ej. re-renders o Strict Mode), el timer podía cancelarse y la petición no se llegaba a hacer, dejando Crédito vacío.

**Solución:** Delay cambiado a **0 ms** para que la petición se programe en el siguiente tick en cuanto haya `showPreview` y `cedulasUnicas`, sin esperar 350 ms.

### 2. Dependencia solo del efecto (timing / estado)

- La asignación de crédito dependía solo del `useEffect` que reacciona a `showPreview` y `cedulasUnicas.join(',')`.
- Cualquier condición de carrera o orden de actualización de estado podía hacer que el usuario viera la tabla antes de que llegara la respuesta de préstamos y se aplicara la asignación.

**Solución:** Asignación de crédito **también** dentro de `processExcelFile`, justo después de `setExcelData(processed)` y `setShowPreview(true)`:
- Se calculan las cédulas únicas del `processed` recién creado.
- Se llama a `getPrestamosByCedula` o `getPrestamosByCedulasBatch` con esas cédulas.
- Al resolver la promesa se hace `setPrestamosPorCedula(map)` y `setExcelData(prev => prev.map(...))` para rellenar `prestamo_id` cuando haya un solo crédito activo por cédula.
- Así la asignación ocurre en el mismo flujo del procesamiento del archivo, sin depender solo del efecto.

### 3. Criterio de “vacío” para `prestamo_id`

- Si en el Excel la columna de crédito venía como `0` o se interpretaba como `0`, no se consideraba “vacío” y no se autoasignaba el único crédito.

**Solución:** Se considera vacío también cuando `prestamo_id === 0` en la función `prestamoIdVacio` y en el cálculo del valor del Select en la UI.

### 4. Lookup de cédula en la UI distinto al del hook

- En la tabla se usaba `row.cedula` para buscar en `prestamosPorCedula`.
- El mapa se rellena con la clave que devuelve `cedulaLookupParaFila(cedula, numero_documento)` (p. ej. "AUL V23107415" → "V23107415").
- Si el Excel traía prefijo o la cédula en otra columna, la clave no coincidía y la UI no encontraba créditos.

**Solución:** En `ExcelUploaderPagosUI` se usa **siempre** `cedulaLookupParaFila(row.cedula, row.numero_documento)` para:
- Obtener la lista de créditos de la fila.
- Calcular el valor del Select cuando hay un solo crédito y ninguno elegido.
- Botón “Buscar” y `onBlur` de cédula.

## Cambios realizados (resumen)

| Archivo | Cambio |
|--------|--------|
| `frontend/src/hooks/useExcelUploadPagos.ts` | Delay del efecto de 350 ms → **0 ms**. |
| `frontend/src/hooks/useExcelUploadPagos.ts` | Dentro de `processExcelFile`, tras mostrar preview: petición de préstamos por cédulas únicas del `processed` y, al resolver, `setPrestamosPorCedula` + `setExcelData` con asignación de `prestamo_id` cuando hay 1 crédito activo. |
| `frontend/src/hooks/useExcelUploadPagos.ts` | `prestamoIdVacio` considera `v === 0` como vacío. |
| `frontend/src/components/pagos/ExcelUploaderPagosUI.tsx` | Lookup por `cedulaLookupParaFila(row.cedula, row.numero_documento)` y valor del Select tratando `prestamo_id === 0` como “no elegido” para auto-seleccionar el único crédito. |

## Comprobaciones recomendadas

1. **Backend:** Que `GET /api/v1/prestamos/cedula/{cedula}` y `POST /api/v1/prestamos/cedula/batch` devuelvan préstamos en estado APROBADO o DESEMBOLSADO para la cédula (normalizada sin guiones, mayúsculas).
2. **Datos:** Que la cédula del Excel corresponda a un cliente con al menos un préstamo en esos estados; si todos están PAGADO/CANCELADO, no se mostrará crédito para auto-asignar.
3. **Red:** Si la petición falla (red o 4xx/5xx), no se asigna crédito; revisar consola y pestaña Red por errores.

## Referencia de código

- Cédulas únicas: `cedulasUnicas` (useMemo desde `excelData` con `cedulaLookupParaFila` y `looksLikeCedula`).
- Estados considerados activos: `ESTADOS_PRESTAMO_ACTIVO = ['APROBADO', 'DESEMBOLSADO']`.
- Asignación en dos sitios: (1) en el `.then()` del efecto (timer 0 ms), (2) en el `.then()` de la petición lanzada desde `processExcelFile`.
