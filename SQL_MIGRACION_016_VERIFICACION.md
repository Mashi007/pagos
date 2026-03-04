# SQL PARA EJECUTAR MIGRACIÓN 016 Y VERIFICAR

**Objetivo**: Crear tabla `cuota_pagos` para historial completo de pagos  
**Requiere**: PostgreSQL 12+ (ZoneInfo)  
**Tiempo estimado**: 2-5 minutos

---

## 📋 PASO 1: EJECUTAR MIGRACIÓN 016

### Opción A: Desde terminal (Recomendado)

```bash
# Conectarse a la BD y ejecutar el archivo
psql $DATABASE_URL < backend/scripts/016_crear_tabla_cuota_pagos.sql

# Verificar que se ejecutó sin errores (debería decir "BEGIN" y "COMMIT")
```

### Opción B: Desde cliente SQL (pgAdmin, DBeaver)

**Copiar y pegar TODO esto**:

```sql
-- ============================================================
-- Migration: 016_crear_tabla_cuota_pagos.sql
-- ============================================================
-- Propósito: Crear tabla join cuota_pagos para historial completo de pagos por cuota
-- Razón: Actual pago_id en cuota solo guarda el ÚLTIMO pago; se pierden pagos parciales
-- Solución: cuota_pagos registra TODOS los pagos aplicados a cada cuota con monto y orden FIFO

BEGIN;

-- 1. Crear tabla cuota_pagos
CREATE TABLE IF NOT EXISTS public.cuota_pagos (
    id BIGSERIAL PRIMARY KEY,
    cuota_id INTEGER NOT NULL,
    pago_id INTEGER NOT NULL,
    monto_aplicado NUMERIC(14, 2) NOT NULL,
    fecha_aplicacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    orden_aplicacion INTEGER NOT NULL DEFAULT 0,
    es_pago_completo BOOLEAN NOT NULL DEFAULT FALSE,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cuota_id) REFERENCES public.cuotas(id) ON DELETE CASCADE,
    FOREIGN KEY (pago_id) REFERENCES public.pagos(id) ON DELETE CASCADE
);

-- 2. Índices para queries comunes
CREATE INDEX IF NOT EXISTS idx_cuota_pagos_cuota_id ON public.cuota_pagos(cuota_id);
CREATE INDEX IF NOT EXISTS idx_cuota_pagos_pago_id ON public.cuota_pagos(pago_id);
CREATE INDEX IF NOT EXISTS idx_cuota_pagos_fecha ON public.cuota_pagos(fecha_aplicacion);

-- 3. Índice único para prevenir duplicados (mismo pago aplicado 2x a misma cuota)
CREATE UNIQUE INDEX IF NOT EXISTS uq_cuota_pagos_cuota_pago ON public.cuota_pagos(cuota_id, pago_id);

-- 4. Migración de datos existentes: Convertir pago_id existentes en cuota_pagos
-- (Solo si hay datos en cuotas con pago_id no NULL)
INSERT INTO public.cuota_pagos (cuota_id, pago_id, monto_aplicado, fecha_aplicacion, es_pago_completo, creado_en)
SELECT 
    c.id as cuota_id,
    c.pago_id,
    c.total_pagado as monto_aplicado,
    COALESCE(c.fecha_pago, CURRENT_TIMESTAMP) as fecha_aplicacion,
    (c.total_pagado >= c.monto_cuota - 0.01) as es_pago_completo,
    COALESCE(c.creado_en, CURRENT_TIMESTAMP) as creado_en
FROM public.cuotas c
WHERE c.pago_id IS NOT NULL
ON CONFLICT (cuota_id, pago_id) DO NOTHING;

COMMIT;
```

**Resultado esperado**:
```
BEGIN
CREATE TABLE
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE UNIQUE INDEX
INSERT 0 X  (donde X = número de registros migrados)
COMMIT
```

---

## ✅ PASO 2: VERIFICAR QUE TODO FUNCIONÓ

### Test 1: ¿Existe la tabla?

```sql
-- Debería retornar 1 fila
SELECT EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'cuota_pagos'
);

-- Resultado esperado:
-- | exists |
-- |--------|
-- | t      |  ✅ (t = true)
```

### Test 2: ¿Tiene los índices?

```sql
-- Debería retornar 4 índices
SELECT 
    indexname, 
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
AND tablename = 'cuota_pagos'
ORDER BY indexname;

-- Resultado esperado:
-- | indexname                        | indexdef                                               |
-- |----------------------------------|-------------------------------------------------------|
-- | idx_cuota_pagos_cuota_id        | CREATE INDEX idx_cuota_pagos_cuota_id ON cuota_pagos |
-- | idx_cuota_pagos_fecha           | CREATE INDEX idx_cuota_pagos_fecha ON cuota_pagos    |
-- | idx_cuota_pagos_pago_id         | CREATE INDEX idx_cuota_pagos_pago_id ON cuota_pagos  |
-- | uq_cuota_pagos_cuota_pago       | CREATE UNIQUE INDEX uq_cuota_pagos_cuota_pago ...    |
```

### Test 3: ¿Tiene columnas correctas?

