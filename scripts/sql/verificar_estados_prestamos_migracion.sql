-- ======================================================================
-- VERIFICACION: ESTADOS DE PRESTAMOS DESPUES DE MIGRACION
-- ======================================================================
-- Objetivo: Verificar que todos los préstamos estén en estado 'APROBADO'
-- Contexto: Migración de base de datos
-- ======================================================================

-- ======================================================================
-- 1. DISTRIBUCION DE ESTADOS DE PRESTAMOS
-- ======================================================================

SELECT 
    estado,
    COUNT(*) AS total_prestamos,
    COUNT(DISTINCT cedula) AS total_clientes_distintos,
    MIN(fecha_registro) AS primer_prestamo,
    MAX(fecha_registro) AS ultimo_prestamo,
    MIN(fecha_aprobacion) AS primera_aprobacion,
    MAX(fecha_aprobacion) AS ultima_aprobacion
FROM prestamos
GROUP BY estado
ORDER BY total_prestamos DESC;

-- ======================================================================
-- 2. PRESTAMOS QUE NO ESTAN EN ESTADO 'APROBADO'
-- ======================================================================

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    p.estado,
    p.total_financiamiento,
    p.numero_cuotas,
    p.fecha_registro,
    p.fecha_aprobacion,
    c.nombres AS nombre_cliente,
    c.estado AS estado_cliente,
    c.activo AS cliente_activo,
    COUNT(cu.id) AS total_cuotas_generadas
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado != 'APROBADO'
GROUP BY p.id, p.cedula, p.estado, p.total_financiamiento, 
         p.numero_cuotas, p.fecha_registro, p.fecha_aprobacion,
         c.nombres, c.estado, c.activo
ORDER BY p.estado, p.fecha_registro DESC;

-- ======================================================================
-- 3. RESUMEN: PRESTAMOS POR ESTADO
-- ======================================================================

SELECT 
    'Total prestamos' AS metrica,
    COUNT(*) AS valor
FROM prestamos

UNION ALL

SELECT 
    'Prestamos APROBADOS' AS metrica,
    COUNT(*) AS valor
FROM prestamos
WHERE estado = 'APROBADO'

UNION ALL

SELECT 
    'Prestamos NO APROBADOS' AS metrica,
    COUNT(*) AS valor
FROM prestamos
WHERE estado != 'APROBADO'

UNION ALL

SELECT 
    'Prestamos con cuotas generadas' AS metrica,
    COUNT(DISTINCT p.id) AS valor
FROM prestamos p
INNER JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'

UNION ALL

SELECT 
    'Prestamos APROBADOS sin cuotas' AS metrica,
    COUNT(DISTINCT p.id) AS valor
FROM prestamos p
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
  AND cu.id IS NULL;

-- ======================================================================
-- 4. PRESTAMOS APROBADOS SIN CUOTAS GENERADAS
-- ======================================================================
-- Estos pueden requerir atención si deberían tener cuotas
-- ======================================================================

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    p.estado,
    p.total_financiamiento,
    p.numero_cuotas,
    p.cuota_periodo,
    p.fecha_aprobacion,
    p.fecha_registro,
    c.nombres AS nombre_cliente,
    c.estado AS estado_cliente,
    c.activo AS cliente_activo
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
  AND cu.id IS NULL
ORDER BY p.fecha_aprobacion DESC
LIMIT 50;

-- ======================================================================
-- 5. VERIFICACION: PRESTAMOS CON ESTADOS DIFERENTES A 'APROBADO'
-- ======================================================================

SELECT 
    estado,
    COUNT(*) AS cantidad,
    COUNT(DISTINCT cedula) AS clientes_afectados,
    SUM(total_financiamiento) AS total_financiamiento,
    SUM(numero_cuotas) AS total_cuotas_planificadas
FROM prestamos
WHERE estado != 'APROBADO'
GROUP BY estado
ORDER BY cantidad DESC;

-- ======================================================================
-- 6. DETALLE COMPLETO DE PRESTAMOS NO APROBADOS
-- ======================================================================

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    c.nombres AS nombre_cliente,
    p.estado AS estado_prestamo,
    p.total_financiamiento,
    p.numero_cuotas,
    p.cuota_periodo,
    p.fecha_registro,
    p.fecha_aprobacion,
    c.estado AS estado_cliente,
    c.activo AS cliente_activo,
    COUNT(cu.id) AS cuotas_generadas,
    COUNT(pag.id) AS pagos_registrados,
    COALESCE(SUM(pag.monto_pagado), 0) AS total_pagado
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
LEFT JOIN pagos pag ON p.cedula = pag.cedula AND pag.activo = TRUE
WHERE p.estado != 'APROBADO'
GROUP BY p.id, p.cedula, c.nombres, p.estado, p.total_financiamiento,
         p.numero_cuotas, p.cuota_periodo, p.fecha_registro, 
         p.fecha_aprobacion, c.estado, c.activo
ORDER BY p.estado, p.fecha_registro DESC;

-- ======================================================================
-- 7. ESTADISTICAS POR ESTADO Y RELACION CON CLIENTES
-- ======================================================================

SELECT 
    p.estado AS estado_prestamo,
    COUNT(DISTINCT p.id) AS total_prestamos,
    COUNT(DISTINCT p.cedula) AS clientes_con_prestamos,
    COUNT(DISTINCT CASE WHEN c.activo = TRUE THEN c.id END) AS clientes_activos,
    COUNT(DISTINCT CASE WHEN c.activo = FALSE THEN c.id END) AS clientes_inactivos,
    COUNT(DISTINCT cu.id) AS total_cuotas_generadas,
    COUNT(DISTINCT pag.id) AS total_pagos_registrados,
    COALESCE(SUM(p.total_financiamiento), 0) AS total_financiamiento,
    COALESCE(SUM(pag.monto_pagado), 0) AS total_pagado
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
LEFT JOIN pagos pag ON p.cedula = pag.cedula AND pag.activo = TRUE
GROUP BY p.estado
ORDER BY total_prestamos DESC;

-- ======================================================================
-- 8. VERIFICACION FINAL: ¿TODOS LOS PRESTAMOS ESTAN APROBADOS?
-- ======================================================================

SELECT 
    CASE 
        WHEN COUNT(CASE WHEN estado != 'APROBADO' THEN 1 END) = 0 
        THEN 'SI: Todos los prestamos estan APROBADOS'
        ELSE CONCAT('NO: Hay ', COUNT(CASE WHEN estado != 'APROBADO' THEN 1 END), ' prestamos NO aprobados')
    END AS verificacion,
    COUNT(*) AS total_prestamos,
    COUNT(CASE WHEN estado = 'APROBADO' THEN 1 END) AS prestamos_aprobados,
    COUNT(CASE WHEN estado != 'APROBADO' THEN 1 END) AS prestamos_no_aprobados
FROM prestamos;

-- ======================================================================
-- NOTAS:
-- ======================================================================
-- Esta verificación es importante después de una migración de BD
-- Si hay préstamos con estados diferentes a 'APROBADO', pueden requerir:
-- 1. Revisión manual para determinar si deben estar aprobados
-- 2. Corrección masiva si todos deben estar aprobados
-- 3. Validación de la lógica de negocio
-- ======================================================================
