# Auditoría: Formato de documento 740087408305094 (y números largos)

## Objetivo
Asegurar que el documento en formato **solo números largos** (ej. `740087408305094`) se acepte en todo el flujo y que no vuelva el error de "no reconocer" este formato.

## Caso de referencia
- **Valor en Excel:** celda con número `740087408305094` (sin comillas; Excel puede mostrarlo como `7.4E+14`).
- **Comportamiento esperado:** se reconoce, se muestra y se guarda como `"740087408305094"` (string de 15 dígitos). No notación científica, no pérdida de dígitos.

---

## Puntos de control (no tocar sin revisar esta auditoría)

### 1. Lectura Excel (frontend)
| Archivo | Qué hace |
|---------|----------|
| `frontend/src/types/exceljs.ts` | En `readExcelToJSON`, **cualquier celda** con valor numérico y `Math.abs(val) >= 1e14` se convierte a string de dígitos completos (`Math.round(val).toString()` o `BigInt(...).toString()`). Así el valor nunca sale del lector en notación científica. |

**Regla:** No quitar ni relajar la condición `Math.abs(val) >= 1e14` para números. Cualquier número largo (14+ dígitos) debe salir del lector como string de dígitos.

### 2. Normalización al procesar filas (frontend)
| Archivo | Qué hace |
|---------|----------|
| `frontend/src/utils/pagoExcelValidation.ts` → `normalizarNumeroDocumento()` | Acepta `unknown`; si es `number` y `>= 1e14` devuelve string de dígitos (sin notación científica). Si es string: quita €/$/Bs al inicio/final; si es solo dígitos devuelve tal cual; si es notación científica (`\d+\.?\d*[eE][+-]?\d+`) la expande a dígitos. |
| `frontend/src/hooks/useExcelUploadPagos.ts` | Al leer cada fila: `numeroDoc = normalizarNumeroDocumento(row[cols.documento])`. Al guardar (individual o batch): `numeroDoc = normalizarNumeroDocumento(row.numero_documento)`. |

**Regla:** Toda lectura o envío de `numero_documento` debe pasar por `normalizarNumeroDocumento`. No usar `row[cols.documento]` o `row.numero_documento` sin normalizar para guardar o validar.

### 3. Validación (frontend)
| Archivo | Qué hace |
|---------|----------|
| `frontend/src/utils/pagoExcelValidation.ts` → `validatePagoField('numero_documento', value, ...)` | Usa `docNorm = normalizarNumeroDocumento(value)` antes de comprobar duplicados en `documentosExistentes` / `documentosEnArchivo`. |

**Regla:** En validación de `numero_documento` siempre usar el valor normalizado para comparaciones y duplicados.

### 4. Backend (API pagos)
| Archivo | Qué hace |
|---------|----------|
| `backend/app/api/v1/endpoints/pagos.py` → `_normalizar_numero_documento()` | Quita símbolos €, $, Bs al inicio/final; si es notación científica la convierte a `str(int(round(float(s))))`; si es solo dígitos devuelve tal cual. |
| `pagos.py` → `crear_pago` | `num_doc = _normalizar_numero_documento(payload.numero_documento)`; se usa para duplicados y para guardar. |
| `pagos.py` → `actualizar_pago` | Normaliza `data["numero_documento"]` antes de duplicados y al asignar al modelo. |
| `pagos.py` → `_numero_documento_ya_existe()` | Normaliza el argumento antes de comparar con la BD. |

**Regla:** Crear, actualizar y comprobar duplicados deben usar siempre `_normalizar_numero_documento`; no comparar ni guardar el valor crudo.

### 5. Formulario registro de pago (frontend)
| Archivo | Qué hace |
|---------|----------|
| `frontend/src/components/pagos/RegistrarPagoForm.tsx` | Normaliza `numero_documento` antes de enviar (incluye manejo de notación científica). |
| `frontend/src/components/reportes/TablaAmortizacionCompleta.tsx` | Muestra y edita `numero_documento`; al guardar usa el valor del formulario. |

**Regla:** Cualquier envío de `numero_documento` al API debe usar valor normalizado (frontend y/o backend).

