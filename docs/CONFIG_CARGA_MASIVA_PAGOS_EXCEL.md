# Configuración campo a campo: Carga masiva de pagos desde Excel

## Columnas del Excel (por índice y nombre)

El archivo se interpreta por **cabecera** (primera fila). Se buscan estas columnas por texto en el encabezado (sin importar mayúsculas/minúsculas):

| Campo lógico   | Palabras clave en cabecera                    | Uso |
|----------------|-----------------------------------------------|-----|
| **Cédula**     | `cedula`, `cédula`                            | Identificación del cliente. Se usa para buscar préstamos (créditos) y enviar al backend. |
| **Fecha pago** | `fecha`, `date`                               | Fecha del pago. Se normaliza a DD/MM/YYYY. |
| **Monto**      | `monto`, `amount`                             | Monto numérico del pago. |
| **Documento**  | `documento`, `numero_documento`, `nº documento`, `doc`, `referencia` | **Todos los formatos:** número largo (12+ dígitos), alfanumérico (BS./VZLA.REF4068, BINANCE/335552, BNCBS./483712), con símbolos. No se quitan símbolos. |
| **Crédito**    | `préstamo`, `prestamo`, `credito`, `crédito`  | Opcional. Si viene vacío o no existe columna, se intenta **asignar automáticamente** cuando la cédula tiene un solo crédito activo. |
| **Conciliación** | `conciliacion`, `conciliación`              | Sí/No. Por defecto Sí. |

Si no se encuentra una cabecera, se usan índices por defecto: 0=Cédula, 1=Fecha, 2=Monto, 3=Documento, 4=Crédito, 5=Conciliación.

### Ejemplo de Excel compatible (base típica)

Cabecera y datos como en el siguiente ejemplo son **compatibles** con la carga masiva:

| cedula    | monto_pagado | fecha_pago  | numero_documento  |
|-----------|--------------|-------------|-------------------|
| V23107415 | 48           | 05-11-2024  | 740087408305094   |
| V23107415 | 48           | 27-11-2024  | 740087403715582   |
| V23107415 | 48           | 06-12-2024  | 740087402462091   |

- **Cabeceras:** Se reconocen por coincidencia (sin importar mayúsculas): `cedula`, `monto_pagado` (contiene "monto"), `fecha_pago` (contiene "fecha"), `numero_documento` (contiene "documento").
- **Cédula:** Formato V/E/J/Z + 6–11 dígitos. Se usa para buscar créditos activos; si hay un solo crédito para esa cédula, se asigna a todas las filas.
- **numero_documento:** Números largos (15 dígitos, ej. 740087408305094) se aceptan tal cual. Si Excel los guarda como "número como texto" (triángulo verde), la lectura los convierte a string para no perder dígitos. No se quitan símbolos si hubiera €, $, Bs.
- **fecha_pago:** Formato DD-MM-YYYY (ej. 05-11-2024) se normaliza a DD/MM/YYYY y se valida año 2020–2030 y que no sea futura.
- **Duplicados:** Regla general: no se aceptan duplicados en documentos (ni en archivo ni en BD). Cada `numero_documento` debe ser único; si se repite, la fila se marca y no se acepta. Documentos numéricos de **10 a 25 dígitos** se aceptan sin problemas; la única restricción es no duplicado. Ver también *AUDITORIA_FORMATO_DOCUMENTO_740087408305094.md* (evitar regresión del borde rojo en la UI).

## Cómo se carga desde el Excel

1. **Lectura** (`readExcelToJSON`): primera hoja → array de celdas. **Número largo (12+ dígitos)** en cualquier columna se lee como texto (se intenta `cell.text` y luego string sin notación científica) para reconocer bien el número largo; resto de formatos (BS./REF, BINANCE/xxx, etc.) se aceptan tal cual.
2. **Validación de archivo** (`validateExcelFile`): extensión, tipo MIME.
3. **Validación de datos** (`validateExcelData`): al menos una fila de datos además de la cabecera.
4. **Detección de columnas**: se recorre la primera fila (cabecera) y se asigna cada campo al índice donde coincida alguna palabra clave.
5. **Por cada fila de datos**:
   - `cedula` = `row[cols.cedula]` (trim).
   - `fecha_pago` = `convertirFechaExcelPago(row[cols.fecha])`.
   - `monto_pagado` = parse float de `row[cols.monto]` (coma → punto).
   - `numero_documento` = `normalizarNumeroDocumento(row[cols.documento])` (solo normaliza número/científico; **no** quita símbolos).
   - `prestamo_id` = si la columna Crédito tiene valor numérico válido, se usa; si la celda parece Sí/No/1/0 se interpreta como Conciliación y no como ID de préstamo.
   - `conciliado` = Sí por defecto; No solo si el valor es "NO".
