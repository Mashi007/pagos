-- ============================================
-- LIMPIAR: Columna total_pagado en tabla cuotas
-- ============================================
-- Este script establece total_pagado = 0.00 en TODAS las cuotas
-- y también limpia fecha_pago y actualiza el estado
--
-- ⚠️ ADVERTENCIA: Este script elimina TODOS los datos de pagos en cuotas
-- Solo ejecutar si estás seguro de que quieres empezar desde cero
-- ============================================

-- ============================================
-- PASO 1: BACKUP ANTES DE LIMPIAR
-- ============================================
-- Crear tabla de respaldo con los datos actuales
CREATE TABLE IF NOT EXISTS cuotas_backup_total_pagado AS
SELECT 
    id,
    prestamo_id,
    numero_cuota,
    total_pagado,
    fecha_pago,
    estado,
    monto_cuota,
    fecha_vencimiento,
    NOW() AS fecha_backup
FROM cuotas
WHERE total_pagado > 0 OR fecha_pago IS NOT NULL;

-- ============================================
-- PASO 2: VERIFICAR CUANTAS CUOTAS SE VAN A LIMPIAR
-- ============================================
SELECT 
    'CUOTAS QUE SE VAN A LIMPIAR' AS seccion,
    COUNT(*) AS total_cuotas_a_limpiar,
    SUM(total_pagado) AS monto_total_a_limpiar
FROM cuotas
WHERE total_pagado > 0 OR fecha_pago IS NOT NULL;

-- ============================================
-- PASO 3: LIMPIAR TOTAL_PAGADO Y FECHA_PAGO
-- ============================================
-- Establecer total_pagado = 0.00 en todas las cuotas
UPDATE cuotas
SET 
    total_pagado = 0.00,
    fecha_pago = NULL,
    estado = CASE 
        WHEN fecha_vencimiento < CURRENT_DATE THEN 'ATRASADO'
        ELSE 'PENDIENTE'
    END,
    dias_mora = CASE 
        WHEN fecha_vencimiento < CURRENT_DATE THEN 
            EXTRACT(DAY FROM (CURRENT_DATE - fecha_vencimiento))
        ELSE 0
    END,
    dias_morosidad = CASE 
        WHEN fecha_vencimiento < CURRENT_DATE THEN 
            EXTRACT(DAY FROM (CURRENT_DATE - fecha_vencimiento))
        ELSE 0
    END,
    actualizado_en = NOW()
WHERE total_pagado > 0 OR fecha_pago IS NOT NULL;

-- ============================================
-- PASO 4: VERIFICACION POST-LIMPIEZA
-- ============================================
SELECT 
    'VERIFICACION POST-LIMPIEZA' AS seccion,
    COUNT(*) AS total_cuotas,
    COUNT(CASE WHEN total_pagado = 0 OR total_pagado IS NULL THEN 1 END) AS cuotas_con_total_pagado_cero,
    COUNT(CASE WHEN total_pagado > 0 THEN 1 END) AS cuotas_con_total_pagado_mayor_cero,
    COUNT(CASE WHEN fecha_pago IS NULL THEN 1 END) AS cuotas_sin_fecha_pago,
    COUNT(CASE WHEN fecha_pago IS NOT NULL THEN 1 END) AS cuotas_con_fecha_pago
FROM cuotas;

-- ============================================
-- PASO 5: RESUMEN DE ESTADOS ACTUALIZADOS
-- ============================================
SELECT 
    'RESUMEN ESTADOS DESPUES DE LIMPIAR' AS seccion,
    estado,
    COUNT(*) AS cantidad_cuotas
FROM cuotas
GROUP BY estado
ORDER BY cantidad_cuotas DESC;
