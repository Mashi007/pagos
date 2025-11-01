# 📋 GUÍA PASO A PASO: Cargar Fechas de Aprobación desde CSV

## 🎯 OBJETIVO
Cargar fechas de aprobación desde un archivo CSV e integrarlas a la tabla `prestamos`.

---

## 📝 PREPARACIÓN DEL ARCHIVO CSV

### Paso 1: Crear el archivo CSV

Crea un archivo de texto con extensión `.csv` (por ejemplo: `fechas_aprobacion.csv`)

### Paso 2: Formato del archivo

El archivo debe tener **exactamente** este formato:

```csv
cedula,fecha_aprobacion
V30596349,2025-05-24
V12345678,2025-05-25
V98765432,2025-05-26
```

**IMPORTANTE:**
- Primera línea: encabezados `cedula,fecha_aprobacion`
- Fechas en formato: `YYYY-MM-DD` (ejemplo: 2025-05-24 para 24/05/2025)
- Sin espacios adicionales
- Sin comillas (o todas las celdas entre comillas)
- Separador: coma (`,`)
- Codificación: UTF-8

### Paso 3: Ejemplo completo del archivo

```csv
cedula,fecha_aprobacion
V30596349,2025-05-24
V26844298,2025-05-24
V31007833,2025-05-24
V31379675,2025-05-25
V32028626,2025-05-25
```

**Guarda el archivo en una ubicación que puedas acceder fácilmente** (por ejemplo: `C:\Users\PORTATIL\Documents\fechas_aprobacion.csv`)

---

## 🗄️ PASO 1: Crear la tabla temporal en DBeaver

### 1.1 Abre DBeaver y conéctate a tu base de datos

### 1.2 Abre el script: `Crear_Tabla_Fechas_Aprobacion.sql`

### 1.3 Ejecuta SOLO el PASO 1 (hasta la línea del CREATE INDEX):

```sql
-- Crear tabla temporal (si ya existe, la elimina primero)
DROP TABLE IF EXISTS fechas_aprobacion_temp CASCADE;

CREATE TABLE fechas_aprobacion_temp (
    id SERIAL PRIMARY KEY,
    cedula VARCHAR(20) NOT NULL,
    fecha_aprobacion DATE NOT NULL,
    observaciones TEXT,
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crear índice para búsqueda rápida por cédula
CREATE INDEX idx_fechas_aprobacion_cedula ON fechas_aprobacion_temp(cedula);
```

### 1.4 Verifica que la tabla se creó

Ejecuta esta consulta para verificar:
```sql
SELECT * FROM fechas_aprobacion_temp LIMIT 1;
```

Si no da error, la tabla está creada correctamente ✅

---

## 📤 PASO 2: Cargar datos desde CSV (DBeaver)

### 2.1 En DBeaver, en el panel izquierdo (Database Navigator):

1. Expande tu base de datos
2. Expande `Schemas` → `public` → `Tables`
3. Busca la tabla `fechas_aprobacion_temp`
4. **Click derecho** sobre `fechas_aprobacion_temp`
5. Selecciona: **"Import Data"** o **"Importar datos"**

### 2.2 En la ventana de importación:

1. **Source:** Selecciona tu archivo CSV
   - Click en "Browse" o "Examinar"
   - Navega a donde guardaste `fechas_aprobacion.csv`
   - Selecciónalo y click "Abrir"

2. **Format:** Selecciona **"CSV"**

3. **Options:**
   - ✅ Marca: **"First line is header"** o **"Primera línea es encabezado"**
   - **Delimiter:** `,` (coma)
   - **Encoding:** UTF-8

4. **Column Mapping (Mapeo de columnas):**
   - Verifica que:
     - `cedula` del CSV → `cedula` de la tabla
     - `fecha_aprobacion` del CSV → `fecha_aprobacion` de la tabla
   - Las columnas `id`, `observaciones`, `fecha_carga` se llenan automáticamente

5. Click **"Next"** o **"Siguiente"**

### 2.3 Revisa la vista previa:

