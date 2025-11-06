-- ============================================
-- VERIFICACIÓN DETALLADA: ARTICULACIÓN PAGOS - PRESTAMOS
-- ============================================

-- ============================================
-- VERIFICACIÓN 1: ¿Existe Foreign Key en BD?
-- ============================================

SELECT 
    '=== VERIFICACIÓN 1: Foreign Key pagos.prestamo_id ===' AS verificacion,
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    CASE 
        WHEN tc.constraint_type = 'FOREIGN KEY' THEN '✅ Existe FK en BD'
        ELSE '❌ No existe FK'
    END AS estado
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
LEFT JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.table_name = 'pagos'
  AND kcu.column_name = 'prestamo_id'
  AND tc.table_schema = 'public';

-- ============================================
-- VERIFICACIÓN 2: Estado de prestamo_id en PAGOS
-- ============================================

SELECT 
    '=== VERIFICACIÓN 2: Estado de prestamo_id en PAGOS ===' AS verificacion,
    COUNT(*) AS total_pagos,
    COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END) AS pagos_con_prestamo_id,
    COUNT(CASE WHEN prestamo_id IS NULL THEN 1 END) AS pagos_sin_prestamo_id,
    ROUND(100.0 * COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END) / 
          NULLIF(COUNT(*), 0), 2) AS porcentaje_con_prestamo_id
FROM pagos;

-- ============================================
-- VERIFICACIÓN 3: Pagos con prestamo_id válido
-- ============================================

SELECT 
    '=== VERIFICACIÓN 3: Pagos con prestamo_id válido ===' AS verificacion,
    COUNT(*) AS total_pagos_con_prestamo_id,
    COUNT(CASE WHEN pr.id IS NOT NULL THEN 1 END) AS prestamo_id_valido,
    COUNT(CASE WHEN pr.id IS NULL THEN 1 END) AS prestamo_id_invalido,
    ROUND(100.0 * COUNT(CASE WHEN pr.id IS NOT NULL THEN 1 END) / 
          NULLIF(COUNT(*), 0), 2) AS porcentaje_valido
FROM pagos p
LEFT JOIN prestamos pr ON p.prestamo_id = pr.id
WHERE p.prestamo_id IS NOT NULL;

-- ============================================
-- VERIFICACIÓN 4: Concordancia cédula entre pagos y préstamos
-- ============================================

SELECT 
    '=== VERIFICACIÓN 4: Concordancia cédula pagos vs préstamos ===' AS verificacion,
    COUNT(*) AS pagos_con_prestamo_id,
    COUNT(CASE WHEN p.cedula_cliente = pr.cedula THEN 1 END) AS cedulas_coinciden,
    COUNT(CASE WHEN p.cedula_cliente != pr.cedula THEN 1 END) AS cedulas_no_coinciden,
    ROUND(100.0 * COUNT(CASE WHEN p.cedula_cliente = pr.cedula THEN 1 END) / 
          NULLIF(COUNT(*), 0), 2) AS porcentaje_coinciden
FROM pagos p
INNER JOIN prestamos pr ON p.prestamo_id = pr.id;

-- ============================================
-- VERIFICACIÓN 5: Pagos aplicados a cuotas
-- ============================================

SELECT 
    '=== VERIFICACIÓN 5: Pagos aplicados a cuotas ===' AS verificacion,
    COUNT(DISTINCT p.id) AS total_pagos_con_prestamo,
    COUNT(DISTINCT pc.pago_id) AS pagos_vinculados_a_cuotas,
    COUNT(DISTINCT c.id) AS cuotas_con_pagos_aplicados,
    COUNT(DISTINCT pr.id) AS prestamos_afectados,
    ROUND(100.0 * COUNT(DISTINCT pc.pago_id) / 
          NULLIF(COUNT(DISTINCT p.id), 0), 2) AS porcentaje_pagos_aplicados
FROM pagos p
LEFT JOIN prestamos pr ON p.prestamo_id = pr.id
LEFT JOIN pago_cuotas pc ON p.id = pc.pago_id
LEFT JOIN cuotas c ON pc.cuota_id = c.id
WHERE p.prestamo_id IS NOT NULL;

-- ============================================
-- VERIFICACIÓN 6: Resumen completo de articulación
-- ============================================

SELECT 
    '=== VERIFICACIÓN 6: Resumen Completo ===' AS verificacion,
    (SELECT COUNT(*) FROM prestamos) AS total_prestamos,
    (SELECT COUNT(*) FROM prestamos p INNER JOIN clientes c ON p.cliente_id = c.id) AS prestamos_articulados_cliente,
    (SELECT COUNT(*) FROM prestamos p INNER JOIN clientes c ON p.cedula = c.cedula) AS prestamos_articulados_cedula,
    (SELECT COUNT(DISTINCT prestamo_id) FROM cuotas) AS prestamos_con_cuotas,
    (SELECT COUNT(*) FROM pagos WHERE prestamo_id IS NOT NULL) AS pagos_con_prestamo_id,
    (SELECT COUNT(*) FROM pagos p INNER JOIN prestamos pr ON p.prestamo_id = pr.id 
     WHERE p.cedula_cliente = pr.cedula) AS pagos_con_cedula_coincidente,
    (SELECT COUNT(DISTINCT prestamo_id) FROM pagos WHERE prestamo_id IS NOT NULL) AS prestamos_con_pagos,
    (SELECT COUNT(DISTINCT pc.pago_id) FROM pago_cuotas pc) AS pagos_aplicados_a_cuotas,
    (SELECT COUNT(DISTINCT c.id) FROM cuotas c 
     WHERE EXISTS (SELECT 1 FROM pago_cuotas pc WHERE pc.cuota_id = c.id)) AS cuotas_con_pagos_aplicados;

