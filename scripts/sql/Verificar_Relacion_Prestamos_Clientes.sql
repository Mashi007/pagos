-- ============================================
-- VERIFICACIÓN DETALLADA: RELACIÓN PRÉSTAMOS-CLIENTES
-- ============================================

-- ============================================
-- 1. VERIFICAR RELACIÓN POR cliente_id
-- ============================================
SELECT 
    '=== RELACIÓN POR cliente_id ===' AS verificacion,
    COUNT(DISTINCT p.id) AS total_prestamos,
    COUNT(DISTINCT p.cliente_id) AS prestamos_con_cliente_id,
    COUNT(DISTINCT c.id) AS clientes_encontrados,
    COUNT(DISTINCT CASE WHEN c.id IS NULL THEN p.cliente_id END) AS prestamos_sin_cliente_valido,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN c.id IS NOT NULL THEN p.id END) / COUNT(DISTINCT p.id), 2) AS porcentaje_relacionados
FROM prestamos p
LEFT JOIN clientes c ON p.cliente_id = c.id;

-- Detalle: Préstamos SIN cliente_id válido
SELECT 
    'Préstamos SIN cliente_id válido' AS problema,
    p.id AS prestamo_id,
    p.cliente_id,
    p.cedula AS cedula_prestamo,
    p.nombres AS nombres_prestamo,
    p.estado,
    p.fecha_registro
FROM prestamos p
LEFT JOIN clientes c ON p.cliente_id = c.id
WHERE c.id IS NULL
ORDER BY p.fecha_registro DESC;

-- ============================================
-- 2. VERIFICAR RELACIÓN POR CÉDULA
-- ============================================
SELECT 
    '=== RELACIÓN POR CÉDULA ===' AS verificacion,
    COUNT(DISTINCT p.id) AS total_prestamos,
    COUNT(DISTINCT p.cedula) AS cedulas_distintas_prestamos,
    COUNT(DISTINCT c.cedula) AS cedulas_distintas_clientes,
    COUNT(DISTINCT CASE WHEN c.cedula IS NULL THEN p.cedula END) AS cedulas_prestamos_sin_cliente,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN c.cedula IS NOT NULL THEN p.id END) / COUNT(DISTINCT p.id), 2) AS porcentaje_relacionados_cedula
FROM prestamos p
LEFT JOIN clientes c ON UPPER(TRIM(p.cedula)) = UPPER(TRIM(c.cedula));

-- Detalle: Préstamos con cédula pero SIN coincidencia en clientes
SELECT 
    'Préstamos con cédula SIN coincidencia en clientes' AS problema,
    p.id AS prestamo_id,
    p.cedula AS cedula_prestamo,
    p.cliente_id,
    p.nombres AS nombres_prestamo,
    p.estado,
    p.fecha_registro
FROM prestamos p
WHERE NOT EXISTS (
    SELECT 1 FROM clientes c 
    WHERE UPPER(TRIM(c.cedula)) = UPPER(TRIM(p.cedula))
)
ORDER BY p.fecha_registro DESC;

-- ============================================
-- 3. VERIFICAR INCONSISTENCIAS ENTRE cliente_id Y cédula
-- ============================================
SELECT 
    '=== INCONSISTENCIAS cliente_id vs CÉDULA ===' AS verificacion,
    COUNT(*) AS total_casos,
    COUNT(CASE WHEN p.cliente_id IS NOT NULL AND c_match.id IS NULL THEN 1 END) AS cliente_id_sin_cedula_match,
    COUNT(CASE WHEN p.cedula IS NOT NULL AND c_cedula.id IS NULL THEN 1 END) AS cedula_sin_cliente_match,
    COUNT(CASE WHEN p.cliente_id IS NOT NULL AND c_match.id IS NOT NULL AND p.cedula IS NOT NULL AND UPPER(TRIM(p.cedula)) != UPPER(TRIM(c_match.cedula)) THEN 1 END) AS cliente_id_cedula_no_coinciden
FROM prestamos p
LEFT JOIN clientes c_match ON p.cliente_id = c_match.id
LEFT JOIN clientes c_cedula ON UPPER(TRIM(p.cedula)) = UPPER(TRIM(c_cedula.cedula));

-- Casos donde cliente_id existe pero la cédula del préstamo NO coincide con la cédula del cliente
SELECT 
    'Cliente_id existe pero cédula NO coincide' AS problema,
    p.id AS prestamo_id,
    p.cliente_id,
    p.cedula AS cedula_prestamo,
    c.cedula AS cedula_cliente,
    p.nombres AS nombres_prestamo,
    c.nombres AS nombres_cliente,
    p.estado
FROM prestamos p
JOIN clientes c ON p.cliente_id = c.id
WHERE UPPER(TRIM(p.cedula)) != UPPER(TRIM(c.cedula))
ORDER BY p.fecha_registro DESC;

-- Casos donde cédula coincide pero cliente_id es diferente
SELECT 
    'Cédula coincide pero cliente_id diferente' AS problema,
    p.id AS prestamo_id,
    p.cliente_id AS cliente_id_prestamo,
    c_match.id AS cliente_id_real,
    p.cedula AS cedula_prestamo,
    p.nombres AS nombres_prestamo,
    c_match.nombres AS nombres_cliente,
    p.estado
FROM prestamos p
JOIN clientes c_match ON UPPER(TRIM(p.cedula)) = UPPER(TRIM(c_match.cedula))
LEFT JOIN clientes c_prestamo ON p.cliente_id = c_prestamo.id
WHERE p.cliente_id IS NULL 
   OR p.cliente_id != c_match.id
ORDER BY p.fecha_registro DESC;

