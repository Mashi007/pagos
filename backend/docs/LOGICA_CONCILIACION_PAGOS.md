# 📋 LÓGICA DE CONCILIACIÓN DE PAGOS

## Fecha de Documentación
2025-11-06

---

## 🎯 PROCESO DE CONCILIACIÓN

### Descripción General

La conciliación de pagos se realiza mediante la comparación **EXACTA** del campo `numero_documento` entre:
- **Reporte Bancario (Excel):** Columna "Número de Documento"
- **Tabla `pagos`:** Campo `numero_documento`

---

## 📊 FLUJO DE CONCILIACIÓN

### PASO 1: Carga Masiva de Pagos (Opcional)

**Endpoint:** `POST /api/v1/pagos/upload`

**Proceso:**
1. Se sube archivo Excel con pagos (columnas: Cédula, Fecha, Monto, Número de Documento)
2. Para cada pago nuevo:
   - Se verifica si el `numero_documento` ya existe EXACTAMENTE en la BD
   - Si existe → se crea el pago con `conciliado = TRUE`
   - Si no existe → se crea el pago con `conciliado = FALSE`

**Archivo:** `backend/app/api/v1/endpoints/pagos_upload.py` (líneas 122-139)

---

### PASO 2: Conciliación Bancaria (Principal)

**Endpoint:** `POST /api/v1/pagos/conciliacion/upload`

**Proceso:**
1. Se sube archivo Excel (reporte bancario) con 2 columnas:
   - **"Fecha de Depósito"**
   - **"Número de Documento"**

2. Para cada fila del Excel:
   - Se lee el `numero_documento` del Excel
   - Se normaliza (trim espacios): `numero_documento_normalizado = numero_documento.strip()`
   - Se busca en la tabla `pagos` con comparación EXACTA:
     ```sql
     WHERE TRIM(numero_documento) = numero_documento_normalizado
       AND activo = TRUE
     ```

3. **Si encuentra coincidencia EXACTA:**
   - ✅ Se marca `conciliado = TRUE`
   - ✅ Se establece `fecha_conciliacion = datetime.now()`
   - ✅ Se establece `verificado_concordancia = 'SI'`
   - ✅ Se guarda en la BD

4. **Si NO encuentra coincidencia EXACTA:**
   - ❌ El pago NO se marca como conciliado
   - ❌ Permanece con `conciliado = FALSE` (o el valor que tenía)
   - ❌ Permanece con `verificado_concordancia = 'NO'` (o el valor que tenía)
   - ⚠️ Se registra como "no encontrado" en el resultado

**Archivo:** `backend/app/api/v1/endpoints/pagos_conciliacion.py` (líneas 65-110)

---

## ✅ REGLAS DE CONCILIACIÓN

### 1. Comparación EXACTA

**Regla:** La comparación es **EXACTA** (case-sensitive, sin espacios)

**Ejemplos:**

| Excel | BD | ¿Coincide? | Resultado |
|-------|----|-----------|-----------|
| `740087407785556` | `740087407785556` | ✅ SÍ | `conciliado = TRUE`, `verificado_concordancia = 'SI'` |
| `740087407785556` | ` 740087407785556 ` | ✅ SÍ | `conciliado = TRUE` (trim normaliza espacios) |
| `740087407785556` | `740087407785557` | ❌ NO | `conciliado = FALSE`, `verificado_concordancia = 'NO'` |
| `ZELLE` | `zelle` | ❌ NO | `conciliado = FALSE` (case-sensitive) |
| `s/n` | `S/N` | ❌ NO | `conciliado = FALSE` (case-sensitive) |

### 2. Normalización

**Proceso:**
- Se aplica `trim()` (elimina espacios al inicio y final)
- **NO** se convierte a mayúsculas/minúsculas (case-sensitive)
- **NO** se eliminan espacios internos

**Código:**
```python
numero_documento_normalizado = numero_documento.strip()
```

