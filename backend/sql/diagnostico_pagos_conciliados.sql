-- ====================================================================
-- AUDITORIA SQL - VERIFICAR PAGOS CONCILIADOS PARA PRESTAMO #4601
-- ====================================================================
-- Script para ejecutar directamente en PostgreSQL para diagnosticar
-- por qué los pagos conciliados no aparecen en la tabla de amortización

-- ====================================================================
-- 1. INFORMACIÓN DEL PRÉSTAMO
-- ====================================================================
SELECT 
    p.id,
    p.cliente_id,
    p.cedula,
    p.nombres,
    p.total_financiamiento,
    p.estado,
    p.numero_cuotas,
    p.modalidad_pago,
    p.fecha_registro,
    p.fecha_aprobacion
FROM public.prestamos p
WHERE p.id = 4601;

-- ====================================================================
-- 2. CUOTAS DEL PRÉSTAMO
-- ====================================================================
SELECT 
    c.id,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.monto_cuota,
    c.pago_id,
    c.total_pagado,
    c.estado,
    c.fecha_pago
FROM public.cuotas c
WHERE c.prestamo_id = 4601
ORDER BY c.numero_cuota;

-- ====================================================================
-- 3. TODOS LOS PAGOS REGISTRADOS PARA ESTE PRÉSTAMO
-- ====================================================================
SELECT 
    p.id,
    p.prestamo_id,
    p.cedula,
    p.fecha_pago,
    p.monto_pagado,
    p.conciliado,
    p.verificado_concordancia,
    p.estado,
    p.referencia_pago,
    p.numero_documento
FROM public.pagos p
WHERE p.prestamo_id = 4601
ORDER BY p.fecha_pago DESC;

-- ====================================================================
-- 4. ANÁLISIS: CUOTAS vs PAGOS (Búsqueda por FK)
-- ====================================================================
SELECT 
    c.numero_cuota,
    c.fecha_vencimiento,
    c.monto_cuota,
    c.pago_id,
    c.total_pagado,
    p.id as pago_id_encontrado,
    p.monto_pagado,
    p.conciliado,
    p.verificado_concordancia,
    CASE 
        WHEN p.conciliado = true THEN '✅ CONCILIADO'
        WHEN p.verificado_concordancia = 'SI' THEN '✅ VERIFICADO SI'
        WHEN p.id IS NULL THEN '❌ SIN PAGO'
        ELSE '⚠️  PAGO SIN CONCILIAR'
    END as estado_conciliacion
FROM public.cuotas c
LEFT JOIN public.pagos p ON c.pago_id = p.id
WHERE c.prestamo_id = 4601
ORDER BY c.numero_cuota;

-- ====================================================================
-- 5. ANÁLISIS: BÚSQUEDA ALTERNATIVA POR RANGO DE FECHAS
-- ====================================================================
-- Para cada cuota, buscar pagos en rango ±15 días (como lo hace el nuevo endpoint)
WITH cuotas_con_rangos AS (
    SELECT 
        numero_cuota,
        fecha_vencimiento,
        monto_cuota,
        (fecha_vencimiento - interval '15 days')::date as fecha_inicio,
        (fecha_vencimiento + interval '15 days')::date as fecha_fin
    FROM public.cuotas
    WHERE prestamo_id = 4601
)
SELECT 
    c.numero_cuota,
    c.fecha_vencimiento,
    c.monto_cuota,
    p.id as pago_encontrado,
    DATE(p.fecha_pago) as fecha_pago,
    p.monto_pagado,
    p.conciliado,
    p.verificado_concordancia,
    c.fecha_inicio,
    c.fecha_fin
FROM cuotas_con_rangos c
LEFT JOIN public.pagos p ON (
    p.prestamo_id = 4601
    AND DATE(p.fecha_pago) >= c.fecha_inicio
    AND DATE(p.fecha_pago) <= c.fecha_fin
)
WHERE p.id IS NOT NULL
ORDER BY c.numero_cuota, p.fecha_pago;

