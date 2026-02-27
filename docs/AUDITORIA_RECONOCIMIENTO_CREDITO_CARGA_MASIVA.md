# Auditoría: Reconocimiento automático de crédito en Carga masiva de pagos

## Objetivo
Garantizar que el crédito se asigne automáticamente cuando la cédula tiene un solo préstamo activo, y que el formato del documento (con o sin "comillas" en Excel) no afecte al reconocimiento.

## Flujo actual

1. **Excel** → columnas: Cédula, Fecha pago, Monto, **Documento**, Crédito (opcional), Conciliación.
2. **Frontend** lee filas, normaliza Documento (equivalente a comillas) y obtiene préstamos por cédula.
3. Si la cédula tiene **un solo** préstamo activo (APROBADO/DESEMBOLSADO), se asigna ese `prestamo_id` a la fila (campo Crédito).
4. Al guardar, se envía `cedula_cliente`, `prestamo_id`, `numero_documento`, etc. al backend.

## Causas por las que el crédito no se reconocía

### 1. Cédulas usadas para buscar préstamos
- **Problema:** Si en el Excel la columna "Cédula" contenía por error un **número de documento** (solo dígitos, ej. 740087464410397), se llamaba a `getPrestamosByCedula("740087464410397")`. El backend no tiene cliente con esa "cédula", devuelve `[]` y no se asigna crédito.
- **Solución:** En el frontend, `cedulasUnicas` solo incluye valores con **formato de cédula**: `V/E/J/Z` + 6–11 dígitos. Así no se usa nunca un número de documento como cédula para buscar préstamos.
- **Archivo:** `frontend/src/hooks/useExcelUploadPagos.ts` (filtro `looksLikeCedula` en `cedulasUnicas`).

### 2. Documento sin "comillas" (notación científica)
- **Problema:** En Excel, números largos sin comillas se guardan como número y pueden leerse en notación científica (ej. 7.4E+14). Eso no cambia la cédula, pero si en algún flujo se usaba el documento para comparar o buscar, podía fallar la coincidencia.
- **Solución:**
  - **Frontend:** `normalizarNumeroDocumento()` en `pagoExcelValidation.ts` convierte siempre a string de dígitos completos (número, notación científica o string).
  - **Backend:** `_normalizar_numero_documento()` en `pagos.py` normaliza al crear/actualizar pago y al comprobar duplicados, de modo que el valor almacenado y la comparación usen el mismo formato (equivalente a "comillas" en Excel).
- **Archivos:** `frontend/src/utils/pagoExcelValidation.ts`, `backend/app/api/v1/endpoints/pagos.py`.

### 3. Coincidencia cédula (mayúsculas / guiones)
- Ya estaba cubierto: búsqueda por cédula con variantes (trim, sin guión, toUpperCase, toLowerCase) en frontend y backend (`_normalizar_cedula_para_busqueda`).

## Cambios realizados (resumen)

| Ámbito    | Cambio |
|----------|--------|
| Frontend | `cedulasUnicas` solo incluye strings que cumplen formato cédula (V/E/J/Z + 6–11 dígitos). |
| Frontend | Lectura de cédula del Excel siempre como string: `String(row[cols.cedula]).trim()`. |
| Frontend | Documento siempre normalizado con `normalizarNumeroDocumento()` al leer cada fila. |
| Backend  | `_normalizar_numero_documento()`: convierte notación científica y deja solo dígitos. |
| Backend  | Crear/actualizar pago y comprobación de duplicados usan valor normalizado de documento. |

## Verificación

- Subir Excel con **Cédula** correcta (ej. V23107415) y **Documento** con números largos **sin** comillas en Excel.
- Comprobar que la columna **Crédito** se rellena con "Crédito #N" cuando ese cliente tiene un solo préstamo activo.
- Comprobar que al guardar, el pago queda con `prestamo_id` correcto y `numero_documento` guardado como string de dígitos completos (sin notación científica).
