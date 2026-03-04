# SQL Verification: UNIQUE Constraint en numero_documento

## Ejecución en BD Real

Copia y pega los comandos en tu cliente PostgreSQL para verificar que la BD está correctamente configurada.

---

## PASO 1: Verificar que existe el constraint UNIQUE

```sql
-- Ver todos los constraints en tabla pagos
SELECT
    constraint_name,
    constraint_type,
    table_name
FROM information_schema.table_constraints
WHERE table_name = 'pagos'
ORDER BY constraint_type DESC;

-- Resultado esperado:
-- ┌─────────────────────────────────┬─────────────────────┬────────┐
-- │ constraint_name                 │ constraint_type     │ table  │
-- ├─────────────────────────────────┼─────────────────────┼────────┤
-- │ pagos_pkey                      │ PRIMARY KEY         │ pagos  │
-- │ pagos_numero_documento_key      │ UNIQUE              │ pagos  │
-- │ fk_pagos_cedula                 │ FOREIGN KEY         │ pagos  │
-- │ chk_pagos_estado_valido         │ CHECK               │ pagos  │
-- └─────────────────────────────────┴─────────────────────┴────────┘
```

---

## PASO 2: Ver la definición del constraint UNIQUE

```sql
-- Ver definición exacta del constraint
SELECT
    conname as constraint_name,
    pg_get_constraintdef(oid) as definition
FROM pg_constraint
WHERE conrelid = (SELECT oid FROM pg_class WHERE relname = 'pagos')
  AND contype = 'u';

-- Resultado esperado:
-- ┌──────────────────────────────────┬────────────────────────────────────────┐
-- │ constraint_name                  │ definition                             │
-- ├──────────────────────────────────┼────────────────────────────────────────┤
-- │ pagos_numero_documento_key       │ UNIQUE (numero_documento)              │
-- └──────────────────────────────────┴────────────────────────────────────────┘
```

---

## PASO 3: Ver el índice creado

```sql
-- Los UNIQUE constraints crean índices automáticamente
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'pagos'
  AND indexname LIKE '%numero%';

-- Resultado esperado:
-- ┌──────────────────────────────────┬────────────────────────────────────────┐
-- │ indexname                        │ indexdef                               │
-- ├──────────────────────────────────┼────────────────────────────────────────┤
-- │ pagos_numero_documento_key       │ CREATE UNIQUE INDEX ... ON numero_documento
-- └──────────────────────────────────┴────────────────────────────────────────┘
```

---

## PASO 4: Verificar que NO hay duplicados existentes

```sql
-- Contar pagos duplicados (no debería haber)
SELECT
    COUNT(*) as total_pagos,
    COUNT(DISTINCT numero_documento) as documentos_unicos,
    COUNT(*) - COUNT(DISTINCT numero_documento) as DUPLICADOS_ENCONTRADOS
FROM public.pagos
WHERE numero_documento IS NOT NULL;

-- Resultado esperado:
-- ┌────────────┬─────────────────────┬───────────────────────────┐
-- │ total_pagos│ documentos_unicos    │ DUPLICADOS_ENCONTRADOS    │
-- ├────────────┼─────────────────────┼───────────────────────────┤
-- │ 1234       │ 1234                │ 0                         │
-- └────────────┴─────────────────────┴───────────────────────────┘

-- Si DUPLICADOS_ENCONTRADOS > 0, significa que hay datos duplicados
-- en la BD antes de implementar el constraint.
-- En ese caso, ejecuta la limpieza (ver PASO 5A)
```

---

## PASO 5A: Si hay duplicados existentes, limpiarlos

```sql
-- SOLO si el paso 4 mostró duplicados > 0

-- Ver cuáles son los duplicados
SELECT
    numero_documento,
    COUNT(*) as cantidad,
    STRING_AGG(id::text, ', ') as ids
FROM public.pagos
WHERE numero_documento IS NOT NULL
GROUP BY numero_documento
HAVING COUNT(*) > 1
ORDER BY cantidad DESC
LIMIT 20;

-- Crear tabla de backup
CREATE TABLE IF NOT EXISTS pagos_duplicados_backup AS
SELECT * FROM pagos
WHERE numero_documento IS NOT NULL
  AND numero_documento IN (
      SELECT numero_documento
      FROM pagos
      WHERE numero_documento IS NOT NULL
      GROUP BY numero_documento
      HAVING COUNT(*) > 1
  );

-- Eliminar duplicados (MANTENER el ID más antiguo)
DELETE FROM pagos
WHERE id NOT IN (
    SELECT DISTINCT ON (numero_documento) id
    FROM pagos
    WHERE numero_documento IS NOT NULL
    ORDER BY numero_documento, id ASC
)
AND numero_documento IS NOT NULL;

-- Verificar que se limpiaron
SELECT
    COUNT(*) as total_pagos,
    COUNT(DISTINCT numero_documento) as documentos_unicos
FROM public.pagos
WHERE numero_documento IS NOT NULL;
-- Ambos números deben ser iguales
```

---

## PASO 5B: Crear/Recrear el constraint si no existe

