# 🔧 Solución: INSERT No Inserta Registros

**Problema:** El INSERT ejecuta sin errores pero no inserta ningún registro.

---

## 🔍 Diagnóstico

### Posibles Causas:

1. **Tabla temporal vacía** - El CSV no se cargó correctamente
2. **Condiciones WHERE muy estrictas** - Los datos no cumplen las condiciones
3. **Error silencioso** - Hay un error que no se muestra

---

## ✅ Pasos para Diagnosticar

### 1. Verificar si hay datos en temporal:

```sql
SELECT COUNT(*) as total_en_temporal FROM clientes_temp;
```

**Si es 0:** El CSV no se cargó. Revisa la importación en DBeaver.

**Si es > 0:** Continúa con el siguiente paso.

---

### 2. Verificar condiciones WHERE:

```sql
SELECT 
    'Total registros' as tipo,
    COUNT(*) as cantidad
FROM clientes_temp

UNION ALL

SELECT 
    'Con cédula válida' as tipo,
    COUNT(*) as cantidad
FROM clientes_temp
WHERE cedula IS NOT NULL AND TRIM(cedula) != ''

UNION ALL

SELECT 
    'Con nombres válidos' as tipo,
    COUNT(*) as cantidad
FROM clientes_temp
WHERE nombres IS NOT NULL AND TRIM(nombres) != ''

UNION ALL

SELECT 
    'Cumplen todas las condiciones' as tipo,
    COUNT(*) as cantidad
FROM clientes_temp
WHERE cedula IS NOT NULL 
  AND TRIM(cedula) != ''
  AND nombres IS NOT NULL 
  AND TRIM(nombres) != '';
```

**Si "Cumplen todas las condiciones" es 0:** Los datos no cumplen las condiciones. Revisa el formato del CSV.

**Si es > 0:** Hay un problema con el INSERT. Continúa.

---

### 3. Ver ejemplo de datos:

```sql
SELECT 
    id,
    cedula,
    nombres,
    email,
    estado,
    CASE 
        WHEN cedula IS NULL THEN 'Cédula NULL'
        WHEN TRIM(cedula) = '' THEN 'Cédula vacía'
        ELSE 'OK'
    END as estado_cedula,
    CASE 
        WHEN nombres IS NULL THEN 'Nombres NULL'
        WHEN TRIM(nombres) = '' THEN 'Nombres vacíos'
        ELSE 'OK'
    END as estado_nombres
FROM clientes_temp 
LIMIT 10;
```

---

### 4. Probar INSERT manual con un registro:

```sql
-- Insertar solo el primer registro válido
INSERT INTO clientes (
    cedula, nombres, telefono, email, direccion,
    fecha_nacimiento, ocupacion, estado, activo,
    fecha_registro, fecha_actualizacion, usuario_registro, notas
)
SELECT 
    REPLACE(REPLACE(TRIM(COALESCE(cedula, '')), '-', ''), ' ', '') as cedula,
    TRIM(COALESCE(nombres, '')) as nombres,
    TRIM(COALESCE(telefono, '+589999999999')) as telefono,
    LOWER(TRIM(COALESCE(email, 'buscaremail@noemail.com'))) as email,
    TRIM(COALESCE(direccion, 'Actualizar dirección')) as direccion,
    COALESCE(fecha_nacimiento, '2000-01-01'::date) as fecha_nacimiento,
    TRIM(COALESCE(ocupacion, 'Actualizar ocupación')) as ocupacion,
    CASE 
        WHEN UPPER(TRIM(COALESCE(estado, ''))) IN ('ACTIVO', 'INACTIVO', 'FINALIZADO') 
        THEN UPPER(TRIM(estado))
        ELSE 'ACTIVO'
    END as estado,
    COALESCE(activo, true) as activo,
    COALESCE(fecha_registro, CURRENT_TIMESTAMP) as fecha_registro,
    CURRENT_TIMESTAMP as fecha_actualizacion,
    COALESCE(usuario_registro, 'SISTEMA') as usuario_registro,
    COALESCE(notas, 'No hay observaciones') as notas
FROM clientes_temp
WHERE cedula IS NOT NULL 
  AND TRIM(cedula) != ''
  AND nombres IS NOT NULL 
  AND TRIM(nombres) != ''
LIMIT 1;

-- Verificar si se insertó
SELECT COUNT(*) as registros_insertados FROM clientes;
```

**Si se inserta:** El INSERT funciona, pero hay un problema con el conjunto completo. Revisa si hay restricciones o triggers.

**Si no se inserta:** Hay un error. Revisa los mensajes de error en DBeaver.

---

## 🛠️ Soluciones Comunes

### Problema 1: CSV no se cargó correctamente

**Solución:**
1. Verificar que el CSV tiene encabezados correctos
2. Re-importar usando la herramienta de DBeaver
3. Verificar que los datos se cargaron: `SELECT COUNT(*) FROM clientes_temp;`

---

### Problema 2: Datos no cumplen condiciones WHERE

**Solución:**
1. Verificar formato de cédula y nombres en el CSV
2. Ajustar condiciones WHERE si es necesario
3. O limpiar datos antes de importar

---

### Problema 3: Restricciones o triggers bloquean INSERT

**Solución:**
1. Verificar restricciones CHECK en la tabla `clientes`
2. Verificar triggers que puedan estar bloqueando
3. Revisar logs de errores en DBeaver

---

## 📋 Script de Diagnóstico Completo

Usa el script: `scripts/sql/diagnosticar_importacion_clientes.sql`

Este script ejecuta todas las verificaciones automáticamente.

---

## ✅ Script Corregido

El script `importar_clientes_desde_csv_dbeaver.sql` ahora incluye:
- ✅ Verificación antes del INSERT
- ✅ Diagnóstico automático
- ✅ Mensajes claros de error

---

**¿Necesitas ayuda con algún paso específico?** Ejecuta el script de diagnóstico y comparte los resultados.

