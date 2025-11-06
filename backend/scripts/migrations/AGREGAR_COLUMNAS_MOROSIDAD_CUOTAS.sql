-- ============================================================================
-- MIGRACIÓN: Agregar Columnas de Morosidad en Tabla cuotas
-- ============================================================================
-- Fecha: 2025-11-06
-- Descripción: Agrega dos columnas calculadas automáticamente:
--   1. dias_morosidad: Días de atraso (desde fecha_vencimiento hasta hoy o fecha_pago)
--   2. monto_morosidad: Monto pendiente (monto_cuota - total_pagado)
-- ============================================================================

-- ============================================================================
-- PASO 1: Agregar Columnas
-- ============================================================================

-- Columna 1: Días de Morosidad
ALTER TABLE cuotas
ADD COLUMN IF NOT EXISTS dias_morosidad INTEGER DEFAULT 0;

COMMENT ON COLUMN cuotas.dias_morosidad IS 
'Días de morosidad calculados automáticamente: 
- Si no pagada: (CURRENT_DATE - fecha_vencimiento).days
- Si pagada: (fecha_pago - fecha_vencimiento).days (si fecha_pago > fecha_vencimiento)
- Si pagada a tiempo: 0';

-- Columna 2: Monto de Morosidad (Pendiente)
ALTER TABLE cuotas
ADD COLUMN IF NOT EXISTS monto_morosidad NUMERIC(12, 2) DEFAULT 0.00;

COMMENT ON COLUMN cuotas.monto_morosidad IS 
'Monto de morosidad calculado automáticamente: 
monto_cuota - total_pagado (lo que falta por pagar)';

-- ============================================================================
-- PASO 2: Crear Índices para Optimización
-- ============================================================================

-- Índice para queries de morosidad por días
CREATE INDEX IF NOT EXISTS idx_cuotas_dias_morosidad 
ON cuotas(dias_morosidad) 
WHERE dias_morosidad > 0;

-- Índice para queries de morosidad por monto
CREATE INDEX IF NOT EXISTS idx_cuotas_monto_morosidad 
ON cuotas(monto_morosidad) 
WHERE monto_morosidad > 0;

-- Índice compuesto para queries de morosidad
CREATE INDEX IF NOT EXISTS idx_cuotas_morosidad_completo 
ON cuotas(dias_morosidad, monto_morosidad, estado) 
WHERE dias_morosidad > 0 AND monto_morosidad > 0;

-- ============================================================================
-- PASO 3: Calcular Valores Iniciales para Datos Existentes
-- ============================================================================

-- Actualizar dias_morosidad para todas las cuotas existentes
UPDATE cuotas
SET dias_morosidad = CASE
    -- Si está pagada y fecha_pago > fecha_vencimiento: días entre fecha_pago y fecha_vencimiento
    WHEN fecha_pago IS NOT NULL AND fecha_pago > fecha_vencimiento 
    THEN (fecha_pago - fecha_vencimiento)::INTEGER
    -- Si no está pagada y fecha_vencimiento < CURRENT_DATE: días desde fecha_vencimiento hasta hoy
    WHEN fecha_pago IS NULL AND fecha_vencimiento < CURRENT_DATE 
    THEN (CURRENT_DATE - fecha_vencimiento)::INTEGER
    -- Si está pagada a tiempo o no vencida: 0
    ELSE 0
END;

-- Actualizar monto_morosidad para todas las cuotas existentes
UPDATE cuotas
SET monto_morosidad = GREATEST(0, monto_cuota - COALESCE(total_pagado, 0));

-- ============================================================================
-- PASO 4: Verificar Actualización
-- ============================================================================

-- Verificar cuotas con morosidad
SELECT 
    'VERIFICACIÓN: Cuotas con morosidad' as verificacion,
    COUNT(*) as total_cuotas,
    COUNT(CASE WHEN dias_morosidad > 0 THEN 1 END) as cuotas_con_dias_morosidad,
    COUNT(CASE WHEN monto_morosidad > 0 THEN 1 END) as cuotas_con_monto_morosidad,
    SUM(dias_morosidad) as total_dias_morosidad,
    SUM(monto_morosidad) as total_monto_morosidad
FROM cuotas;

-- Verificar distribución de días de morosidad
SELECT 
    'DISTRIBUCIÓN: Días de morosidad' as verificacion,
    CASE
        WHEN dias_morosidad = 0 THEN '0 días (al día)'
        WHEN dias_morosidad BETWEEN 1 AND 5 THEN '1-5 días'
        WHEN dias_morosidad BETWEEN 6 AND 15 THEN '6-15 días'
        WHEN dias_morosidad BETWEEN 16 AND 30 THEN '16-30 días (1 mes)'
        WHEN dias_morosidad BETWEEN 31 AND 60 THEN '31-60 días (2 meses)'
        WHEN dias_morosidad BETWEEN 61 AND 90 THEN '61-90 días (3 meses)'
        WHEN dias_morosidad BETWEEN 91 AND 180 THEN '91-180 días (4-6 meses)'
        WHEN dias_morosidad BETWEEN 181 AND 365 THEN '181-365 días (6-12 meses)'
        ELSE 'Más de 1 año'
    END as rango_dias,
    COUNT(*) as cantidad_cuotas,
    SUM(monto_morosidad) as monto_total
FROM cuotas
WHERE dias_morosidad > 0
GROUP BY 
    CASE
        WHEN dias_morosidad = 0 THEN '0 días (al día)'
        WHEN dias_morosidad BETWEEN 1 AND 5 THEN '1-5 días'
        WHEN dias_morosidad BETWEEN 6 AND 15 THEN '6-15 días'
        WHEN dias_morosidad BETWEEN 16 AND 30 THEN '16-30 días (1 mes)'
        WHEN dias_morosidad BETWEEN 31 AND 60 THEN '31-60 días (2 meses)'
        WHEN dias_morosidad BETWEEN 61 AND 90 THEN '61-90 días (3 meses)'
        WHEN dias_morosidad BETWEEN 91 AND 180 THEN '91-180 días (4-6 meses)'
        WHEN dias_morosidad BETWEEN 181 AND 365 THEN '181-365 días (6-12 meses)'
        ELSE 'Más de 1 año'
    END
ORDER BY MIN(dias_morosidad);

-- ============================================================================
-- PASO 5: Verificar Consistencia
-- ============================================================================

-- Verificar que monto_morosidad = monto_cuota - total_pagado
SELECT 
    'VERIFICACIÓN: Consistencia monto_morosidad' as verificacion,
    COUNT(*) as total_cuotas,
    COUNT(CASE WHEN ABS(monto_morosidad - (monto_cuota - COALESCE(total_pagado, 0))) > 0.01 THEN 1 END) as inconsistencias
FROM cuotas;

-- ============================================================================
-- ✅ MIGRACIÓN COMPLETADA
-- ============================================================================
-- NOTA: Estas columnas se actualizarán automáticamente cuando:
--   1. Se registre un pago (función _aplicar_monto_a_cuota)
--   2. Se actualice el estado de una cuota (función _actualizar_estado_cuota)
--   3. Se ejecute el script de actualización periódica (si se implementa)
-- ============================================================================

