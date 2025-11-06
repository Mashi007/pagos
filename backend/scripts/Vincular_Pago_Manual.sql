-- ============================================================================
-- VINCULAR PAGO MANUALMENTE - UN PAGO A LA VEZ
-- Usar este script para vincular individualmente cada pago
-- ============================================================================

-- INSTRUCCIONES:
-- 1. Reemplazar [PAGO_ID] con el ID del pago
-- 2. Reemplazar [PRESTAMO_ID] con el ID del préstamo al que se debe vincular
-- 3. Ejecutar el UPDATE
-- 4. Ejecutar el SELECT de verificación

-- ============================================================================
-- PASO 1: Ver información del pago antes de vincular
-- ============================================================================

SELECT 
    'PASO 1: Informacion del pago antes de vincular' AS seccion;

SELECT 
    p.id AS pago_id,
    p.cedula_cliente,
    p.monto_pagado,
    TO_CHAR(p.fecha_pago, 'DD/MM/YYYY') AS fecha_pago,
    p.prestamo_id AS prestamo_id_actual,
    CASE 
        WHEN p.prestamo_id IS NULL THEN 'Sin vincular'
        ELSE 'Ya vinculado'
    END AS estado
FROM pagos p
WHERE p.id = [PAGO_ID];  -- Reemplazar [PAGO_ID]

-- ============================================================================
-- PASO 2: Ver préstamos disponibles para este cliente
-- ============================================================================

SELECT 
    'PASO 2: Prestamos disponibles para este cliente' AS seccion;

SELECT 
    pr.id AS prestamo_id,
    pr.cedula,
    pr.total_financiamiento,
    pr.numero_cuotas,
    TO_CHAR(pr.fecha_aprobacion, 'DD/MM/YYYY') AS fecha_aprobacion,
    pr.estado,
    COUNT(DISTINCT c.id) AS total_cuotas,
    COUNT(DISTINCT CASE WHEN c.estado = 'PENDIENTE' THEN c.id END) AS cuotas_pendientes,
    COUNT(DISTINCT CASE WHEN c.estado = 'PAGADO' THEN c.id END) AS cuotas_pagadas,
    COALESCE(SUM(CASE WHEN c.estado = 'PENDIENTE' THEN c.monto_cuota - c.total_pagado ELSE 0 END), 0) AS saldo_pendiente,
    CASE 
        WHEN COUNT(DISTINCT c.id) = 0 THEN 'SIN CUOTAS GENERADAS'
        WHEN COUNT(DISTINCT CASE WHEN c.estado = 'PENDIENTE' THEN c.id END) > 0 THEN 'TIENE CUOTAS PENDIENTES'
        ELSE 'TODAS LAS CUOTAS PAGADAS'
    END AS recomendacion
FROM prestamos pr
LEFT JOIN cuotas c ON pr.id = c.prestamo_id
WHERE pr.cedula = (SELECT cedula_cliente FROM pagos WHERE id = [PAGO_ID])  -- Reemplazar [PAGO_ID]
    AND pr.estado = 'APROBADO'
GROUP BY pr.id, pr.cedula, pr.total_financiamiento, pr.numero_cuotas, pr.fecha_aprobacion, pr.estado
ORDER BY pr.fecha_aprobacion DESC;

-- ============================================================================
-- PASO 3: ACTUALIZAR PAGO (DESCOMENTAR Y REEMPLAZAR [PRESTAMO_ID])
-- ============================================================================

/*
UPDATE pagos
SET prestamo_id = [PRESTAMO_ID]  -- Reemplazar [PRESTAMO_ID] con el ID del préstamo elegido
WHERE id = [PAGO_ID];  -- Reemplazar [PAGO_ID]
*/

-- ============================================================================
-- PASO 4: Verificar vinculación exitosa
-- ============================================================================

SELECT 
    'PASO 4: Verificacion despues de vincular' AS seccion;

SELECT 
    p.id AS pago_id,
    p.cedula_cliente,
    p.monto_pagado,
    p.prestamo_id,
    pr.total_financiamiento,
    pr.estado AS estado_prestamo,
    CASE 
        WHEN p.prestamo_id IS NOT NULL THEN 'OK: Vinculado'
        ELSE 'ERROR: No vinculado'
    END AS estado_vinculacion
FROM pagos p
LEFT JOIN prestamos pr ON p.prestamo_id = pr.id
WHERE p.id = [PAGO_ID];  -- Reemplazar [PAGO_ID]

-- ============================================================================
-- PASO 5: Aplicar pago a cuotas (usar endpoint API o script Python)
-- ============================================================================

SELECT 
    'PASO 5: Aplicar pago a cuotas' AS seccion;

SELECT 
    'Despues de vincular, usar el endpoint:' AS instruccion,
    CONCAT('POST /api/v1/pagos/', [PAGO_ID], '/aplicar-cuotas') AS endpoint_api,
    'O ejecutar el script Python: python scripts/python/Aplicar_Pagos_Pendientes.py' AS alternativa;