### 3. Verificación Adicional

**Antes de marcar como conciliado:**
- Se verifica que el `numero_documento` de la BD coincida EXACTAMENTE con el del Excel
- Si no coincide exactamente, NO se marca como conciliado (aunque la query lo encontró)

**Código:**
```python
numero_documento_bd = str(pago.numero_documento).strip() if pago.numero_documento else ""
if numero_documento_bd != numero_documento_normalizado:
    # NO conciliar
    return (0, [numero_documento_normalizado], [])
```

---

## 🔍 CAMPOS AFECTADOS

### Al Conciliar (Coincidencia EXACTA)

| Campo | Valor |
|-------|-------|
| `conciliado` | `TRUE` |
| `fecha_conciliacion` | `datetime.now()` |
| `verificado_concordancia` | `'SI'` |

### Si NO se Concilia (Sin Coincidencia)

| Campo | Valor |
|-------|-------|
| `conciliado` | `FALSE` (o valor anterior) |
| `fecha_conciliacion` | `NULL` (o valor anterior) |
| `verificado_concordancia` | `'NO'` (o valor anterior) |

---

## 📝 EJEMPLOS PRÁCTICOS

### Ejemplo 1: Conciliación Exitosa

**Excel (Reporte Bancario):**
```
Fecha de Depósito | Número de Documento
2025-11-06        | 740087407785556
```

**BD (Tabla `pagos`):**
```
id | numero_documento      | conciliado | verificado_concordancia
1  | 740087407785556       | FALSE      | NO
```

**Resultado:**
```
id | numero_documento      | conciliado | fecha_conciliacion      | verificado_concordancia
1  | 740087407785556       | TRUE       | 2025-11-06 10:30:00     | SI
```

---

### Ejemplo 2: Sin Coincidencia

**Excel (Reporte Bancario):**
```
Fecha de Depósito | Número de Documento
2025-11-06        | 740087407785556
```

**BD (Tabla `pagos`):**
```
id | numero_documento      | conciliado | verificado_concordancia
1  | 740087407785557       | FALSE      | NO
```

**Resultado:**
```
id | numero_documento      | conciliado | fecha_conciliacion | verificado_concordancia
1  | 740087407785557       | FALSE      | NULL                | NO
```

**Nota:** El pago NO se marca como conciliado porque el número de documento no coincide exactamente.

---

### Ejemplo 3: Coincidencia con Espacios

**Excel (Reporte Bancario):**
```
Fecha de Depósito | Número de Documento
2025-11-06        |  740087407785556  
```

**BD (Tabla `pagos`):**
```
id | numero_documento      | conciliado | verificado_concordancia
1  | 740087407785556       | FALSE      | NO
```

**Resultado:**
```
id | numero_documento      | conciliado | fecha_conciliacion      | verificado_concordancia
1  | 740087407785556       | TRUE       | 2025-11-06 10:30:00     | SI
```

**Nota:** Los espacios se normalizan con `trim()`, por lo que coincide.

---

## ⚠️ CASOS ESPECIALES

### 1. Duplicados en Excel

**Comportamiento:**
- Si el mismo `numero_documento` aparece múltiples veces en el Excel, solo se procesa la primera vez
- Las siguientes apariciones se ignoran (no se vuelven a conciliar)

**Código:**
```python
if numero_documento in documentos_procesados:
    return (0, [], [])  # Ignorar duplicado
documentos_procesados.add(numero_documento)
```

### 2. Pago Ya Conciliado

**Comportamiento:**
- Si el pago ya está conciliado (`conciliado = TRUE`), NO se vuelve a conciliar
- Se registra en logs pero no se modifica

**Código:**
```python
if pago.conciliado:
    logger.info(f"Pago ID {pago.id} ya estaba conciliado")
    return False  # No se concilia nuevamente
```

### 3. Múltiples Pagos con Mismo `numero_documento`