```sql
-- Debería retornar 9 columnas
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'cuota_pagos'
ORDER BY ordinal_position;

-- Resultado esperado:
-- | column_name      | data_type           | is_nullable |
-- |------------------|---------------------|-------------|
-- | id               | bigint              | NO          |
-- | cuota_id         | integer             | NO          |
-- | pago_id          | integer             | NO          |
-- | monto_aplicado   | numeric             | NO          |
-- | fecha_aplicacion | timestamp           | YES         |
-- | orden_aplicacion | integer             | NO          |
-- | es_pago_completo | boolean             | NO          |
-- | creado_en        | timestamp           | YES         |
-- | actualizado_en   | timestamp           | YES         |
```

### Test 4: ¿Se migraron los datos existentes?

```sql
-- Cuántos registros se migraron desde cuotas con pago_id
SELECT COUNT(*) as total_registros_migrados
FROM public.cuota_pagos;

-- Compara con:
SELECT COUNT(*) as cuotas_con_pago
FROM public.cuotas
WHERE pago_id IS NOT NULL;

-- Si son iguales = ✅ Migración correcta
```

### Test 5: ¿Funcionan las FKs?

```sql
-- Intentar insertar con cuota_id inválida (debe fallar)
INSERT INTO public.cuota_pagos (cuota_id, pago_id, monto_aplicado, es_pago_completo)
VALUES (999999, 1, 100.00, false);

-- Resultado esperado:
-- ERROR:  insert or update on table "cuota_pagos" violates foreign key constraint "cuota_pagos_cuota_id_fkey"
```

### Test 6: ¿Previene duplicados?

```sql
-- Intentar insertar el mismo cuota_id + pago_id (debe fallar)
INSERT INTO public.cuota_pagos (cuota_id, pago_id, monto_aplicado, es_pago_completo)
SELECT c.cuota_id, c.pago_id, c.monto_aplicado, c.es_pago_completo
FROM public.cuota_pagos c
LIMIT 1;

-- Resultado esperado:
-- ERROR:  duplicate key value violates unique constraint "uq_cuota_pagos_cuota_pago"
```

---

## 📊 PASO 3: QUERIES DE PRUEBA (Si quieres ver datos)

### Query 1: Ver historial de pagos de una cuota

```sql
-- Reemplaza 1 con un ID real de cuota
SELECT 
    cp.id,
    cp.cuota_id,
    cp.pago_id,
    cp.monto_aplicado,
    cp.fecha_aplicacion,
    cp.orden_aplicacion,
    cp.es_pago_completo,
    p.numero_documento,
    p.cedula_cliente
FROM public.cuota_pagos cp
JOIN public.pagos p ON cp.pago_id = p.id
WHERE cp.cuota_id = 1
ORDER BY cp.orden_aplicacion ASC;

-- Resultado: Lista TODOS los pagos que tocaron esa cuota (en orden FIFO)
```

### Query 2: Ver suma de pagos por cuota (debe coincidir con total_pagado)

```sql
-- Verificar que monto_aplicado suma correctamente
SELECT 
    cp.cuota_id,
    SUM(cp.monto_aplicado) as suma_pagos,
    c.total_pagado,
    CASE 
        WHEN SUM(cp.monto_aplicado)::NUMERIC(14,2) = c.total_pagado 
        THEN '✅ Coincide'
        ELSE '❌ NO coincide'
    END as validacion
FROM public.cuota_pagos cp
JOIN public.cuotas c ON cp.cuota_id = c.id
GROUP BY cp.cuota_id, c.total_pagado
HAVING SUM(cp.monto_aplicado)::NUMERIC(14,2) != c.total_pagado  -- Solo mostrar incongruencias
LIMIT 10;

-- Si no retorna filas = ✅ Todo coincide perfectamente
```

### Query 3: Ver cuotas con múltiples pagos (pagos parciales)

```sql
-- Cuotas que recibieron más de un pago
SELECT 
    c.id as cuota_id,
    c.numero_cuota,
    c.monto as monto_cuota,
    c.total_pagado,
    COUNT(cp.id) as cantidad_pagos,
    STRING_AGG(DISTINCT cp.pago_id::text, ', ') as pagos_ids
FROM public.cuotas c
LEFT JOIN public.cuota_pagos cp ON c.id = cp.cuota_id
WHERE c.pago_id IS NOT NULL
GROUP BY c.id, c.numero_cuota, c.monto, c.total_pagado
HAVING COUNT(cp.id) > 1
ORDER BY COUNT(cp.id) DESC
LIMIT 10;

-- Resultado: Cuotas con historial de múltiples pagos parciales
```

### Query 4: Ver estadísticas de tabla

```sql
-- Stats generales
SELECT 
    'cuota_pagos' as tabla,
    (SELECT COUNT(*) FROM public.cuota_pagos) as total_registros,
    (SELECT COUNT(DISTINCT cuota_id) FROM public.cuota_pagos) as cuotas_unicas,
    (SELECT COUNT(DISTINCT pago_id) FROM public.cuota_pagos) as pagos_unicos,
    (SELECT MIN(fecha_aplicacion) FROM public.cuota_pagos) as fecha_primer_pago,
    (SELECT MAX(fecha_aplicacion) FROM public.cuota_pagos) as fecha_ultimo_pago;

-- Resultado: Resumen de actividad
```

