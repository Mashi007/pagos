-- ============================================
-- VERIFICACIÓN COMPLETA: MÓDULO PRÉSTAMOS
-- Ejecutar en DBeaver para verificar configuración
-- ============================================

-- ============================================
-- 1. ESTRUCTURA DE LA TABLA PRESTAMOS
-- ============================================
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'prestamos'
ORDER BY ordinal_position;

-- ============================================
-- 2. ÍNDICES Y CONSTRAINTS
-- ============================================
SELECT 
    t.relname AS tabla,
    i.relname AS indice,
    a.attname AS columna,
    ix.indisunique AS es_unico,
    ix.indisprimary AS es_primaria
FROM pg_class t
JOIN pg_index ix ON t.oid = ix.indrelid
JOIN pg_class i ON i.oid = ix.indexrelid
LEFT JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
WHERE t.relname = 'prestamos'
  AND t.relkind = 'r'
ORDER BY i.relname;

-- Constraints (Foreign Keys, Primary Keys, Checks)
SELECT
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
LEFT JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.table_name = 'prestamos'
  AND tc.table_schema = 'public'
ORDER BY tc.constraint_type, tc.constraint_name;

-- ============================================
-- 3. RELACIONES CON OTRAS TABLAS
-- ============================================
-- 3.1 Verificar relación con CLIENTES
SELECT 
    'Relación con CLIENTES' AS tipo_relacion,
    COUNT(DISTINCT p.cliente_id) AS prestamos_con_cliente_id,
    COUNT(DISTINCT c.id) AS clientes_existentes,
    COUNT(DISTINCT CASE WHEN c.id IS NULL THEN p.cliente_id END) AS prestamos_sin_cliente
FROM prestamos p
LEFT JOIN clientes c ON p.cliente_id = c.id;

-- 3.2 Verificar relación con CEDULA
SELECT 
    'Relación por CEDULA' AS tipo_relacion,
    COUNT(DISTINCT p.cedula) AS cedulas_distintas_prestamos,
    COUNT(DISTINCT c.cedula) AS cedulas_distintas_clientes,
    COUNT(DISTINCT CASE WHEN c.cedula IS NULL THEN p.cedula END) AS cedulas_prestamos_sin_cliente
FROM prestamos p
LEFT JOIN clientes c ON UPPER(TRIM(p.cedula)) = UPPER(TRIM(c.cedula));

-- 3.3 Verificar relación con CUOTAS (amortización)
SELECT 
    'Relación con CUOTAS' AS tipo_relacion,
    COUNT(DISTINCT p.id) AS prestamos_totales,
    COUNT(DISTINCT c.prestamo_id) AS prestamos_con_cuotas,
    COUNT(DISTINCT CASE WHEN c.prestamo_id IS NULL THEN p.id END) AS prestamos_sin_cuotas,
    COUNT(c.id) AS total_cuotas
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id;

-- 3.4 Verificar relación con PAGOS
SELECT 
    'Relación con PAGOS' AS tipo_relacion,
    COUNT(DISTINCT p.id) AS prestamos_totales,
    COUNT(DISTINCT pg.prestamo_id) AS prestamos_con_pagos,
    COUNT(DISTINCT CASE WHEN pg.prestamo_id IS NULL THEN p.id END) AS prestamos_sin_pagos,
    COUNT(pg.id) AS total_pagos
FROM prestamos p
LEFT JOIN pagos pg ON p.id = pg.prestamo_id;

-- ============================================
-- 4. ESTADOS Y DATOS BÁSICOS
-- ============================================
-- 4.1 Conteo por estado
SELECT 
    estado,
    COUNT(*) AS cantidad,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS porcentaje,
    SUM(total_financiamiento) AS total_financiado,
    AVG(total_financiamiento) AS promedio_monto
FROM prestamos
GROUP BY estado
ORDER BY cantidad DESC;