-- ====================================================================
-- 6. CONTEOS RESUMEN
-- ====================================================================
SELECT 
    'Total Cuotas' as metrica,
    COUNT(*) as valor
FROM public.cuotas
WHERE prestamo_id = 4601
UNION ALL
SELECT 
    'Total Pagos',
    COUNT(*)
FROM public.pagos
WHERE prestamo_id = 4601
UNION ALL
SELECT 
    'Pagos Conciliados',
    COUNT(*)
FROM public.pagos
WHERE prestamo_id = 4601 AND (conciliado = true OR verificado_concordancia = 'SI')
UNION ALL
SELECT 
    'Pagos Sin Conciliar',
    COUNT(*)
FROM public.pagos
WHERE prestamo_id = 4601 AND (conciliado != true OR conciliado IS NULL)
UNION ALL
SELECT 
    'Cuotas con pago_id vinculado',
    COUNT(*)
FROM public.cuotas
WHERE prestamo_id = 4601 AND pago_id IS NOT NULL
UNION ALL
SELECT 
    'Cuotas SIN pago_id (NULL)',
    COUNT(*)
FROM public.cuotas
WHERE prestamo_id = 4601 AND pago_id IS NULL;

-- ====================================================================
-- 7. TOTAL FINANCIERO
-- ====================================================================
SELECT 
    'Total Financiamiento' as concepto,
    SUM(p.monto_cuota)::numeric(14,2) as valor
FROM public.cuotas c
JOIN public.prestamos p ON c.prestamo_id = p.id
WHERE p.id = 4601
UNION ALL
SELECT 
    'Total Pagado (cuotas.total_pagado)',
    SUM(c.total_pagado)::numeric(14,2)
FROM public.cuotas c
WHERE c.prestamo_id = 4601
UNION ALL
SELECT 
    'Total Pagos Registrados (pagos.monto_pagado)',
    SUM(p.monto_pagado)::numeric(14,2)
FROM public.pagos p
WHERE p.prestamo_id = 4601
UNION ALL
SELECT 
    'Total Pagos Conciliados',
    SUM(p.monto_pagado)::numeric(14,2)
FROM public.pagos p
WHERE p.prestamo_id = 4601 AND (p.conciliado = true OR p.verificado_concordancia = 'SI');

-- ====================================================================
-- 8. DIAGNOSTICO: ¿POR QUÉ NO SE VEN LOS PAGOS CONCILIADOS?
-- ====================================================================
-- Este query identifica la raíz del problema
SELECT 
    'PROBLEMA DIAGNOSTICADO' as tipo,
    CASE 
        WHEN (
            SELECT COUNT(*) 
            FROM public.pagos 
            WHERE prestamo_id = 4601 AND pago_id IS NULL
        ) > 0 THEN 'cuota.pago_id está NULL - FK no vinculada'
        WHEN (
            SELECT COUNT(*) 
            FROM public.pagos 
            WHERE prestamo_id = 4601 AND conciliado = false
        ) > 0 THEN 'Pagos no conciliados en BD'
        WHEN (
            SELECT COUNT(*) 
            FROM public.pagos 
            WHERE prestamo_id = 4601
        ) = 0 THEN 'No hay pagos registrados para este préstamo'
        ELSE 'Datos parecen estar correctos'
    END as diagnostico
UNION ALL
SELECT 
    'SOLUCIÓN IMPLEMENTADA',
    'Nuevo endpoint busca pagos por rango de fechas (±15 días) cuando pago_id=NULL'
UNION ALL
SELECT 
    'VERIFICAR',
    'Ejecutar el endpoint GET /prestamos/4601/cuotas después del deploy'
;

-- ====================================================================
-- NOTAS DE EJECUCIÓN:
-- ====================================================================
-- 1. Ejecutar este script contra la BD de Render
-- 2. Reemplazar 4601 por otro prestamo_id si es necesario
-- 3. Los resultados mostrarán si los pagos conciliados existen pero no se vinculan
-- 4. Si los queries anteriores muestran pagos conciliados pero con pago_id=NULL,
--    es confirmación de que el nuevo endpoint corrige el problema
