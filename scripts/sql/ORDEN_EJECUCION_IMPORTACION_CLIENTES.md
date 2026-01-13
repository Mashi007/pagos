# 📋 ORDEN DE EJECUCIÓN DE SCRIPTS SQL PARA IMPORTACIÓN DE CLIENTES

## 🎯 OBJETIVO
Este documento describe el orden correcto de ejecución de los scripts SQL para preparar e importar datos de clientes desde un CSV a la tabla `clientes`.

---

## 📌 ORDEN DE EJECUCIÓN RECOMENDADO

### **FASE 1: PREPARACIÓN Y VERIFICACIÓN PREVIA** ⚙️

#### **1.1 Verificar Estado de la Tabla y Secuencia de IDs**
**Script:** `verificar_secuencia_id_clientes.sql`

**Propósito:**
- Verificar que la tabla `clientes` esté vacía
- Confirmar el estado de la secuencia de IDs
- Determinar desde qué número iniciará el próximo ID

**Qué hacer:**
- Ejecutar el script completo
- Revisar los resultados en la sección "CONFIRMACIÓN FINAL"
- Si la tabla está vacía pero la secuencia NO está en 0:
  - Descomentar la sección "OPCIÓN: RESETEAR SECUENCIA A 1"
  - Ejecutar esa sección para resetear la secuencia a 1

**Resultado esperado:**
```
✅ CORRECTO: Empezará desde ID = 1
```

---

#### **1.2 Verificar Mapeo de Columnas del CSV**
**Script:** `verificar_mapeo_importacion_clientes.sql`

**Propósito:**
- Confirmar que todas las columnas necesarias están mapeadas
- Verificar que NO se está intentando mapear columnas eliminadas (`activo`)
- Confirmar que el mapeo coincide con la estructura actual de la tabla

**Qué hacer:**
- Ejecutar el script completo
- Revisar la sección "ESTRUCTURA ACTUAL DE TABLA CLIENTES"
- Confirmar que todas las columnas marcadas como "✅ DEBE MAPEARSE" están en tu CSV

**Resultado esperado:**
- Todas las columnas requeridas están presentes
- No hay intento de mapear `id` o `activo`

---

### **FASE 2: CARGA TEMPORAL Y VERIFICACIÓN DE DUPLICADOS** 🔍

#### **2.1 Actualizar Columna Teléfono en Tabla Final (OPCIONAL pero recomendado)**
**Script:** `actualizar_columna_telefono_clientes.sql`

**Propósito:**
- Aumentar el tamaño de la columna `telefono` de VARCHAR(15) a VARCHAR(50)
- Permite aceptar múltiples teléfonos separados por `/`

**Qué hacer:**
- Ejecutar el script antes de importar datos
- Esto evita errores al importar desde la tabla temporal a la final

---

#### **2.2 Crear Tabla Temporal**
**Script:** `crear_tabla_temporal_clientes.sql`

**Propósito:**
- Crear tabla temporal `clientes_temp` con estructura adecuada
- Las columnas de fecha son TEXT para aceptar formato español
- Columna `telefono` es VARCHAR(50) para aceptar múltiples números

**Qué hacer:**
- Ejecutar el script completo
- Verificar que la tabla se creó correctamente

---

#### **2.3 Cargar CSV a Tabla Temporal en DBeaver**
**Acción Manual en DBeaver:**
- Usar la herramienta de importación de DBeaver
- Cargar el CSV (`clientes_cvs (enero).csv`) a `clientes_temp`

**Importante:**
- NO importar directamente a `clientes`
- Usar la tabla temporal para verificar antes

---

#### **2.4 Limpiar Datos en Tabla Temporal**
**Script:** `limpiar_datos_tabla_temporal.sql`

**Propósito:**
- Limpiar espacios en blanco
- Normalizar cédulas, emails, estados
- Preparar datos para conversión de fechas

**Qué hacer:**
- Ejecutar DESPUÉS de importar el CSV
- Revisar los resultados de la verificación

---

#### **2.5 Convertir Fechas en Tabla Temporal**
**Script:** `convertir_fechas_tabla_temporal.sql`