-- 4.2 Modalidades de pago
SELECT 
    modalidad_pago,
    COUNT(*) AS cantidad,
    AVG(numero_cuotas) AS promedio_cuotas,
    AVG(cuota_periodo) AS promedio_cuota_periodo
FROM prestamos
GROUP BY modalidad_pago
ORDER BY cantidad DESC;

-- 4.3 Prestamos con fecha_base_calculo (requerida para generar cuotas)
SELECT 
    'Fecha Base Cálculo' AS verificación,
    COUNT(*) AS total_prestamos,
    COUNT(fecha_base_calculo) AS con_fecha_base,
    COUNT(*) - COUNT(fecha_base_calculo) AS sin_fecha_base,
    COUNT(CASE WHEN estado = 'APROBADO' AND fecha_base_calculo IS NULL THEN 1 END) AS aprobados_sin_fecha
FROM prestamos;

-- ============================================
-- 5. INTEGRIDAD DE DATOS
-- ============================================
-- 5.1 Prestamos sin cliente_id válido
SELECT 
    'Prestamos sin cliente_id válido' AS problema,
    p.id,
    p.cedula,
    p.nombres,
    p.cliente_id,
    p.estado
FROM prestamos p
LEFT JOIN clientes c ON p.cliente_id = c.id
WHERE c.id IS NULL
LIMIT 10;

-- 5.2 Prestamos con cedula pero sin coincidencia en clientes
SELECT 
    'Prestamos con cedula sin coincidencia' AS problema,
    p.id,
    p.cedula AS cedula_prestamo,
    p.nombres AS nombres_prestamo,
    p.estado
FROM prestamos p
WHERE NOT EXISTS (
    SELECT 1 FROM clientes c 
    WHERE UPPER(TRIM(c.cedula)) = UPPER(TRIM(p.cedula))
)
LIMIT 10;

-- 5.3 Prestamos aprobados sin cuotas generadas
SELECT 
    'Prestamos aprobados sin cuotas' AS problema,
    p.id,
    p.cedula,
    p.nombres,
    p.estado,
    p.fecha_base_calculo,
    p.numero_cuotas,
    COUNT(c.id) AS cuotas_existentes
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, p.nombres, p.estado, p.fecha_base_calculo, p.numero_cuotas
HAVING COUNT(c.id) = 0
LIMIT 10;

-- 5.4 Prestamos con número de cuotas inconsistente
SELECT 
    'Inconsistencia cuotas' AS problema,
    p.id,
    p.cedula,
    p.numero_cuotas AS cuotas_esperadas,
    COUNT(c.id) AS cuotas_reales,
    ABS(p.numero_cuotas - COUNT(c.id)) AS diferencia
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
GROUP BY p.id, p.cedula, p.numero_cuotas
HAVING ABS(p.numero_cuotas - COUNT(c.id)) > 0
LIMIT 10;

-- ============================================
-- 6. VERIFICAR DATOS DE EJEMPLO
-- ============================================
-- 6.1 Últimos 5 préstamos creados
SELECT 
    p.id,
    p.cedula,
    p.nombres,
    p.estado,
    p.total_financiamiento,
    p.modalidad_pago,
    p.numero_cuotas,
    p.cuota_periodo,
    p.fecha_base_calculo,
    p.fecha_registro,
    p.fecha_aprobacion,
    c.id AS cliente_id_existe,
    (SELECT COUNT(*) FROM cuotas WHERE prestamo_id = p.id) AS total_cuotas,
    (SELECT COUNT(*) FROM pagos WHERE prestamo_id = p.id) AS total_pagos
FROM prestamos p
LEFT JOIN clientes c ON p.cliente_id = c.id
ORDER BY p.fecha_registro DESC
LIMIT 5;

