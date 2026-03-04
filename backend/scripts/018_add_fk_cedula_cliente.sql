-- Migration: 018_add_fk_cedula_cliente.sql
-- Propósito: Agregar FK constraint entre pagos.cedula_cliente → clientes.cedula
-- Requisito PREVIO: Ejecutar 017_audit_cedulas_huerfanas.sql y revisar resultados
-- ADVERTENCIA: Si hay cedulas huérfanas, fallarán al agregar FK. Ver paso 1.

-- ============================================================
-- PASO 1: LIMPIAR CEDULAS HUÉRFANAS (Opcional)
-- ============================================================
-- Descomenta si deseas eliminar pagos huérfanos automáticamente:
--
-- DELETE FROM public.pagos p
-- WHERE NOT EXISTS (
--     SELECT 1 FROM public.clientes c
--     WHERE c.cedula = p.cedula_cliente
-- ) AND p.cedula_cliente != '';
--
-- O si deseas ver cuántos sería (sin eliminar):
-- SELECT COUNT(*) as pagos_para_eliminar FROM public.pagos p
-- WHERE NOT EXISTS (
--     SELECT 1 FROM public.clientes c
--     WHERE c.cedula = p.cedula_cliente
-- ) AND p.cedula_cliente != '';

BEGIN;

-- PASO 2: Verificar integridad antes de agregar FK
DO $$
DECLARE
    huerfanos_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO huerfanos_count
    FROM public.pagos p
    WHERE NOT EXISTS (
        SELECT 1 FROM public.clientes c
        WHERE c.cedula = p.cedula_cliente
    ) AND p.cedula_cliente != '';
    
    IF huerfanos_count > 0 THEN
        RAISE EXCEPTION 'ERROR: Hay % pagos con cedulas huérfanas. Ejecutar 017_audit_cedulas_huerfanas.sql y limpiar antes de continuar.', huerfanos_count;
    END IF;
END $$;

-- PASO 3: Agregar FK constraint
ALTER TABLE public.pagos
ADD CONSTRAINT fk_pagos_cedula_cliente
FOREIGN KEY (cedula_cliente)
REFERENCES public.clientes(cedula)
ON DELETE SET NULL
ON UPDATE CASCADE;

-- PASO 4: Crear índice para mejorar performance de FK
CREATE INDEX IF NOT EXISTS idx_pagos_cedula_cliente ON public.pagos(cedula_cliente);

COMMIT;

-- ============================================================
-- VERIFICACIÓN POST-MIGRACIÓN
-- ============================================================
-- Ejecuta estas queries para confirmar que todo funcionó:

-- 1. Ver que FK existe
SELECT constraint_name, table_name, column_name
FROM information_schema.key_column_usage
WHERE table_name = 'pagos' AND constraint_name = 'fk_pagos_cedula_cliente';

-- 2. Ver que índice existe
SELECT indexname FROM pg_indexes
WHERE tablename = 'pagos' AND indexname = 'idx_pagos_cedula_cliente';

-- 3. Verificar que no hay cedulas huérfanas
SELECT COUNT(*) as cedulas_huerfanas
FROM public.pagos p
WHERE NOT EXISTS (
    SELECT 1 FROM public.clientes c
    WHERE c.cedula = p.cedula_cliente
);
-- Resultado esperado: 0
