# Análisis: problema de carga masiva en cuanto a formato — RESUELTO

**Fecha:** 2026-02-27  
**Objetivo:** Confirmar si el problema de carga masiva de pagos quedó resuelto en cuanto a **formatos** (documento, crédito, duplicados, errores 500).

---

## 1. Documentación existente revisada

| Documento | Contenido relevante |
|-----------|----------------------|
| **COHERENCIA_BACK_FRONT_CARGA_MASIVA.md** | Rutas batch y POST pago alineadas; body PagoCreate; duplicados 409; número de documento sin quitar símbolos. |
| **CONFIG_CARGA_MASIVA_PAGOS_EXCEL.md** | Columnas Excel (Cédula, Fecha, Monto, **Documento**, Crédito, Conciliación); **todos los formatos** de documento: número largo, BS./, BINANCE/, BNCBS./, etc.; lectura número largo como texto; normalización sin quitar símbolos. |
| **AUDITORIA_FORMATO_DOCUMENTO_740087408305094.md** | Número largo (15 dígitos) aceptado; notación científica convertida a dígitos; puntos de control en lectura Excel, normalización front/back, validación y duplicados. |
| **AUDITORIA_RECONOCIMIENTO_CREDITO_CARGA_MASIVA.md** | Crédito automático cuando 1 préstamo activo por cédula; `cedulasUnicas` solo con formato cédula (V/E/J + 6–11 dígitos); no usar número de documento como cédula. |

---

## 2. Problemas de formato que existían y cómo se resolvieron

### 2.1 Formato del número de documento

| Problema | Resolución en código |
|----------|----------------------|
| Excel guarda número largo como número → se lee en notación científica (7.4E+14) y se pierden dígitos. | **Frontend:** `exceljs.ts`: cualquier celda con `\|val\| >= 1e11` se lee como string de dígitos completos. `pagoExcelValidation.ts`: `normalizarNumeroDocumento()` trata números `>= 1e11` como “número largo” y devuelve string. |
| Documentos con símbolos o varios valores concatenados (ej. `740087408451411/bs.bna-ref926361`) superaban 100 caracteres en BD → **500**. | **Backend:** `pagos.py`: `_truncar_numero_documento()` trunca a 100 caracteres; se usa en `crear_pago`, `actualizar_pago` y carga masiva CSV. Así no se excede `String(100)` y no hay 500 por longitud. |
| Aceptar todos los formatos (número largo, BS./, BINANCE/, VE/, etc.) sin rechazarlos. | **Frontend y backend:** no se quitan símbolos; solo se normaliza notación científica. Documentos alfanuméricos o con `/` se envían y guardan (truncados a 100 en backend). |

**Conclusión:** El formato de **documento** en carga masiva está resuelto: número largo, notación científica y formatos alfanuméricos se aceptan; documentos largos se truncan en backend y se evita el 500.

---

### 2.2 Crédito (prestamo_id) y confusión con número de documento

| Problema | Resolución en código |
|----------|----------------------|
| En el Excel o en la UI se elegía por error un **número de documento** (ej. 740087408451411) como “crédito”. Ese valor se enviaba como `prestamo_id`. En PostgreSQL `INTEGER` solo admite hasta 2 147 483 647 → **500 "integer out of range"**. | **Backend:** En `schemas/pago.py`, `PagoCreate` y `PagoUpdate` tienen validador `prestamo_id_en_rango`: solo se acepta `prestamo_id` entre 1 y 2 147 483 647. Si se envía un número de documento como crédito → **422** con mensaje claro (“prestamo_id debe estar entre 1 y …; si el valor parece un número de documento, elija el crédito correcto”). |
| Carga masiva CSV (backend): columna “préstamo” con número de documento → mismo error 500. | **Backend:** En `pagos.py`, al parsear la columna de préstamo del CSV, si el entero es &lt; 1 o &gt; 2 147 483 647 se trata como “sin crédito” (`prestamo_id = None`). |

**Conclusión:** El problema de **formato de crédito** (número de documento enviado como `prestamo_id`) está resuelto: ya no hay 500 por “integer out of range”; se devuelve 422 o se ignora el valor en CSV.

---

### 2.3 Duplicados y flujo de revisión

| Aspecto | Estado |
|---------|--------|
| Documento duplicado en BD | Backend devuelve **409**. Frontend muestra mensaje y opción “Revisar Pagos”. Documentado en COHERENCIA_BACK_FRONT_CARGA_MASIVA. |
| Normalización para duplicados | Backend usa `_normalizar_numero_documento` y `_truncar_numero_documento` antes de comprobar duplicados y de guardar; frontend usa `normalizarNumeroDocumento`. Coherente. |

**Conclusión:** Formato y manejo de **duplicados** en carga masiva están alineados y resueltos.

---

### 2.4 Reconocimiento automático de crédito

| Aspecto | Estado (documentado y en código) |
|--------|-----------------------------------|
| Cédulas para batch | Solo se envían al batch cédulas con formato V/E/J/Z + 6–11 dígitos; no se usa número de documento como cédula. |
| Un solo crédito por cédula | Se asigna ese `prestamo_id` a todas las filas de esa cédula. |
| Fallback una sola cédula en archivo | Si en todo el archivo solo hay una cédula con créditos, se usa para todas las filas. |

**Conclusión:** El **formato** de cédula y la lógica de asignación de crédito en carga masiva están resueltos y documentados.

---

## 3. Resumen: ¿se resolvió el problema de carga masiva en cuanto a formato?

**Sí.** En cuanto a formato, el problema de carga masiva quedó resuelto en estos puntos:

1. **Formato de documento**
   - Número largo (12+ dígitos) y notación científica: se leen y guardan como string de dígitos completos (umbral 1e11 en frontend).
   - Formatos alfanuméricos (BS./, BINANCE/, VE/, etc.): aceptados sin quitar símbolos.
   - Documentos muy largos (&gt; 100 caracteres): truncados en backend a 100 caracteres para evitar 500.

2. **Formato de crédito (prestamo_id)**
   - Si se envía un número de documento como crédito: validación en schema → 422 con mensaje claro; en CSV backend se trata como “sin crédito”. Ya no hay 500 por “integer out of range”.

3. **Duplicados**
   - 409 coherente entre backend y frontend; normalización y truncado aplicados antes de comparar y guardar.

4. **Reconocimiento de crédito**
   - Cédulas con formato correcto; asignación automática cuando hay un solo préstamo activo; fallback cuando solo hay una cédula con créditos en el archivo.

La documentación (COHERENCIA_BACK_FRONT_CARGA_MASIVA, CONFIG_CARGA_MASIVA_PAGOS_EXCEL, AUDITORIA_FORMATO_DOCUMENTO_740087408305094, AUDITORIA_RECONOCIMIENTO_CREDITO_CARGA_MASIVA) describe el diseño y las reglas; las correcciones de **truncado de documento** y **validación de prestamo_id** se añadieron después en código y evitan los 500 que aún aparecían en logs. Para no perder esta información, conviene actualizar AUDITORIA_FORMATO_DOCUMENTO_740087408305094 con el umbral 1e11 (no 1e14) y añadir en CONFIG o en un doc de “errores evitados” la mención al truncado a 100 caracteres y a la validación de rango de `prestamo_id`.
