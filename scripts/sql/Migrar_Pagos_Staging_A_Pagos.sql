-- ============================================================================
-- MIGRACION: PAGOS_STAGING A PAGOS
-- Script para migrar pagos desde staging a la tabla principal
-- EJECUTAR CON PRECAUCIÓN - Revisar antes de ejecutar
-- ============================================================================

-- PASO 1: Verificar registros a migrar
SELECT 
    'PASO 1: Registros que se migraran' AS seccion;

SELECT 
    COUNT(*) AS total_registros_a_migrar,
    COUNT(DISTINCT cedula_cliente) AS clientes_unicos,
    COALESCE(SUM(monto_pagado), 0) AS monto_total
FROM pagos_staging ps
WHERE NOT EXISTS (
    SELECT 1 FROM pagos p 
    WHERE (
        ps.id = p.id 
        OR (
            ps.cedula_cliente = p.cedula_cliente 
            AND ps.monto_pagado = p.monto_pagado 
            AND ps.fecha_pago = p.fecha_pago
            AND (ps.prestamo_id = p.prestamo_id OR (ps.prestamo_id IS NULL AND p.prestamo_id IS NULL))
        )
    )
);

-- PASO 2: Ver muestra de registros a migrar
SELECT 
    'PASO 2: Muestra de registros a migrar (10 primeros)' AS seccion;

SELECT 
    ps.id,
    ps.cedula_cliente,
    ps.prestamo_id,
    ps.monto_pagado,
    ps.fecha_pago,
    ps.metodo_pago,
    ps.referencia_pago,
    ps.estado,
    ps.fecha_registro,
    ps.usuario_registro
FROM pagos_staging ps
WHERE NOT EXISTS (
    SELECT 1 FROM pagos p 
    WHERE (
        ps.id = p.id 
        OR (
            ps.cedula_cliente = p.cedula_cliente 
            AND ps.monto_pagado = p.monto_pagado 
            AND ps.fecha_pago = p.fecha_pago
            AND (ps.prestamo_id = p.prestamo_id OR (ps.prestamo_id IS NULL AND p.prestamo_id IS NULL))
        )
    )
)
ORDER BY ps.fecha_registro
LIMIT 10;

-- ============================================================================
-- PASO 3: MIGRACION (DESCOMENTAR PARA EJECUTAR)
-- ============================================================================

/*
-- IMPORTANTE: Revisar los resultados del PASO 1 y PASO 2 antes de ejecutar

-- Migrar pagos desde staging a pagos
INSERT INTO pagos (
    cedula_cliente,
    prestamo_id,
    monto_pagado,
    fecha_pago,
    metodo_pago,
    referencia_pago,
    estado,
    fecha_registro,
    usuario_registro
)
SELECT 
    ps.cedula_cliente,
    ps.prestamo_id,
    ps.monto_pagado,
    ps.fecha_pago,
    ps.metodo_pago,
    ps.referencia_pago,
    COALESCE(ps.estado, 'PAGADO') AS estado,
    COALESCE(ps.fecha_registro, CURRENT_TIMESTAMP) AS fecha_registro,
    COALESCE(ps.usuario_registro, 'sistema') AS usuario_registro
FROM pagos_staging ps
WHERE NOT EXISTS (
    SELECT 1 FROM pagos p 
    WHERE (
        ps.id = p.id 
        OR (
            ps.cedula_cliente = p.cedula_cliente 
            AND ps.monto_pagado = p.monto_pagado 
            AND ps.fecha_pago = p.fecha_pago
            AND (ps.prestamo_id = p.prestamo_id OR (ps.prestamo_id IS NULL AND p.prestamo_id IS NULL))
        )
    )
);

-- Después de migrar, se deben aplicar los pagos a las cuotas
-- Esto se hace automáticamente si el endpoint de crear_pago() llama a aplicar_pago_a_cuotas()
-- O manualmente ejecutando la lógica para cada pago migrado
*/

-- PASO 4: Verificar resultado de migracion
SELECT 
    'PASO 4: Verificar resultado (ejecutar después de migrar)' AS seccion;

SELECT 
    'Total en pagos_staging' AS metrica,
    COUNT(*)::VARCHAR AS valor
FROM pagos_staging

UNION ALL

SELECT 
    'Total en pagos',
    COUNT(*)::VARCHAR
FROM pagos

UNION ALL

SELECT 
    'Registros migrados',
    (
        SELECT COUNT(*)::VARCHAR
        FROM pagos p
        WHERE EXISTS (
            SELECT 1 FROM pagos_staging ps
            WHERE (
                ps.id = p.id 
                OR (
                    ps.cedula_cliente = p.cedula_cliente 
                    AND ps.monto_pagado = p.monto_pagado 
                    AND ps.fecha_pago = p.fecha_pago
                )
            )
        )
    );

-- NOTA IMPORTANTE:
-- Después de migrar los pagos, es necesario aplicar cada pago a las cuotas
-- Esto normalmente se hace automáticamente cuando se crea un pago a través de la API
-- Si se migran directamente a la BD, hay que ejecutar la lógica de aplicar_pago_a_cuotas()
-- para cada pago migrado o crear un script que lo haga