**Comportamiento:**
- Si hay múltiples pagos con el mismo `numero_documento`, se concilia el PRIMERO encontrado
- Los demás NO se concilian automáticamente

**Código:**
```python
pago = db.query(Pago)
    .filter(func.trim(Pago.numero_documento) == numero_documento_normalizado, Pago.activo.is_(True))
    .first()  # Solo el primero
```

---

## 📊 RESULTADO DE LA CONCILIACIÓN

### Respuesta del Endpoint

```json
{
  "pagos_conciliados": 150,
  "pagos_no_encontrados": 25,
  "documentos_no_encontrados": ["740087407785556", "ZELLE", ...],
  "errores": 0,
  "errores_detalle": []
}
```

### Campos Explicados

- **`pagos_conciliados`:** Cantidad de pagos marcados como conciliados (coincidencia EXACTA)
- **`pagos_no_encontrados`:** Cantidad de `numero_documento` del Excel que NO se encontraron en la BD
- **`documentos_no_encontrados`:** Lista de `numero_documento` que no se encontraron (primeros 20)
- **`errores`:** Cantidad de errores al procesar el archivo
- **`errores_detalle`:** Detalle de errores (primeros 10)

---

## ✅ CONFIRMACIÓN DE LÓGICA

### Regla Principal

**✅ CONFIRMADO:**

1. **Al subir archivo Excel (reporte bancario):**
   - Se compara `numero_documento` del Excel con `numero_documento` de la tabla `pagos`
   - Comparación: **EXACTA** (case-sensitive, con normalización de espacios con `trim()`)

2. **Si coincide EXACTAMENTE:**
   - ✅ `conciliado = TRUE`
   - ✅ `fecha_conciliacion = datetime.now()`
   - ✅ `verificado_concordancia = 'SI'`

3. **Si NO coincide EXACTAMENTE:**
   - ❌ `conciliado = FALSE` (o valor anterior)
   - ❌ `fecha_conciliacion = NULL` (o valor anterior)
   - ❌ `verificado_concordancia = 'NO'` (o valor anterior)

---

## 🔧 IMPLEMENTACIÓN ACTUAL

### Archivos Relevantes

1. **`backend/app/api/v1/endpoints/pagos_conciliacion.py`**
   - Endpoint: `POST /api/v1/pagos/conciliacion/upload`
   - Función: `_procesar_fila_conciliacion()` (líneas 65-114)
   - Función: `_conciliar_pago()` (líneas 47-62)

2. **`backend/app/api/v1/endpoints/pagos_upload.py`**
   - Endpoint: `POST /api/v1/pagos/upload`
   - Función: `_procesar_fila_pago()` (líneas 64-172)
   - Verifica conciliación al crear pagos nuevos

---

## 📈 ESTADÍSTICAS ACTUALES

Según la verificación realizada:

- **Total de Pagos:** 13,679
- **Pagos Conciliados:** 2,386 (17.44%)
- **Pagos Sin Conciliar:** 11,293 (82.56%)
- **`verificado_concordancia = 'NO'`:** 13,679 (100%)

**Observación:** Todos los pagos tienen `verificado_concordancia = 'NO'`, lo que indica que:
- O no se ha ejecutado el proceso de conciliación bancaria
- O los `numero_documento` del reporte bancario no coinciden exactamente con los de la BD

---

## 🎯 RECOMENDACIONES

### Para Mejorar la Conciliación

1. **Verificar Formato de `numero_documento`:**
   - Asegurar que el formato en el Excel coincida exactamente con el de la BD
   - Considerar normalización adicional si es necesario (ej: eliminar guiones, espacios internos)

2. **Revisar Casos de "No Encontrados":**
   - Analizar los `numero_documento` que no se encuentran
   - Verificar si hay diferencias de formato (espacios, mayúsculas, etc.)

3. **Implementar Logs Detallados:**
   - Registrar todos los casos de no coincidencia
   - Identificar patrones de diferencias

---

**Última actualización:** 2025-11-06