**Propósito:**
- Convertir fechas de formato español a formato PostgreSQL
- Cambiar columnas de TEXT a DATE/TIMESTAMP

**Qué hacer:**
- Ejecutar DESPUÉS de limpiar los datos
- Verificar que las fechas se convirtieron correctamente

---

#### **2.6 Verificar Duplicados en el CSV**
**Script:** `verificar_duplicados_antes_importar.sql`

**Propósito:**
- Detectar duplicados dentro del CSV mismo
- Detectar conflictos con clientes existentes en la tabla `clientes`
- Generar un resumen antes de importar

**Qué hacer:**
1. **Ajustar el nombre de la tabla temporal** en el script:
   ```sql
   tabla_temp TEXT := 'clientes_temp';  -- ⚠️ CAMBIAR si usas otro nombre
   ```
2. Ejecutar el script completo
3. Revisar todas las secciones:
   - Duplicados en CSV (Cédula + Nombre)
   - Duplicados en CSV (Email)
   - Conflictos con clientes existentes

**Resultado esperado:**
```
✅ NO HAY DUPLICADOS NI CONFLICTOS. Puedes proceder con la importación.
```

**Si hay problemas:**
- Corregir duplicados en el CSV antes de continuar
- Decidir qué hacer con conflictos con clientes existentes

---

### **FASE 3: IMPORTACIÓN FINAL** 📥

#### **3.1 Importar desde Tabla Temporal a Tabla Final**
**Opciones:**

**Opción A: Importación Manual en DBeaver**
- Usar la herramienta de importación de DBeaver
- Mapear desde `clientes_temp` hacia `clientes`
- Configurar para manejar errores (skip o stop)

**Opción B: Script SQL de Inserción**
```sql
-- Ejemplo básico (ajustar según necesidades)
INSERT INTO clientes (
    cedula, nombres, telefono, email, direccion,
    fecha_nacimiento, ocupacion, estado,
    fecha_registro, fecha_actualizacion, usuario_registro, notas
)
SELECT 
    cedula, nombres, telefono, email, direccion,
    fecha_nacimiento, ocupacion, 
    COALESCE(estado, 'ACTIVO'),  -- Default ACTIVO si no viene
    COALESCE(fecha_registro, CURRENT_TIMESTAMP),
    COALESCE(fecha_actualizacion, CURRENT_TIMESTAMP),
    COALESCE(usuario_registro, 'itmaster@rapicreditca.com'),
    COALESCE(notas, 'No existe observaciones')
FROM clientes_temp
WHERE NOT EXISTS (
    -- Evitar duplicados por cédula + nombre
    SELECT 1 FROM clientes c
    WHERE c.cedula = clientes_temp.cedula
    AND LOWER(TRIM(c.nombres)) = LOWER(TRIM(clientes_temp.nombres))
)
AND NOT EXISTS (
    -- Evitar duplicados por email
    SELECT 1 FROM clientes c
    WHERE LOWER(TRIM(c.email)) = LOWER(TRIM(clientes_temp.email))
    AND clientes_temp.email NOT LIKE '%@noemail.com'
    AND clientes_temp.email NOT LIKE '%buscaremail%'
);
```

---

#### **3.2 Verificación Post-Importación**
**Script:** `verificar_secuencia_id_clientes.sql` (ejecutar nuevamente)

**Propósito:**
- Confirmar que los registros se importaron correctamente
- Verificar que los IDs se generaron correctamente
- Confirmar el total de registros importados

**Qué hacer:**
- Ejecutar la sección "VERIFICACIÓN 1: ESTADO ACTUAL DE LA TABLA"
- Comparar el total de registros con lo esperado

---

## 📊 RESUMEN DEL FLUJO COMPLETO