-- 6.2 Prestamo con más detalles (primer préstamo aprobado con cuotas)
SELECT 
    p.id AS prestamo_id,
    p.cedula,
    p.nombres,
    p.estado,
    p.total_financiamiento,
    p.modalidad_pago,
    p.numero_cuotas,
    p.cuota_periodo,
    p.fecha_base_calculo,
    p.tasa_interes,
    p.usuario_proponente,
    p.usuario_aprobador,
    COUNT(DISTINCT c.id) AS total_cuotas,
    COUNT(DISTINCT pg.id) AS total_pagos,
    SUM(c.total_pagado) AS total_pagado_cuotas,
    SUM(CASE WHEN c.estado = 'PAGADO' THEN 1 ELSE 0 END) AS cuotas_pagadas,
    SUM(CASE WHEN c.estado = 'ATRASADO' THEN 1 ELSE 0 END) AS cuotas_atrasadas,
    SUM(CASE WHEN c.estado = 'PENDIENTE' THEN 1 ELSE 0 END) AS cuotas_pendientes
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
LEFT JOIN pagos pg ON p.id = pg.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, p.nombres, p.estado, p.total_financiamiento, 
         p.modalidad_pago, p.numero_cuotas, p.cuota_periodo, 
         p.fecha_base_calculo, p.tasa_interes, p.usuario_proponente, p.usuario_aprobador
ORDER BY p.fecha_aprobacion DESC NULLS LAST
LIMIT 1;

-- ============================================
-- 7. VERIFICAR COLUMNAS CRÍTICAS
-- ============================================
-- 7.1 Valores nulos en columnas críticas
SELECT 
    'Valores nulos' AS verificación,
    COUNT(*) AS total_prestamos,
    COUNT(cliente_id) AS con_cliente_id,
    COUNT(cedula) AS con_cedula,
    COUNT(nombres) AS con_nombres,
    COUNT(total_financiamiento) AS con_total,
    COUNT(modalidad_pago) AS con_modalidad,
    COUNT(numero_cuotas) AS con_numero_cuotas,
    COUNT(cuota_periodo) AS con_cuota_periodo,
    COUNT(fecha_registro) AS con_fecha_registro
FROM prestamos;

-- 7.2 Rangos de valores
SELECT 
    'Rangos de valores' AS verificación,
    MIN(total_financiamiento) AS min_financiamiento,
    MAX(total_financiamiento) AS max_financiamiento,
    AVG(total_financiamiento) AS avg_financiamiento,
    MIN(numero_cuotas) AS min_cuotas,
    MAX(numero_cuotas) AS max_cuotas,
    AVG(numero_cuotas) AS avg_cuotas,
    MIN(cuota_periodo) AS min_cuota_periodo,
    MAX(cuota_periodo) AS max_cuota_periodo,
    AVG(cuota_periodo) AS avg_cuota_periodo
FROM prestamos
WHERE total_financiamiento IS NOT NULL;

-- ============================================
-- 8. RESUMEN FINAL
-- ============================================
SELECT 
    '=== RESUMEN FINAL ===' AS seccion,
    COUNT(*) AS total_prestamos,
    COUNT(DISTINCT cliente_id) AS clientes_distintos,
    COUNT(DISTINCT cedula) AS cedulas_distintas,
    COUNT(CASE WHEN estado = 'APROBADO' THEN 1 END) AS aprobados,
    COUNT(CASE WHEN estado = 'DRAFT' THEN 1 END) AS draft,
    COUNT(CASE WHEN estado = 'EN_REVISION' THEN 1 END) AS en_revision,
    COUNT(CASE WHEN estado = 'EVALUADO' THEN 1 END) AS evaluados,
    COUNT(CASE WHEN estado = 'RECHAZADO' THEN 1 END) AS rechazados,
    SUM(total_financiamiento) AS total_financiado_global,
    COUNT(DISTINCT prestamo_id) AS prestamos_con_cuotas,
    COUNT(DISTINCT pagos.prestamo_id) AS prestamos_con_pagos
FROM prestamos
LEFT JOIN cuotas ON prestamos.id = cuotas.prestamo_id
LEFT JOIN pagos ON prestamos.id = pagos.prestamo_id;

