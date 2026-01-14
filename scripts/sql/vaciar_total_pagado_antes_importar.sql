-- ============================================
-- VACIAR total_pagado ANTES DE IMPORTAR PAGOS
-- Para ejecutar en DBeaver
-- ============================================
-- ⚠️ IMPORTANTE: Este script vacía total_pagado en todas las cuotas
-- Ejecutar SOLO si quieres limpiar antes de importar pagos conciliados
-- ============================================

-- ============================================
-- PASO 1: VERIFICAR ESTADO ACTUAL (ANTES DE VACIAR)
-- ============================================
SELECT 
    'ESTADO ANTES DE VACIAR' as etapa,
    COUNT(*) as total_cuotas,
    COUNT(*) FILTER (WHERE total_pagado > 0) as cuotas_con_pago,
    SUM(total_pagado) as suma_total_pagado
FROM public.cuotas;

-- ============================================
-- PASO 2: MOSTRAR CUOTAS QUE SE VAN A VACIAR
-- ============================================
SELECT 
    'CUOTAS QUE SE VACIARAN' as etapa,
    c.id as cuota_id,
    c.prestamo_id,
    pr.cedula,
    c.numero_cuota,
    c.monto_cuota,
    c.total_pagado,
    c.estado
FROM public.cuotas c
JOIN public.prestamos pr ON pr.id = c.prestamo_id
WHERE c.total_pagado > 0
ORDER BY c.prestamo_id, c.numero_cuota;

-- ============================================
-- PASO 3: VACIAR total_pagado Y CAMPOS RELACIONADOS
-- ============================================
-- ⚠️ DESCOMENTAR PARA EJECUTAR:

/*
UPDATE public.cuotas
SET 
    total_pagado = 0,
    fecha_pago = NULL,
    dias_mora = NULL,
    estado = CASE 
        WHEN estado = 'PAGADO' THEN 'PENDIENTE'
        WHEN estado = 'PARCIAL' THEN 'PENDIENTE'
        WHEN estado = 'ADELANTADO' THEN 'PENDIENTE'
        ELSE estado
    END
WHERE total_pagado > 0 OR fecha_pago IS NOT NULL;
*/

-- ============================================
-- PASO 4: VERIFICAR ESTADO DESPUÉS DE VACIAR
-- ============================================
-- Ejecutar después de vaciar para verificar:

/*
SELECT 
    'ESTADO DESPUES DE VACIAR' as etapa,
    COUNT(*) as total_cuotas,
    COUNT(*) FILTER (WHERE total_pagado > 0) as cuotas_con_pago,
    COUNT(*) FILTER (WHERE total_pagado = 0 OR total_pagado IS NULL) as cuotas_vacias,
    SUM(total_pagado) as suma_total_pagado
FROM public.cuotas;
*/

-- ============================================
-- PASO 5: VERIFICAR QUE NO QUEDEN PAGOS
-- ============================================
-- Ejecutar después de vaciar:

/*
SELECT 
    'VERIFICACION FINAL' as etapa,
    COUNT(*) FILTER (WHERE total_pagado > 0) as cuotas_con_pago_restante,
    CASE 
        WHEN COUNT(*) FILTER (WHERE total_pagado > 0) = 0
        THEN 'OK - TODAS LAS CUOTAS ESTÁN VACÍAS'
        ELSE 'ERROR - AÚN HAY CUOTAS CON PAGOS'
    END as validacion
FROM public.cuotas;
*/

-- ============================================
-- RESUMEN
-- ============================================
SELECT 
    '[INFO] Script listo. Descomentar las secciones para ejecutar el vaciado.' as resultado;