```sql
-- Si por alguna razón NO existe el constraint, ejecuta esto:

-- Primero, elimina el constraint si existe
ALTER TABLE public.pagos
DROP CONSTRAINT IF EXISTS pagos_numero_documento_key CASCADE;

-- Luego, créalo
ALTER TABLE public.pagos
ADD CONSTRAINT pagos_numero_documento_key UNIQUE (numero_documento);

-- Verificar que se creó
SELECT
    constraint_name,
    constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'pagos'
  AND constraint_type = 'UNIQUE';
```

---

## PASO 6: TEST - Intentar insertar documento duplicado

```sql
-- Este test DEBERÍA FALLAR con error de violación de constraint

BEGIN;

-- Insertar primer documento de prueba
INSERT INTO public.pagos (
    cedula,
    fecha_pago,
    monto_pagado,
    numero_documento,
    estado,
    referencia_pago,
    usuario_registro
) VALUES (
    'V99999999',
    NOW(),
    1000.00,
    'DOC_TEST_UNIQUE_001',
    'PENDIENTE',
    'TEST_UNIQUE',
    'test@example.com'
);

-- Obtener el ID
SELECT id FROM pagos WHERE numero_documento = 'DOC_TEST_UNIQUE_001' LIMIT 1;

-- Intentar insertar el MISMO documento (CON DIFERENTE CÉDULA/MONTO)
-- Este comando DEBE FALLAR
INSERT INTO public.pagos (
    cedula,
    fecha_pago,
    monto_pagado,
    numero_documento,
    estado,
    referencia_pago,
    usuario_registro
) VALUES (
    'V88888888',
    NOW(),
    2000.00,
    'DOC_TEST_UNIQUE_001',  -- DUPLICADO - DEBE FALLAR
    'PENDIENTE',
    'TEST_UNIQUE',
    'test@example.com'
);

-- ERROR ESPERADO:
-- ERROR: duplicate key value violates unique constraint "pagos_numero_documento_key"
-- Detail: Key (numero_documento)=(DOC_TEST_UNIQUE_001) already exists.

ROLLBACK;  -- Limpiar todos los cambios de prueba
```

---

## PASO 7: Verificar comportamiento con NULL

```sql
-- Los UNIQUE constraints permiten múltiples NULL
-- Esto es por diseño en PostgreSQL

BEGIN;

INSERT INTO public.pagos (cedula, fecha_pago, monto_pagado, estado, referencia_pago, numero_documento)
VALUES ('V11111111', NOW(), 100.00, 'PENDIENTE', 'REF1', NULL);

INSERT INTO public.pagos (cedula, fecha_pago, monto_pagado, estado, referencia_pago, numero_documento)
VALUES ('V22222222', NOW(), 200.00, 'PENDIENTE', 'REF2', NULL);

INSERT INTO public.pagos (cedula, fecha_pago, monto_pagado, estado, referencia_pago, numero_documento)
VALUES ('V33333333', NOW(), 300.00, 'PENDIENTE', 'REF3', NULL);

-- Los 3 anteriores deberían crearse SIN ERROR
-- Porque NULL es diferente de NULL en UNIQUE constraints

SELECT COUNT(*) as pagos_con_documento_null
FROM public.pagos
WHERE numero_documento IS NULL;

ROLLBACK;
```

---

## PASO 8: Verificar que la BD está funcional

```sql
-- Health check: Verificar que la tabla pagos existe y tiene datos
SELECT
    tablename as tabla,
    (SELECT COUNT(*) FROM pagos) as total_filas,
    (SELECT COUNT(DISTINCT prestamo_id) FROM pagos) as prestamos_unicos,
    (SELECT COUNT(DISTINCT cedula) FROM pagos) as cedulas_unicas,
    (SELECT COUNT(DISTINCT numero_documento) FROM pagos WHERE numero_documento IS NOT NULL) as documentos_unicos
FROM pg_tables
WHERE tablename = 'pagos';

-- Resultado: Si ves datos, BD está funcional
```

---

## 📊 Checklist de Verificación

Marca cada item después de ejecutar:

```
CONSTRAINT VERIFICATION:
☐ Paso 1: Constraint UNIQUE existe en información_schema
☐ Paso 2: pg_get_constraintdef muestra definición correcta
☐ Paso 3: Índice B-tree está creado
☐ Paso 4: No hay duplicados existentes (o fueron limpiados)
☐ Paso 5A: Si había duplicados, fueron respaldados y eliminados
☐ Paso 5B: Constraint está activo y funcional
☐ Paso 6: TEST FALLÓ al insertar duplicado (es lo esperado)
☐ Paso 7: NULL es permitido (funcionamiento correcto)
☐ Paso 8: BD está funcional y con datos

RESULTADO FINAL: ✅ INTEGRACIÓN BD VERIFICADA
```

---

## ✅ Resultado Final

Si todos los pasos pasaron:

✅ **BD está correctamente configurada** para rechazar duplicados  
✅ **Constraint UNIQUE está activo** en `numero_documento`  
✅ **Índice B-tree existe** para O(1) lookup  
✅ **No hay datos duplicados** en la tabla  
✅ **Sistema de validación Python está integrado**  
✅ **Defensa secundaria está en BD**  

**Conclusión**: Sistema de rechazo de duplicados está **COMPLETAMENTE INTEGRADO Y FUNCIONAL** ✅