---

## Formatos que deben aceptarse (resumen)
- `740087408305094` (número o string de dígitos)
- `7.4E+14` / `7.40087408305094e+14` (notación científica)
- `740087408305094€` o `€740087408305094` (con símbolo de moneda)
- `VE/14514848`, `BNC/101754120`, etc. (otros formatos; se almacenan tal cual salvo limpieza de €/$/Bs)

---

## Comprobación rápida (evitar regresiones)
1. Subir Excel con columna Documento que tenga **solo el número** `740087408305094` (sin comillas en la celda).
2. Comprobar en previsualización: el campo Documento debe mostrar `740087408305094` (15 dígitos, sin `E+14`).
3. Guardar el pago y en BD (o en listado): `numero_documento` debe ser `740087408305094`.
4. No debe aparecer notación científica en UI ni en duplicados.

Si en algún paso el valor aparece en notación científica o con menos dígitos, revisar el punto de control correspondiente en esta auditoría.

---

## Regla de negocio: 10–25 dígitos y no duplicados (evitar regresión del borde rojo)

### Regla general
- **No se aceptan duplicados en documentos:** ni en el archivo ni en el sistema (BD). Es la única restricción de contenido para Nº documento.
- **Documentos numéricos de 10 a 25 dígitos:** se aceptan sin problemas. No se valida “formato”; solo se rechaza por duplicado.

### Por qué volvía el “borde rojo” en la UI de carga masiva
Los números de 15 dígitos (p. ej. `740087427577222`) se marcaban en rojo cuando:
1. **Clave de duplicados inconsistente:** se añadía la cadena vacía `''` al set `documentosEnArchivo` o la normalización al añadir no coincidía con la usada al validar (número vs string, notación científica).
2. **Columna interpretada como Cédula:** si la primera columna del Excel tenía los números largos y no se reconocía cabecera “Documento”, se leían como cédula y la validación de cédula (V/E/J/Z + 6–11 dígitos) fallaba.

### Puntos de control para no regresar

| Dónde | Qué debe cumplirse |
|-------|---------------------|
| `pagoExcelValidation.ts` | `validatePagoField('numero_documento')`: documentos solo numéricos 10–25 dígitos (`/^\d{10,25}$/`) solo se marcan inválidos si están en `documentosExistentes` o `documentosEnArchivo`. No añadir `''` al set. Comentario en cabecera del módulo: “no añadir '' a documentosEnArchivo; misma normalización al añadir y al validar”. |
| `useExcelUploadPagos.ts` (processExcelFile) | Guardar `numero_documento` en cada fila como **string normalizado** (`numeroDocStr`); solo añadir al set con `if (numeroDocStr) documentosEnArchivo.add(numeroDocStr)`. Intercambio: si la columna “Cédula” trae número largo (`looksLikeDocumentNotCedula(cedula)`) y “Documento” está vacío o es una cédula, usar ese valor como documento y la otra celda como cédula. |
| `useExcelUploadPagos.ts` (updateCellValue) | Al revalidar al editar una celda, construir `documentosEnArchivo` solo con documentos **no vacíos** de las demás filas: `if (docNorm) documentosEnArchivo.add(docNorm)`. |

### Constantes y referencias en código
- `DOCUMENTO_DIGITS_MIN = 10`, `DOCUMENTO_DIGITS_MAX = 25` en `pagoExcelValidation.ts` (documentación del rango aceptado).
- Backend: “Documentos numéricos de 10 a 25 dígitos se aceptan sin problemas” en docstring de `pagos.py`; mensajes 409 con “Regla general: no se aceptan duplicados en documentos”.

### Comprobación rápida (evitar regresión del borde rojo)
1. Subir Excel con varias filas cuyos Nº documento sean **solo números de 15 dígitos** (todos distintos).
2. En la previsualización, los campos **Documento** no deben tener borde rojo (solo rojo si hay duplicado en archivo o documento ya existente en BD).
3. Si la primera columna del Excel son esos números y no hay cabecera “Documento”, deben seguir sin borde rojo en la columna Documento (intercambio cédula/documento por contenido).