- Deberías ver tus datos en formato tabla
- Verifica que las fechas se ven correctas (formato YYYY-MM-DD)
- Si todo está bien, click **"Next"**

### 2.4 Configuración final:

1. **Import mode:** Selecciona **"Insert"** o **"Insertar"**
2. **On error:** Selecciona **"Skip row"** o **"Omitir fila"** (para que continue si hay errores)
3. Click **"Start"** o **"Iniciar"**

### 2.5 Espera a que termine:

- Verás un mensaje de progreso
- Al finalizar, te mostrará cuántas filas se insertaron
- Click **"Finish"** o **"Finalizar"**

---

## ✅ PASO 3: Verificar datos cargados

### 3.1 Ejecuta en DBeaver:

```sql
-- Total de registros cargados
SELECT 
    'Total registros en tabla temporal' AS metrica,
    COUNT(*) AS cantidad
FROM fechas_aprobacion_temp;
```

**Debe mostrar el mismo número que filas tiene tu CSV** (sin contar el encabezado)

### 3.2 Verifica que no hay duplicados:

```sql
-- Verificar duplicados por cédula
SELECT 
    cedula,
    COUNT(*) AS cantidad_veces,
    STRING_AGG(fecha_aprobacion::TEXT, ', ') AS fechas
FROM fechas_aprobacion_temp
GROUP BY cedula
HAVING COUNT(*) > 1;
```

**Si esta consulta NO devuelve filas, está bien ✅**
**Si devuelve filas, tienes duplicados - revisa tu CSV**

### 3.3 Ver ejemplos de datos cargados:

```sql
-- Ejemplo de datos cargados (primeros 10)
SELECT 
    id,
    cedula,
    fecha_aprobacion,
    observaciones,
    fecha_carga
FROM fechas_aprobacion_temp
ORDER BY id
LIMIT 10;
```

**Verifica que las cédulas y fechas se vean correctas**

---

## 🔗 PASO 4: Verificar coincidencias con préstamos

### 4.1 Ejecuta esta consulta:

```sql
-- Cuántos préstamos coinciden con las cédulas en la tabla temporal
SELECT 
    'Préstamos que coinciden con tabla temporal' AS metrica,
    COUNT(DISTINCT p.id) AS cantidad_prestamos
FROM prestamos p
INNER JOIN fechas_aprobacion_temp f ON p.cedula = f.cedula
WHERE p.estado = 'APROBADO';
```

**Este número debería ser igual o menor al total de préstamos aprobados**

### 4.2 Verifica cédulas que no coinciden:

```sql
-- Préstamos aprobados que NO están en tabla temporal
SELECT 
    'Préstamos aprobados SIN fecha en tabla temporal' AS metrica,
    COUNT(DISTINCT p.id) AS cantidad
FROM prestamos p
LEFT JOIN fechas_aprobacion_temp f ON p.cedula = f.cedula
WHERE p.estado = 'APROBADO'
    AND f.id IS NULL;
```

**Si este número es alto, falta agregar más cédulas a tu CSV**

---

## 🔄 PASO 5: Integrar fechas a prestamos

### 5.1 Abre el script: `Integrar_Fechas_Aprobacion.sql`

### 5.2 Ejecuta el PASO 1 (verificación antes de actualizar):

```sql
-- Total de préstamos que se actualizarán
SELECT 
    'Préstamos que se actualizarán' AS metrica,
    COUNT(DISTINCT p.id) AS cantidad
FROM prestamos p
INNER JOIN fechas_aprobacion_temp f ON p.cedula = f.cedula
WHERE p.estado = 'APROBADO';
```

**Anota este número - debe coincidir con tus expectativas**

### 5.3 Ejecuta el PASO 2 (actualizar fecha_aprobacion):

```sql
-- Actualizar fecha_aprobacion
UPDATE prestamos p
SET 
    fecha_aprobacion = f.fecha_aprobacion::TIMESTAMP,
    fecha_actualizacion = CURRENT_TIMESTAMP
FROM fechas_aprobacion_temp f
WHERE p.cedula = f.cedula
    AND p.estado = 'APROBADO'
    AND p.fecha_aprobacion IS NULL;
```

