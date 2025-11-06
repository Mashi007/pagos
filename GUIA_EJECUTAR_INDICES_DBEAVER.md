# 📋 Guía: Ejecutar Script de Índices en DBeaver

## ✅ SÍ, puedes ejecutar el script desde DBeaver

DBeaver es perfecto para ejecutar scripts SQL. Aquí te explico cómo hacerlo paso a paso.

---

## 🚀 PASO A PASO

### 1. Abrir DBeaver y Conectar a tu Base de Datos

1. Abre DBeaver
2. Conecta a tu base de datos PostgreSQL
3. Selecciona la base de datos correcta en el panel izquierdo

---

### 2. Abrir el Script SQL

**Opción A: Abrir archivo directamente**
1. En DBeaver: `File` → `Open File` (o `Ctrl+O`)
2. Navega a: `backend/scripts/migracion_indices_dashboard.sql`
3. Se abrirá en una nueva pestaña SQL

**Opción B: Copiar y pegar**
1. Abre el archivo `backend/scripts/migracion_indices_dashboard.sql` en tu editor
2. Copia todo el contenido (`Ctrl+A`, `Ctrl+C`)
3. En DBeaver, crea una nueva pestaña SQL (`Ctrl+\` o `SQL Editor`)
4. Pega el contenido (`Ctrl+V`)

---

### 3. Verificar el Contenido del Script

El script debe comenzar con:
```sql
-- ============================================================================
-- MIGRACIÓN: ÍNDICES CRÍTICOS PARA OPTIMIZAR DASHBOARD
-- ============================================================================
BEGIN;
...
```

---

### 4. Ejecutar el Script

**Opción A: Ejecutar todo el script (Recomendado)**
1. Asegúrate de estar en la pestaña SQL con el script
2. Presiona `Ctrl+Enter` (o `Alt+X`) para ejecutar todo el script
3. O haz clic en el botón ▶️ "Execute SQL Script" en la barra de herramientas

**Opción B: Ejecutar por secciones**
1. Selecciona una sección del script (por ejemplo, solo los índices de préstamos)
2. Presiona `Ctrl+Enter` para ejecutar solo la selección
3. Repite para cada sección

---

### 5. Verificar Resultados

Después de ejecutar, deberías ver:

**En la pestaña "Log" o "Output":**
```
CREATE INDEX
CREATE INDEX
CREATE INDEX
...
COMMIT
```

**Si hay errores:**
- Verás mensajes de error en rojo
- Revisa qué índice falló y por qué

---

### 6. Verificar que los Índices se Crearon

Ejecuta esta query en DBeaver para verificar:

```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname LIKE 'idx_%_dashboard%' 
   OR indexname LIKE 'idx_prestamos_%'
   OR indexname LIKE 'idx_cuotas_%'
   OR indexname LIKE 'idx_pagos_%'
ORDER BY tablename, indexname;
```

**Resultado esperado:** Deberías ver al menos 6 índices listados:
- `idx_prestamos_fecha_aprobacion_ym`
- `idx_cuotas_fecha_vencimiento_ym`
- `idx_cuotas_prestamo_fecha_vencimiento`
- `idx_prestamos_cedula_estado`
- `idx_prestamos_aprobacion_estado_analista`
- `idx_pagos_fecha_pago_activo`

---

## ⚠️ IMPORTANTE ANTES DE EJECUTAR

### 1. Verificar que NO Existen los Índices

Ejecuta primero esta query para ver si ya existen:

```sql
SELECT indexname 
FROM pg_indexes 
WHERE indexname IN (
    'idx_prestamos_fecha_aprobacion_ym',
    'idx_cuotas_fecha_vencimiento_ym',
    'idx_cuotas_prestamo_fecha_vencimiento',
    'idx_prestamos_cedula_estado',
    'idx_prestamos_aprobacion_estado_analista',
    'idx_pagos_fecha_pago_activo'
);
```

**Si ya existen:** El script usa `IF NOT EXISTS`, así que no habrá problema, pero es bueno saberlo.

### 2. Ejecutar en Horario de Bajo Tráfico

- Los índices pueden tardar varios minutos en crearse
- Pueden bloquear temporalmente las tablas
- Mejor ejecutar fuera de horario laboral o en mantenimiento

### 3. Verificar Espacio en Disco

Los índices ocupan espacio adicional. Verifica que tengas suficiente:

```sql
SELECT 
    pg_size_pretty(pg_database_size(current_database())) as tamaño_bd;
```

---

## 🔍 Verificar que los Índices Funcionen

Después de crear los índices, ejecuta esta query para verificar que PostgreSQL los use:

```sql
EXPLAIN ANALYZE 
SELECT 
    EXTRACT(YEAR FROM fecha_aprobacion),
    EXTRACT(MONTH FROM fecha_aprobacion),
    COUNT(*)
FROM prestamos
WHERE estado = 'APROBADO'
GROUP BY EXTRACT(YEAR FROM fecha_aprobacion), EXTRACT(MONTH FROM fecha_aprobacion);
```

**Resultado esperado:** Debe mostrar algo como:
```
Index Scan using idx_prestamos_fecha_aprobacion_ym on prestamos
```

Si ves `Seq Scan` en lugar de `Index Scan`, los índices no se están usando (puede necesitar `ANALYZE`).

---

## 🆘 Si Hay Errores

### Error: "functions in index expression must be marked IMMUTABLE"

**Solución:** Algunas versiones de PostgreSQL pueden tener problemas con `EXTRACT`. En ese caso, puedes usar índices regulares:

```sql
-- En lugar de índice funcional, crear índice regular
CREATE INDEX IF NOT EXISTS idx_prestamos_fecha_aprobacion 
ON prestamos (fecha_aprobacion, estado)
WHERE estado = 'APROBADO' AND fecha_aprobacion IS NOT NULL;
```

### Error: "relation already exists"

**Solución:** El índice ya existe. Esto está bien, el script usa `IF NOT EXISTS` para evitar este error.

### Error: "out of memory" o "timeout"

**Solución:** 
- Ejecutar índices uno por uno
- Ejecutar durante horario de menor tráfico
- Aumentar `work_mem` temporalmente:

```sql
SET work_mem = '256MB';
-- Ejecutar índice
-- Luego restaurar
RESET work_mem;
```

---

## ✅ Checklist de Ejecución

- [ ] DBeaver conectado a la base de datos correcta
- [ ] Script abierto en pestaña SQL
- [ ] Verificado que no hay errores de sintaxis
- [ ] Ejecutado script completo (`Ctrl+Enter`)
- [ ] Verificado que los índices se crearon (query de verificación)
- [ ] Verificado que los índices se usan (`EXPLAIN ANALYZE`)
- [ ] Sin errores en la ejecución

---

## 📊 Después de Ejecutar

1. **Probar endpoints optimizados** y verificar tiempos de respuesta
2. **Monitorear logs** para ver mejoras en rendimiento
3. **Comparar tiempos** antes/después de las optimizaciones

---

## 🎉 Resultado

Una vez ejecutado el script, tendrás:
- ✅ Índices creados y funcionando
- ✅ Queries del dashboard 3-5x más rápidas
- ✅ Menor carga en base de datos
- ✅ Mejor experiencia de usuario

