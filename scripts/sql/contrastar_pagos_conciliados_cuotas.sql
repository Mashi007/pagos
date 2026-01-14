-- ============================================
-- CONTRASTAR: Pagos Conciliados vs Cuotas
-- Para ejecutar en DBeaver
-- ============================================
-- Este script permite contrastar los pagos conciliados
-- con el total_pagado en las cuotas de cada préstamo
-- ============================================

-- ============================================
-- PASO 1: RESUMEN GENERAL
-- ============================================
SELECT 
    'RESUMEN GENERAL' as etapa,
    (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) as total_pagos_conciliados,
    (SELECT SUM(total_pagado) FROM public.cuotas) as total_pagado_en_cuotas,
    (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) - 
    (SELECT SUM(total_pagado) FROM public.cuotas) as diferencia,
    CASE 
        WHEN ABS(
            (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) - 
            (SELECT SUM(total_pagado) FROM public.cuotas)
        ) < 0.01 
        THEN 'OK - COINCIDEN'
        ELSE 'ADVERTENCIA - DIFERENCIA'
    END as validacion;

-- ============================================
-- PASO 2: CONTRASTAR POR PRESTAMO
-- ============================================
SELECT 
    'CONTRASTE POR PRESTAMO' as etapa,
    p.prestamo_id,
    pr.cedula,
    -- Suma de pagos conciliados
    SUM(DISTINCT p.monto_pagado) FILTER (WHERE p.conciliado = TRUE) as suma_pagos_conciliados,
    -- Suma de total_pagado en cuotas
    SUM(c.total_pagado) as suma_total_pagado_cuotas,
    -- Diferencia
    SUM(DISTINCT p.monto_pagado) FILTER (WHERE p.conciliado = TRUE) - 
    SUM(c.total_pagado) as diferencia,
    -- Validación
    CASE 
        WHEN ABS(
            SUM(DISTINCT p.monto_pagado) FILTER (WHERE p.conciliado = TRUE) - 
            SUM(c.total_pagado)
        ) < 0.01 
        THEN 'OK - COINCIDEN'
        ELSE 'ERROR - NO COINCIDEN'
    END as validacion
FROM public.pagos p
JOIN public.prestamos pr ON pr.id = p.prestamo_id
LEFT JOIN public.cuotas c ON c.prestamo_id = p.prestamo_id
WHERE p.conciliado = TRUE
GROUP BY p.prestamo_id, pr.cedula
ORDER BY diferencia DESC, p.prestamo_id;

-- ============================================
-- PASO 3: PRESTAMOS CON DIFERENCIAS
-- ============================================
SELECT 
    'PRESTAMOS CON DIFERENCIAS' as etapa,
    p.prestamo_id,
    pr.cedula,
    SUM(DISTINCT p.monto_pagado) FILTER (WHERE p.conciliado = TRUE) as suma_pagos_conciliados,
    SUM(c.total_pagado) as suma_total_pagado_cuotas,
    ABS(SUM(DISTINCT p.monto_pagado) FILTER (WHERE p.conciliado = TRUE) - SUM(c.total_pagado)) as diferencia_absoluta
FROM public.pagos p
JOIN public.prestamos pr ON pr.id = p.prestamo_id
LEFT JOIN public.cuotas c ON c.prestamo_id = p.prestamo_id
WHERE p.conciliado = TRUE
GROUP BY p.prestamo_id, pr.cedula
HAVING ABS(SUM(DISTINCT p.monto_pagado) FILTER (WHERE p.conciliado = TRUE) - SUM(c.total_pagado)) >= 0.01
ORDER BY diferencia_absoluta DESC;

-- ============================================
-- PASO 4: DETALLE DE UN PRESTAMO ESPECÍFICO
-- ============================================
-- ⚠️ CAMBIAR ESTE ID POR EL PRESTAMO QUE QUIERAS VERIFICAR
-- Ejemplo: WHERE p.prestamo_id = 123

-- 4.1: Pagos conciliados del préstamo
SELECT 
    'PAGOS CONCILIADOS DEL PRESTAMO' as tipo,
    p.id as pago_id,
    p.cedula,
    p.monto_pagado,
    p.fecha_pago,
    p.conciliado,
    p.prestamo_id
FROM public.pagos p
WHERE p.prestamo_id = 123  -- ← CAMBIAR POR EL ID DEL PRESTAMO
  AND p.conciliado = TRUE
ORDER BY p.fecha_pago;

-- 4.2: Cuotas con total_pagado del mismo préstamo
SELECT 
    'CUOTAS CON TOTAL_PAGADO' as tipo,
    c.id as cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    c.monto_cuota,
    c.total_pagado,  -- ← AQUÍ ESTÁN LOS PAGOS CONCILIADOS
    c.estado,
    c.fecha_pago
FROM public.cuotas c
WHERE c.prestamo_id = 123  -- ← Mismo préstamo
ORDER BY c.numero_cuota;

-- 4.3: Resumen comparativo del préstamo
SELECT 
    'RESUMEN COMPARATIVO' as tipo,
    (SELECT SUM(monto_pagado) FROM public.pagos 
     WHERE prestamo_id = 123 AND conciliado = TRUE) as suma_pagos_conciliados,
    (SELECT SUM(total_pagado) FROM public.cuotas 
     WHERE prestamo_id = 123) as suma_total_pagado_cuotas,
    (SELECT SUM(monto_pagado) FROM public.pagos 
     WHERE prestamo_id = 123 AND conciliado = TRUE) - 
    (SELECT SUM(total_pagado) FROM public.cuotas 
     WHERE prestamo_id = 123) as diferencia,
    CASE 
        WHEN ABS(
            (SELECT SUM(monto_pagado) FROM public.pagos 
             WHERE prestamo_id = 123 AND conciliado = TRUE) - 
            (SELECT SUM(total_pagado) FROM public.cuotas 
             WHERE prestamo_id = 123)
        ) < 0.01 
        THEN 'OK - COINCIDEN'
        ELSE 'ERROR - NO COINCIDEN'
    END as validacion;

-- ============================================
-- PASO 5: VERIFICAR PAGOS CONCILIADOS SIN APLICAR
-- ============================================
-- Pagos conciliados que no se han aplicado a cuotas
SELECT 
    'PAGOS CONCILIADOS SIN APLICAR' as etapa,
    p.id as pago_id,
    p.prestamo_id,
    p.cedula,
    p.monto_pagado,
    p.fecha_pago,
    CASE 
        WHEN p.prestamo_id IS NULL THEN 'SIN PRESTAMO_ID'
        WHEN NOT EXISTS (SELECT 1 FROM public.cuotas c WHERE c.prestamo_id = p.prestamo_id) 
        THEN 'PRESTAMO SIN CUOTAS'
        ELSE 'VERIFICAR MANUALMENTE'
    END as razon
FROM public.pagos p
WHERE p.conciliado = TRUE
  AND p.prestamo_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 
      FROM public.cuotas c 
      WHERE c.prestamo_id = p.prestamo_id 
        AND c.total_pagado > 0
  )
ORDER BY p.prestamo_id, p.fecha_pago;

-- ============================================
-- RESUMEN FINAL
-- ============================================
SELECT 
    '[OK] Verificación completada. Los pagos conciliados deben estar en cuotas.total_pagado' as resultado;
