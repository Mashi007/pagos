-- ======================================================================
-- CORRECCION: COMPLETAR CUOTAS FALTANTES
-- ======================================================================
-- Objetivo: Identificar préstamos con cuotas faltantes para regeneración
-- NOTA: Este script solo identifica, la regeneración se hace con Python
-- ======================================================================

-- ======================================================================
-- 1. VERIFICACION ANTES DE CORRECCION
-- ======================================================================

SELECT 
    'ANTES' AS momento,
    COUNT(DISTINCT p.id) AS prestamos_con_cuotas_faltantes,
    SUM(p.numero_cuotas - COUNT(cu.id)) AS total_cuotas_faltantes
FROM prestamos p
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.numero_cuotas
HAVING COUNT(cu.id) < p.numero_cuotas;

-- ======================================================================
-- 2. LISTAR PRESTAMOS CON CUOTAS FALTANTES
-- ======================================================================

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    c.nombres AS nombre_cliente,
    p.numero_cuotas AS cuotas_planificadas,
    COUNT(cu.id) AS cuotas_generadas,
    p.numero_cuotas - COUNT(cu.id) AS cuotas_faltantes,
    p.total_financiamiento,
    p.cuota_periodo,
    p.modalidad_pago,
    p.tasa_interes,
    p.fecha_aprobacion,
    p.fecha_base_calculo,
    CASE 
        WHEN p.fecha_base_calculo IS NULL THEN 'NO PUEDE GENERAR (falta fecha_base_calculo)'
        ELSE 'PUEDE GENERAR'
    END AS puede_regenerar
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, c.nombres, p.numero_cuotas, p.total_financiamiento,
         p.cuota_periodo, p.modalidad_pago, p.tasa_interes, p.fecha_aprobacion,
         p.fecha_base_calculo
HAVING COUNT(cu.id) < p.numero_cuotas
ORDER BY p.id;

-- ======================================================================
-- 3. VERIFICAR CUOTAS EXISTENTES PARA ENTENDER PATRON
-- ======================================================================

SELECT 
    p.id AS prestamo_id,
    p.numero_cuotas AS cuotas_planificadas,
    COUNT(cu.id) AS cuotas_generadas,
    MIN(cu.numero_cuota) AS primera_cuota_numero,
    MAX(cu.numero_cuota) AS ultima_cuota_numero,
    STRING_AGG(DISTINCT cu.numero_cuota::text, ', ' ORDER BY cu.numero_cuota::text) AS numeros_cuotas_existentes
FROM prestamos p
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.numero_cuotas
HAVING COUNT(cu.id) < p.numero_cuotas
ORDER BY p.id
LIMIT 20;

-- ======================================================================
-- 4. PRESTAMOS QUE PUEDEN REGENERARSE (TIENEN fecha_base_calculo)
-- ======================================================================

SELECT 
    COUNT(DISTINCT p.id) AS prestamos_que_pueden_regenerar,
    SUM(p.numero_cuotas - COUNT(cu.id)) AS total_cuotas_a_generar
FROM prestamos p
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
  AND p.fecha_base_calculo IS NOT NULL
GROUP BY p.id, p.numero_cuotas
HAVING COUNT(cu.id) < p.numero_cuotas;

-- ======================================================================
-- 5. PRESTAMOS QUE NO PUEDEN REGENERARSE (FALTA fecha_base_calculo)
-- ======================================================================

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    c.nombres AS nombre_cliente,
    p.numero_cuotas AS cuotas_planificadas,
    COUNT(cu.id) AS cuotas_generadas,
    p.fecha_aprobacion
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
  AND p.fecha_base_calculo IS NULL
GROUP BY p.id, p.cedula, c.nombres, p.numero_cuotas, p.fecha_aprobacion
HAVING COUNT(cu.id) < p.numero_cuotas
ORDER BY p.id;

-- ======================================================================
-- NOTAS:
-- ======================================================================
-- Este script SOLO identifica los préstamos con cuotas faltantes
-- Para regenerar las cuotas faltantes, usar:
-- 1. Script Python: scripts/python/completar_cuotas_faltantes.py
-- 2. O endpoint API: POST /api/v1/prestamos/{id}/generar-amortizacion
-- 
-- IMPORTANTE: 
-- - Los préstamos con fecha_base_calculo pueden regenerarse directamente
-- - Los préstamos sin fecha_base_calculo necesitan asignar fecha primero
-- ======================================================================