---

## 🚨 SI HAY ERRORES

### Error 1: "relation "cuota_pagos" already exists"
```
❌ Problema: Tabla ya existe
✅ Solución: Es normal si ya la creaste antes, puedes ignorar
```

### Error 2: "duplicate key value violates unique constraint"
```
❌ Problema: Ya hay datos duplicados en cuota_pagos
✅ Solución: Ejecutar limpieza:

DELETE FROM public.cuota_pagos
WHERE (cuota_id, pago_id) NOT IN (
    SELECT cuota_id, pago_id
    FROM public.cuota_pagos
    ORDER BY cuota_id, pago_id, creado_en
    LIMIT 1
);
```

### Error 3: "FOREIGN KEY constraint ... referenced in public.cuotas"
```
❌ Problema: FK falló porque referencia a cuota inexistente
✅ Solución: Ejecutar en modo permisivo:

SET CONSTRAINTS ALL DEFERRED;
[Ejecutar migración]
SET CONSTRAINTS ALL IMMEDIATE;
```

### Error 4: "permission denied for schema public"
```
❌ Problema: Usuario sin permisos
✅ Solución: Ejecutar con usuario con permisos (superuser)
```

---

## ✨ SCRIPT COMPLETO (Copiar y pegar TODO)

Si quieres ejecutar verificación completa:

```sql
-- ============================================================
-- MIGRACIÓN 016 + VERIFICACIONES COMPLETAS
-- ============================================================

-- PASO 1: Ejecutar migración
BEGIN;

CREATE TABLE IF NOT EXISTS public.cuota_pagos (
    id BIGSERIAL PRIMARY KEY,
    cuota_id INTEGER NOT NULL,
    pago_id INTEGER NOT NULL,
    monto_aplicado NUMERIC(14, 2) NOT NULL,
    fecha_aplicacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    orden_aplicacion INTEGER NOT NULL DEFAULT 0,
    es_pago_completo BOOLEAN NOT NULL DEFAULT FALSE,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cuota_id) REFERENCES public.cuotas(id) ON DELETE CASCADE,
    FOREIGN KEY (pago_id) REFERENCES public.pagos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cuota_pagos_cuota_id ON public.cuota_pagos(cuota_id);
CREATE INDEX IF NOT EXISTS idx_cuota_pagos_pago_id ON public.cuota_pagos(pago_id);
CREATE INDEX IF NOT EXISTS idx_cuota_pagos_fecha ON public.cuota_pagos(fecha_aplicacion);
CREATE UNIQUE INDEX IF NOT EXISTS uq_cuota_pagos_cuota_pago ON public.cuota_pagos(cuota_id, pago_id);

INSERT INTO public.cuota_pagos (cuota_id, pago_id, monto_aplicado, fecha_aplicacion, es_pago_completo, creado_en)
SELECT 
    c.id as cuota_id,
    c.pago_id,
    c.total_pagado as monto_aplicado,
    COALESCE(c.fecha_pago, CURRENT_TIMESTAMP) as fecha_aplicacion,
    (c.total_pagado >= c.monto_cuota - 0.01) as es_pago_completo,
    COALESCE(c.creado_en, CURRENT_TIMESTAMP) as creado_en
FROM public.cuotas c
WHERE c.pago_id IS NOT NULL
ON CONFLICT (cuota_id, pago_id) DO NOTHING;

COMMIT;

-- PASO 2: Verificaciones
SELECT '✅ Tabla creada' as resultado WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'cuota_pagos'
);

SELECT 'Registros migrados:' as status, COUNT(*) FROM public.cuota_pagos;

SELECT 'Índices creados:' as status, COUNT(*) FROM pg_indexes 
WHERE schemaname = 'public' AND tablename = 'cuota_pagos';

-- PASO 3: Historial de una cuota (si existen datos)
SELECT 
    'Historial de cuota #' || cp.cuota_id as info,
    COUNT(*) as cantidad_pagos,
    SUM(cp.monto_aplicado) as total_aplicado
FROM public.cuota_pagos cp
GROUP BY cp.cuota_id
LIMIT 5;
```

---

## 📝 RESUMEN

| Paso | Comando | Resultado esperado |
|------|---------|-------------------|
| 1 | `psql $DATABASE_URL < backend/scripts/016_crear_tabla_cuota_pagos.sql` | COMMIT (sin errores) |
| 2 | `SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'cuota_pagos')` | `t` (true) |
| 3 | `SELECT COUNT(*) FROM pg_indexes WHERE tablename = 'cuota_pagos'` | `4` (4 índices) |
| 4 | `SELECT COUNT(*) FROM public.cuota_pagos` | N > 0 (datos migrados) |
| 5 | `SELECT COUNT(*) FROM public.cuotas WHERE pago_id IS NOT NULL` | Mismo N que paso 4 |

✅ Si todos pasan = **Migración exitosa**

---

**¿Ya la ejecutaste? Dame la salida o ejecuta el script completo de verificación ↑**
