-- ====================================================================
-- AUDITORIA SQL - VERIFICAR PAGOS CONCILIADOS
-- ====================================================================
-- Este script diagnostica por qué los pagos conciliados no aparecen
-- en la tabla de amortización.
--
-- USO:
-- psql $DATABASE_URL < diagnostico_pagos_conciliados.sql
--
-- O en pgAdmin: Copiar, pegar y ejecutar en la consola SQL
--
-- Reemplazar 4601 con el ID de préstamo que desees auditar
-- ====================================================================

-- PASO 1: Información del Préstamo
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

-- PASO 2: Cuotas del Préstamo
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

-- PASO 3: Todos los Pagos Registrados
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

-- PASO 4: Análisis - Cuotas vs Pagos (búsqueda por FK)
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
        WHEN p.conciliado = true THEN 'CONCILIADO'
        WHEN p.verificado_concordancia = 'SI' THEN 'VERIFICADO'
        WHEN p.id IS NULL THEN 'SIN PAGO'
        ELSE 'NO CONCILIADO'
    END as estado_conciliacion
FROM public.cuotas c
LEFT JOIN public.pagos p ON c.pago_id = p.id
WHERE c.prestamo_id = 4601
ORDER BY c.numero_cuota;

-- PASO 5: Búsqueda por Rango de Fechas (como lo hace el nuevo endpoint)
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

-- PASO 6: Resumen de Conteos
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
    'Pagos No Conciliados',
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
    'Cuotas sin pago_id (NULL)',
    COUNT(*)
FROM public.cuotas
WHERE prestamo_id = 4601 AND pago_id IS NULL;

-- PASO 7: Totales Financieros
SELECT 
    'Total Financiamiento (suma cuotas)' as concepto,
    SUM(c.monto_cuota)::numeric(14,2) as valor
FROM public.cuotas c
WHERE c.prestamo_id = 4601
UNION ALL
SELECT 
    'Total Pagado (cuotas.total_pagado)',
    SUM(c.total_pagado)::numeric(14,2)
FROM public.cuotas c
WHERE c.prestamo_id = 4601
UNION ALL
SELECT 
    'Total Pagos Registrados',
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
-- FIN DE LA AUDITORIA
-- ====================================================================
-- Interpretación de resultados:
--
-- 1. Si PASO 3 muestra pagos con conciliado=true pero PASO 4 no los encuentra
--    → El nuevo endpoint los ENCONTRARA (búsqueda por rango)
--
-- 2. Si PASO 2 muestra pago_id=NULL pero PASO 5 encuentra pagos en rango
--    → Confirmación de que el problema estaba en la FK débil
--
-- 3. Si PASO 7 muestra "Total Pagos Conciliados" > 0
--    → Hay pagos para mostrar; el endpoint debe retornarlos
--
-- ====================================================================
