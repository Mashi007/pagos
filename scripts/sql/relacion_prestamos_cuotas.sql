-- ======================================================================
-- RELACION ENTRE TABLAS PRESTAMOS Y CUOTAS
-- ======================================================================
-- Este script muestra la relación entre las tablas prestamos y cuotas
-- ======================================================================

-- ======================================================================
-- 1. ESTRUCTURA DE LA RELACION
-- ======================================================================

-- Verificar Foreign Key entre cuotas y prestamos
SELECT 
    tc.table_name AS tabla_hija,
    kcu.column_name AS columna_fk,
    ccu.table_name AS tabla_padre,
    ccu.column_name AS columna_pk,
    tc.constraint_name AS nombre_fk
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name = 'cuotas'
    AND ccu.table_name = 'prestamos';

-- ======================================================================
-- 2. RESUMEN DE LA RELACION
-- ======================================================================

SELECT 
    'RESUMEN RELACION' AS tipo,
    COUNT(DISTINCT p.id) AS total_prestamos,
    COUNT(DISTINCT c.id) AS total_cuotas,
    COUNT(DISTINCT c.prestamo_id) AS prestamos_con_cuotas,
    COUNT(DISTINCT p.id) - COUNT(DISTINCT c.prestamo_id) AS prestamos_sin_cuotas,
    ROUND(AVG(cuotas_por_prestamo.cuotas_count), 2) AS promedio_cuotas_por_prestamo,
    MIN(cuotas_por_prestamo.cuotas_count) AS minimo_cuotas,
    MAX(cuotas_por_prestamo.cuotas_count) AS maximo_cuotas
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
LEFT JOIN (
    SELECT prestamo_id, COUNT(*) AS cuotas_count
    FROM cuotas
    GROUP BY prestamo_id
) cuotas_por_prestamo ON p.id = cuotas_por_prestamo.prestamo_id;

-- ======================================================================
-- 3. VERIFICAR INTEGRIDAD REFERENCIAL
-- ======================================================================

-- Cuotas sin préstamo válido (huérfanas)
SELECT 
    'CUOTAS HUERFANAS' AS tipo,
    c.id AS cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    c.fecha_vencimiento
FROM cuotas c
LEFT JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.id IS NULL;

-- Préstamos sin cuotas
SELECT 
    'PRESTAMOS SIN CUOTAS' AS tipo,
    p.id AS prestamo_id,
    p.cedula,
    p.nombres,
    p.numero_cuotas AS cuotas_planificadas,
    p.estado,
    p.fecha_base_calculo
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE c.id IS NULL
  AND p.estado = 'APROBADO'
ORDER BY p.id;

-- ======================================================================
-- 4. VERIFICAR CONSISTENCIA: CUOTAS GENERADAS VS PLANIFICADAS
-- ======================================================================

SELECT 
    'CONSISTENCIA CUOTAS' AS tipo,
    p.id AS prestamo_id,
    p.cedula,
    p.nombres,
    p.numero_cuotas AS cuotas_planificadas,
    COUNT(c.id) AS cuotas_generadas,
    CASE 
        WHEN COUNT(c.id) = p.numero_cuotas THEN 'OK'
        WHEN COUNT(c.id) < p.numero_cuotas THEN 'FALTAN CUOTAS'
        WHEN COUNT(c.id) > p.numero_cuotas THEN 'CUOTAS DE MAS'
        WHEN COUNT(c.id) IS NULL THEN 'SIN CUOTAS'
    END AS estado
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, p.nombres, p.numero_cuotas
HAVING COUNT(c.id) != p.numero_cuotas OR COUNT(c.id) IS NULL
ORDER BY ABS(COALESCE(COUNT(c.id), 0) - p.numero_cuotas) DESC, p.id
LIMIT 20;

-- ======================================================================
-- 5. ESTADISTICAS DE LA RELACION
-- ======================================================================

SELECT 
    'ESTADISTICAS' AS tipo,
    COUNT(DISTINCT p.id) AS total_prestamos,
    COUNT(DISTINCT c.prestamo_id) AS prestamos_con_cuotas,
    COUNT(c.id) AS total_cuotas,
    COUNT(DISTINCT CASE WHEN c.total_pagado > 0 THEN c.prestamo_id END) AS prestamos_con_pagos,
    COUNT(CASE WHEN c.total_pagado > 0 THEN 1 END) AS cuotas_pagadas,
    COUNT(CASE WHEN c.total_pagado = 0 THEN 1 END) AS cuotas_pendientes
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.estado = 'APROBADO';

-- ======================================================================
-- 6. EJEMPLO DE RELACION: VER UN PRESTAMO Y SUS CUOTAS
-- ======================================================================

-- Ejemplo: Ver préstamo con ID 1 y todas sus cuotas
SELECT 
    'EJEMPLO PRESTAMO' AS tipo,
    p.id AS prestamo_id,
    p.cedula,
    p.nombres,
    p.numero_cuotas AS cuotas_planificadas,
    p.total_financiamiento,
    p.modalidad_pago,
    COUNT(c.id) AS cuotas_generadas
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.id = 1
GROUP BY p.id, p.cedula, p.nombres, p.numero_cuotas, p.total_financiamiento, p.modalidad_pago;

-- Ver todas las cuotas de ese préstamo
SELECT 
    c.id AS cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.monto_cuota,
    c.total_pagado,
    c.estado
FROM cuotas c
WHERE c.prestamo_id = 1
ORDER BY c.numero_cuota;

-- ======================================================================
-- NOTAS SOBRE LA RELACION:
-- ======================================================================
-- 1. RELACION PRINCIPAL:
--    - cuotas.prestamo_id → prestamos.id (Foreign Key)
--    - Tipo: Uno a Muchos (1 prestamo → N cuotas)
--
-- 2. INTEGRIDAD REFERENCIAL:
--    - Cada cuota DEBE tener un prestamo_id válido
--    - Si se elimina un préstamo, las cuotas asociadas deberían eliminarse (CASCADE)
--
-- 3. CAMPOS RELACIONADOS:
--    - prestamos.numero_cuotas: Número de cuotas planificadas
--    - cuotas.numero_cuota: Número de cuota (1, 2, 3, ...)
--    - prestamos.fecha_base_calculo: Fecha base para calcular fechas de vencimiento
--    - cuotas.fecha_vencimiento: Fecha calculada desde fecha_base_calculo
--
-- 4. CONSISTENCIA:
--    - COUNT(cuotas) por prestamo_id DEBE ser igual a prestamos.numero_cuotas
--    - Todas las cuotas deben tener numero_cuota único por préstamo (1, 2, 3, ...)
-- ======================================================================