-- ============================================
-- 4. ESTADÍSTICAS DE RELACIONES POR ESTADO
-- ============================================
SELECT 
    '=== ESTADÍSTICAS POR ESTADO ===' AS verificacion,
    p.estado,
    COUNT(DISTINCT p.id) AS total_prestamos,
    COUNT(DISTINCT CASE WHEN c.id IS NOT NULL THEN p.id END) AS con_cliente_id_valido,
    COUNT(DISTINCT CASE WHEN c_cedula.id IS NOT NULL THEN p.id END) AS con_cedula_match,
    COUNT(DISTINCT CASE WHEN c.id IS NULL AND c_cedula.id IS NULL THEN p.id END) AS sin_relacion
FROM prestamos p
LEFT JOIN clientes c ON p.cliente_id = c.id
LEFT JOIN clientes c_cedula ON UPPER(TRIM(p.cedula)) = UPPER(TRIM(c_cedula.cedula))
GROUP BY p.estado
ORDER BY COUNT(DISTINCT p.id) DESC;

-- ============================================
-- 5. VERIFICAR CLIENTES CON MÚLTIPLES PRÉSTAMOS
-- ============================================
SELECT 
    '=== CLIENTES CON MÚLTIPLES PRÉSTAMOS ===' AS verificacion,
    c.id AS cliente_id,
    c.cedula AS cedula_cliente,
    c.nombres AS nombres_cliente,
    COUNT(DISTINCT p.id) AS total_prestamos,
    COUNT(DISTINCT CASE WHEN p.estado = 'APROBADO' THEN p.id END) AS prestamos_aprobados,
    SUM(CASE WHEN p.estado = 'APROBADO' THEN p.total_financiamiento ELSE 0 END) AS total_financiado_aprobados,
    MAX(p.fecha_registro) AS ultimo_prestamo
FROM clientes c
JOIN prestamos p ON c.id = p.cliente_id
GROUP BY c.id, c.cedula, c.nombres
HAVING COUNT(DISTINCT p.id) > 1
ORDER BY COUNT(DISTINCT p.id) DESC
LIMIT 20;

-- ============================================
-- 6. VERIFICAR PRÉSTAMOS ORFANOS (sin relación con clientes)
-- ============================================
SELECT 
    '=== PRÉSTAMOS COMPLETAMENTE ORFANOS ===' AS verificacion,
    COUNT(*) AS total_orphanos
FROM prestamos p
WHERE NOT EXISTS (
    SELECT 1 FROM clientes c 
    WHERE c.id = p.cliente_id 
       OR UPPER(TRIM(c.cedula)) = UPPER(TRIM(p.cedula))
);

-- Detalle de préstamos huérfanos
SELECT 
    'Préstamos huérfanos (sin relación con clientes)' AS problema,
    p.id AS prestamo_id,
    p.cliente_id,
    p.cedula AS cedula_prestamo,
    p.nombres AS nombres_prestamo,
    p.estado,
    p.total_financiamiento,
    p.fecha_registro
FROM prestamos p
WHERE NOT EXISTS (
    SELECT 1 FROM clientes c 
    WHERE c.id = p.cliente_id 
       OR UPPER(TRIM(c.cedula)) = UPPER(TRIM(p.cedula))
)
ORDER BY p.fecha_registro DESC;

-- ============================================
-- 7. RESUMEN DE INTEGRIDAD
-- ============================================
SELECT 
    '=== RESUMEN FINAL DE INTEGRIDAD ===' AS verificacion,
    COUNT(DISTINCT p.id) AS total_prestamos,
    COUNT(DISTINCT CASE WHEN p.cliente_id IS NOT NULL THEN p.id END) AS con_cliente_id,
    COUNT(DISTINCT CASE WHEN p.cedula IS NOT NULL THEN p.id END) AS con_cedula,
    COUNT(DISTINCT CASE WHEN c_id.id IS NOT NULL THEN p.id END) AS cliente_id_valido,
    COUNT(DISTINCT CASE WHEN c_cedula.id IS NOT NULL THEN p.id END) AS cedula_valida,
    COUNT(DISTINCT CASE WHEN c_id.id IS NOT NULL OR c_cedula.id IS NOT NULL THEN p.id END) AS con_relacion_valida,
    COUNT(DISTINCT CASE WHEN c_id.id IS NULL AND c_cedula.id IS NULL THEN p.id END) AS sin_relacion,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN c_id.id IS NOT NULL OR c_cedula.id IS NOT NULL THEN p.id END) / COUNT(DISTINCT p.id), 2) AS porcentaje_integridad
FROM prestamos p
LEFT JOIN clientes c_id ON p.cliente_id = c_id.id
LEFT JOIN clientes c_cedula ON UPPER(TRIM(p.cedula)) = UPPER(TRIM(c_cedula.cedula));

-- ============================================
-- 8. VERIFICAR NORMALIZACIÓN DE CÉDULAS
-- ============================================
SELECT 
    '=== VERIFICAR NORMALIZACIÓN DE CÉDULAS ===' AS verificacion,
    p.cedula AS cedula_prestamo,
    c.cedula AS cedula_cliente,
    COUNT(DISTINCT p.id) AS veces_diferencias,
    CASE 
        WHEN UPPER(TRIM(p.cedula)) = UPPER(TRIM(c.cedula)) THEN 'Igual'
        ELSE 'Diferente (espacios/case)'
    END AS comparacion
FROM prestamos p
JOIN clientes c ON p.cliente_id = c.id
WHERE UPPER(TRIM(p.cedula)) != UPPER(TRIM(c.cedula))
GROUP BY p.cedula, c.cedula, p.cliente_id
LIMIT 10;
