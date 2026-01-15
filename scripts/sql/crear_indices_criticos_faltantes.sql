-- ============================================================================
-- SCRIPT PARA CREAR ÍNDICES CRÍTICOS FALTANTES
-- ============================================================================
-- Fecha: 2026-01-15
-- Propósito: Crear índices críticos identificados en auditoría si no existen
-- IMPORTANTE: Ejecutar primero verificar_indices_criticos.sql para verificar estado
-- ============================================================================

-- ============================================================================
-- ÍNDICES CRÍTICOS - PRIORIDAD ALTA
-- ============================================================================

-- 1. Índice en clientes.cedula (si no existe)
-- Nota: Puede existir con nombre diferente si el modelo tiene index=True
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'clientes' 
        AND (indexname LIKE '%cedula%' OR indexdef LIKE '%cedula%')
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_clientes_cedula ON clientes(cedula);
        RAISE NOTICE 'Índice idx_clientes_cedula creado';
    ELSE
        RAISE NOTICE 'Índice en clientes.cedula ya existe';
    END IF;
END $$;

-- 2. Índice en prestamos.cliente_id (si no existe)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'prestamos' 
        AND (indexname LIKE '%cliente_id%' OR indexdef LIKE '%cliente_id%')
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_prestamos_cliente_id ON prestamos(cliente_id);
        RAISE NOTICE 'Índice idx_prestamos_cliente_id creado';
    ELSE
        RAISE NOTICE 'Índice en prestamos.cliente_id ya existe';
    END IF;
END $$;

-- 3. Índice en cuotas.prestamo_id (si no existe)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'cuotas' 
        AND (indexname LIKE '%prestamo_id%' OR indexdef LIKE '%prestamo_id%')
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_cuotas_prestamo_id ON cuotas(prestamo_id);
        RAISE NOTICE 'Índice idx_cuotas_prestamo_id creado';
    ELSE
        RAISE NOTICE 'Índice en cuotas.prestamo_id ya existe';
    END IF;
END $$;

-- 4. Índice en pagos.prestamo_id (si no existe)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'pagos' 
        AND (indexname LIKE '%prestamo_id%' OR indexdef LIKE '%prestamo_id%')
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_pagos_prestamo_id ON pagos(prestamo_id);
        RAISE NOTICE 'Índice idx_pagos_prestamo_id creado';
    ELSE
        RAISE NOTICE 'Índice en pagos.prestamo_id ya existe';
    END IF;
END $$;

-- ============================================================================
-- ÍNDICES COMPUESTOS ADICIONALES PARA OPTIMIZACIÓN
-- ============================================================================

-- 5. Índice compuesto para cuotas con filtros frecuentes
CREATE INDEX IF NOT EXISTS idx_cuotas_prestamo_estado_fecha 
ON cuotas(prestamo_id, estado, fecha_vencimiento)
WHERE fecha_vencimiento IS NOT NULL;

-- 6. Índice compuesto para prestamos con filtros frecuentes
CREATE INDEX IF NOT EXISTS idx_prestamos_cliente_estado 
ON prestamos(cliente_id, estado)
WHERE estado IN ('APROBADO', 'ACTIVO', 'PENDIENTE');

-- 7. Índice compuesto para pagos con filtros frecuentes
CREATE INDEX IF NOT EXISTS idx_pagos_prestamo_fecha_activo 
ON pagos(prestamo_id, fecha_pago, activo)
WHERE fecha_pago IS NOT NULL AND activo = TRUE;

-- ============================================================================
-- VERIFICACIÓN FINAL
-- ============================================================================

SELECT 
    'INDICES_CREADOS' as categoria,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname IN (
    'idx_clientes_cedula',
    'idx_prestamos_cliente_id',
    'idx_cuotas_prestamo_id',
    'idx_pagos_prestamo_id',
    'idx_cuotas_prestamo_estado_fecha',
    'idx_prestamos_cliente_estado',
    'idx_pagos_prestamo_fecha_activo'
)
ORDER BY tablename, indexname;

-- ============================================================================
-- NOTAS IMPORTANTES
-- ============================================================================
-- 1. Estos índices mejoran significativamente el rendimiento de:
--    - Búsquedas por cédula de cliente
--    - JOINs entre prestamos y clientes
--    - Consultas de cuotas por préstamo
--    - Consultas de pagos por préstamo
--
-- 2. Los índices compuestos optimizan queries que filtran por múltiples campos
--
-- 3. Los índices parciales (WHERE) reducen el tamaño del índice y mejoran
--    el rendimiento para queries que coinciden con la condición WHERE
--
-- 4. Verificar impacto en escritura: más índices = más tiempo en INSERT/UPDATE
--    pero mejor rendimiento en SELECT
-- ============================================================================