```
┌─────────────────────────────────────────────────────────────┐
│ FASE 1: PREPARACIÓN                                         │
├─────────────────────────────────────────────────────────────┤
│ 1. verificar_secuencia_id_clientes.sql                      │
│    └─> Verificar/resetear secuencia de IDs                  │
│                                                              │
│ 2. verificar_mapeo_importacion_clientes.sql                │
│    └─> Verificar mapeo de columnas                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 2: CARGA TEMPORAL Y VERIFICACIÓN                       │
├─────────────────────────────────────────────────────────────┤
│ 2.1. actualizar_columna_telefono_clientes.sql (opcional)   │
│ 2.2. crear_tabla_temporal_clientes.sql                      │
│ 2.3. Cargar CSV a tabla temporal (DBeaver)                  │
│ 2.4. limpiar_datos_tabla_temporal.sql                       │
│ 2.5. convertir_fechas_tabla_temporal.sql                    │
│ 2.6. verificar_duplicados_antes_importar.sql                │
│      └─> Verificar duplicados y conflictos                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 3: IMPORTACIÓN FINAL                                   │
├─────────────────────────────────────────────────────────────┤
│ 3.1. Importar desde temporal a clientes                    │
│      (DBeaver o script SQL)                                 │
│                                                              │
│ 3.2. verificar_secuencia_id_clientes.sql (nuevamente)      │
│      └─> Verificar importación exitosa                     │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚠️ VALIDACIONES QUE SE APLICARÁN AUTOMÁTICAMENTE

Durante la importación, el backend aplicará estas validaciones:

### ✅ **Duplicados que BLOQUEAN la creación:**
- Misma **cédula** Y mismo **nombre completo** (ambos juntos)
- Mismo **email** (excepto emails genéricos como `@noemail.com`)

### ✅ **Duplicados que NO bloquean:**
- Mismo **teléfono** (se permite)
- Misma **cédula** con diferente nombre (se permite)
- Mismo **nombre** con diferente cédula (se permite)

### ✅ **Valores por defecto:**
- `estado`: `'ACTIVO'` (si no viene en CSV)
- `fecha_registro`: `CURRENT_TIMESTAMP` (si no viene)
- `fecha_actualizacion`: `CURRENT_TIMESTAMP` (si no viene)
- `usuario_registro`: Usuario del sistema (si no viene)
- `notas`: `'No existe observaciones'` (si no viene)

---

## 🔧 SOLUCIÓN DE PROBLEMAS

### **Problema: La secuencia no está en 0**
**Solución:** Descomentar y ejecutar la sección "OPCIÓN: RESETEAR SECUENCIA A 1" en `verificar_secuencia_id_clientes.sql`

### **Problema: Hay duplicados en el CSV**
**Solución:** 
- Revisar los resultados de `verificar_duplicados_antes_importar.sql`
- Corregir el CSV eliminando o corrigiendo los duplicados
- Volver a ejecutar la verificación

### **Problema: Hay conflictos con clientes existentes**
**Solución:**
- Revisar los conflictos específicos
- Decidir si actualizar los existentes o saltar los nuevos
- Ajustar el script de inserción según la decisión

### **Problema: Error durante la importación**
**Solución:**
- Revisar los mensajes de error específicos
- Verificar que todas las columnas requeridas tienen valores válidos
- Verificar formatos de fecha, email, teléfono según los validadores

---

## 📝 NOTAS IMPORTANTES

1. **Siempre usar tabla temporal primero** para verificar antes de importar directamente
2. **Backup recomendado:** Hacer backup de la tabla `clientes` antes de importar masivamente
3. **Validaciones del backend:** Aunque verifiques con SQL, el backend aplicará sus propias validaciones
4. **Manejo de errores:** Durante la importación masiva, algunos registros pueden fallar; revisa los logs

---

## ✅ CHECKLIST ANTES DE IMPORTAR

- [ ] Tabla `clientes` está vacía (o lista para recibir datos)
- [ ] Secuencia de IDs está en 0 (próximo ID será 1)
- [ ] Mapeo de columnas es correcto
- [ ] CSV cargado en tabla temporal
- [ ] No hay duplicados en el CSV
- [ ] No hay conflictos con clientes existentes (o se decidió cómo manejarlos)
- [ ] Backup de la tabla `clientes` realizado (si aplica)
- [ ] Listo para proceder con la importación final

---

**Fecha de creación:** 2026-01-XX  
**Última actualización:** 2026-01-XX