**Verifica el mensaje: "Updated Rows: X" (debe ser el número esperado)**

### 5.4 Ejecuta el PASO 3 (actualizar fecha_base_calculo):

```sql
-- Actualizar fecha_base_calculo
UPDATE prestamos p
SET 
    fecha_base_calculo = f.fecha_aprobacion,
    fecha_actualizacion = CURRENT_TIMESTAMP
FROM fechas_aprobacion_temp f
WHERE p.cedula = f.cedula
    AND p.estado = 'APROBADO'
    AND (p.fecha_base_calculo IS NULL OR p.fecha_base_calculo != f.fecha_aprobacion);
```

**Verifica el mensaje: "Updated Rows: X"**

---

## ✅ PASO 6: Verificación final

### 6.1 Ejecuta estas consultas para verificar:

```sql
-- Verificar que las fechas se actualizaron
SELECT 
    'Préstamos con fecha_aprobacion actualizada' AS metrica,
    COUNT(*) AS cantidad
FROM prestamos p
INNER JOIN fechas_aprobacion_temp f ON p.cedula = f.cedula
WHERE p.estado = 'APROBADO'
    AND DATE(p.fecha_aprobacion) = f.fecha_aprobacion;

-- Verificar coincidencia entre fecha_aprobacion y fecha_base_calculo
SELECT 
    'Préstamos donde fecha_base_calculo = fecha_aprobacion' AS metrica,
    COUNT(*) AS cantidad
FROM prestamos
WHERE estado = 'APROBADO'
    AND fecha_aprobacion IS NOT NULL
    AND fecha_base_calculo IS NOT NULL
    AND DATE(fecha_aprobacion) = fecha_base_calculo;
```

### 6.2 Ver ejemplos de préstamos actualizados:

```sql
-- Ejemplo de préstamos actualizados (primeros 10)
SELECT 
    p.id,
    p.cedula,
    p.nombres,
    DATE(p.fecha_aprobacion) AS fecha_aprobacion_date,
    p.fecha_base_calculo,
    CASE 
        WHEN DATE(p.fecha_aprobacion) = p.fecha_base_calculo THEN '✅ COINCIDEN'
        ELSE '❌ NO COINCIDEN'
    END AS verificacion
FROM prestamos p
INNER JOIN fechas_aprobacion_temp f ON p.cedula = f.cedula
WHERE p.estado = 'APROBADO'
ORDER BY p.id
LIMIT 10;
```

**Todas las filas deben mostrar "✅ COINCIDEN"**

---

## 🧹 PASO 7: Limpieza (Opcional)

Una vez verificado que todo está correcto, puedes eliminar la tabla temporal:

```sql
DROP TABLE IF EXISTS fechas_aprobacion_temp;
```

---

## ⚠️ PROBLEMAS COMUNES Y SOLUCIONES

### Error: "Invalid date format"
- **Solución:** Verifica que las fechas en tu CSV estén en formato `YYYY-MM-DD` (ejemplo: 2025-05-24)

### Error: "Column does not exist"
- **Solución:** Verifica que los encabezados en tu CSV sean exactamente: `cedula,fecha_aprobacion`

### "0 rows updated"
- **Solución:** 
  - Verifica que las cédulas en tu CSV coincidan exactamente con las de la base de datos
  - Verifica que los préstamos estén en estado 'APROBADO'
  - Ejecuta el PASO 4 para verificar coincidencias

### Muchos duplicados
- **Solución:** Si una cédula tiene múltiples préstamos, todos usarán la misma fecha (esto es normal)

---

## 📊 RESUMEN

1. ✅ Crear tabla temporal
2. ✅ Preparar CSV con formato correcto
3. ✅ Cargar CSV en DBeaver
4. ✅ Verificar datos cargados
5. ✅ Integrar fechas a prestamos
6. ✅ Verificar resultados
7. ✅ (Opcional) Eliminar tabla temporal

**Después de esto, podrás ejecutar el script de generación masiva de cuotas!** 🎉

