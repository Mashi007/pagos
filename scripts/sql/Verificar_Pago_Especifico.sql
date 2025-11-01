-- ============================================================================
-- VERIFICAR PAGO ESPECIFICO Y POR QUE NO SE ACTUALIZO
-- Ejecutar para un prestamo_id o pago_id especifico
-- ============================================================================

-- Ejemplo: Verificar prestamo #61 (del ejemplo del usuario)
-- Cambiar el ID según sea necesario

-- PASO 1: Informacion del prestamo
SELECT 
    'PASO 1: Informacion del prestamo' AS seccion;

SELECT 
    id,
    cedula,
    estado,
    total_financiamiento,
    numero_cuotas,
    fecha_base_calculo,
    fecha_aprobacion
FROM prestamos
WHERE id = 61;

-- PASO 2: Pagos registrados para este prestamo
SELECT 
    'PASO 2: Pagos registrados para prestamo #61' AS seccion;

SELECT 
    id AS pago_id,
    cedula_cliente,
    prestamo_id,
    monto_pagado,
    fecha_pago,
    fecha_registro,
    estado AS estado_pago,
    usuario_registro
FROM pagos
WHERE prestamo_id = 61
ORDER BY fecha_pago DESC, fecha_registro DESC;

-- PASO 3: Cuotas del prestamo y su estado
SELECT 
    'PASO 3: Cuotas del prestamo y estado actual' AS seccion;

SELECT 
    id AS cuota_id,
    numero_cuota,
    fecha_vencimiento,
    monto_cuota,
    total_pagado,
    capital_pagado,
    interes_pagado,
    capital_pendiente,
    interes_pendiente,
    estado,
    fecha_pago,
    CASE 
        WHEN total_pagado >= monto_cuota AND estado = 'PAGADO' THEN 'OK (Correctamente pagada)'
        WHEN total_pagado >= monto_cuota AND estado != 'PAGADO' THEN 'ERROR (Deberia ser PAGADO)'
        WHEN total_pagado > 0 AND total_pagado < monto_cuota THEN 'Parcial'
        WHEN total_pagado = 0 THEN 'Sin pago'
        ELSE 'Verificar'
    END AS validacion
FROM cuotas
WHERE prestamo_id = 61
ORDER BY numero_cuota;

-- PASO 4: Comparacion pagos vs cuotas actualizadas
SELECT 
    'PASO 4: Comparacion pagos vs cuotas' AS seccion;

SELECT 
    'Total pagos registrados' AS metrica,
    COALESCE(SUM(monto_pagado), 0)::VARCHAR AS valor
FROM pagos
WHERE prestamo_id = 61

UNION ALL

SELECT 
    'Total aplicado en cuotas',
    COALESCE(SUM(total_pagado), 0)::VARCHAR
FROM cuotas
WHERE prestamo_id = 61

UNION ALL

SELECT 
    'Diferencia',
    (COALESCE((SELECT SUM(monto_pagado) FROM pagos WHERE prestamo_id = 61), 0) - 
     COALESCE((SELECT SUM(total_pagado) FROM cuotas WHERE prestamo_id = 61), 0))::VARCHAR,
    CASE 
        WHEN (COALESCE((SELECT SUM(monto_pagado) FROM pagos WHERE prestamo_id = 61), 0) - 
              COALESCE((SELECT SUM(total_pagado) FROM cuotas WHERE prestamo_id = 61), 0)) = 0
            THEN 'OK (Coinciden)'
        WHEN COALESCE((SELECT SUM(total_pagado) FROM cuotas WHERE prestamo_id = 61), 0) = 0
            THEN 'ERROR (No se aplicaron pagos)'
        ELSE 'PARCIAL (Diferencia)'
    END AS estado;

-- PASO 5: Si hay pagos pero no se aplicaron
SELECT 
    'PASO 5: Diagnostico de problema' AS seccion;

SELECT 
    CASE 
        WHEN COUNT(DISTINCT p.id) = 0 THEN 'NO HAY PAGOS REGISTRADOS'
        WHEN COUNT(DISTINCT c.id) = 0 THEN 'ERROR: PRESTAMO SIN CUOTAS GENERADAS'
        WHEN COALESCE(SUM(c.total_pagado), 0) = 0 AND COALESCE(SUM(p.monto_pagado), 0) > 0 
            THEN 'ERROR: PAGOS REGISTRADOS PERO NO APLICADOS A CUOTAS'
        WHEN COALESCE(SUM(c.total_pagado), 0) < COALESCE(SUM(p.monto_pagado), 0)
            THEN 'PARCIAL: NO TODO EL PAGO APLICADO'
        ELSE 'OK: PAGOS APLICADOS CORRECTAMENTE'
    END AS diagnostico,
    COUNT(DISTINCT p.id) AS cantidad_pagos,
    COUNT(DISTINCT c.id) AS cantidad_cuotas,
    COALESCE(SUM(p.monto_pagado), 0) AS total_pagado,
    COALESCE(SUM(c.total_pagado), 0) AS total_aplicado
FROM pagos p
FULL OUTER JOIN cuotas c ON p.prestamo_id = c.prestamo_id
WHERE (p.prestamo_id = 61 OR c.prestamo_id = 61);