6. **Cédulas únicas para créditos**: se recogen **de ambas columnas** (Cédula y Documento) por fila: `cedulaParaLookup(cedula)`, `cedulaParaLookup(numero_documento)`, `cedulaLookupParaFila(cedula, numero_documento)`, y se mantienen solo las que tienen formato V/E/J/Z + 6–11 dígitos.
7. **Petición de préstamos**: `POST /api/v1/prestamos/cedula/batch` con `{ cedulas: uniqueCedulas }`.
8. **Asignación de Crédito**: si hay un solo crédito activo (APROBADO/DESEMBOLSADO) por cédula, se asigna a todas las filas de esa cédula; si en todo el archivo solo hay una cédula con créditos, se usa como **fallback** para todas las filas (así filas con documento numérico también reciben el mismo crédito).

## Flujo de código (resumen)

```
Excel (file) 
  → readExcelToJSON(buffer) 
  → jsonData[][] 
  → detectar columnas por cabecera 
  → por cada fila: construir PagoExcelRow (cedula, fecha_pago, monto_pagado, numero_documento, prestamo_id, conciliado)
  → setExcelData(processed), setShowPreview(true)
  → uniqueCedulas = recoger cédulas válidas de columna Cédula y columna Documento
  → getPrestamosByCedulasBatch(uniqueCedulas)
  → respuesta: { "V23107415": [{ id, estado }, ...] }
  → setPrestamosPorCedula(map), setExcelData(prev => prev.map(r => ... prestamo_id si 1 crédito + fallback))
```

Efecto adicional (por si el fetch en processExcelFile falla o tarda): cuando `showPreview` y `cedulasUnicas.length > 0`, se lanza otro `getPrestamosByCedulasBatch(cedulasUnicas)` y al resolver se hace el mismo `setPrestamosPorCedula` + `setExcelData` con asignación de crédito y fallback.

## Endpoints implicados

| Método | Ruta | Uso |
|--------|------|-----|
| POST   | `/api/v1/prestamos/cedula/batch` | Body: `{ "cedulas": ["V23107415", ...] }`. Respuesta: `{ "prestamos": { "V23107415": [{ id, estado, ... }], ... } }`. Claves = mismas cédulas enviadas. |
| GET    | `/api/v1/prestamos/cedula/{cedula}` | Usado por “Buscar” (un solo cedula). Respuesta: `{ "prestamos": [...], "total": N }`. |
| POST   | `/api/v1/pagos` | Guardar un pago (cedula_cliente, prestamo_id, fecha_pago, monto_pagado, numero_documento, etc.). |

## Reglas de negocio

- **Documento**: se acepta fielmente (con €, $, Bs, BINANCE/xxx, etc.). Solo se normaliza cuando el valor viene como número o notación científica para no perder dígitos.
- **Documentos duplicados**: no se aceptan; si el documento ya existe en BD o se repite en el archivo, se rechaza / se marca para revisión.
- **Crédito**: si la cédula tiene exactamente un crédito en estado APROBADO o DESEMBOLSADO, se asigna automáticamente; si en el archivo solo hay una cédula con créditos, se usa como fallback para todas las filas.

## Flujo 409 (duplicado) y Revisar Pagos

Al guardar una fila (individual o en lote):

1. El frontend hace **POST** a `/api/v1/pagos/` con el pago.
2. Si el backend responde **409** (documento ya existe en BD), el frontend:
   - Considera la fila como duplicado.
   - Hace **POST** a `/api/v1/pagos/con-errores/` con los mismos datos y `observaciones: 'duplicado'` para registrarlos en **Revisar Pagos**.
3. Por eso en la consola se ve la secuencia: **POST pagos → 409**, luego **POST con-errores → 201**, repetida por cada fila duplicada.

Es el comportamiento esperado: no se puede saber que un documento está duplicado sin intentar crear el pago (o sin un endpoint previo de comprobación). Para reducir peticiones futuras se podría añadir un endpoint batch que compruebe qué documentos existen y otro batch para crear en con-errores.

## Aviso CSS "Juego de reglas ignoradas debido a un mal selector"

El mensaje suele aparecer en el CSS compilado (p. ej. `index-*.css`) y puede venir de:

- **Tailwind** (variantes arbitrarias o selectores generados).
- **Alguna dependencia** que incluye estilos con selectores no soportados en el navegador.

Para localizar el selector problemático: hacer build (`npm run build`), abrir el `.css` generado en `dist/assets/` y revisar alrededor del carácter indicado (p. ej. columna 64116). En el código propio ya se evitan selectores como `after:content-['']` (ver comentario en `frontend/src/index.css` sobre el toggle switch). Si el selector está en código de una librería, el aviso puede ignorarse o actualizar la dependencia.
