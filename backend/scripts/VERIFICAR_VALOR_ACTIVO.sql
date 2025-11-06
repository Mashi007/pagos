-- ============================================
-- SCRIPT DE VERIFICACIÓN: Campo valor_activo en prestamos
-- ============================================
-- Este script verifica que la columna valor_activo existe y está correctamente configurada
-- Fecha: 2025-01-15
-- ============================================

-- 1. Verificar que la columna existe
SELECT 
    column_name,
    data_type,
    numeric_precision,
    numeric_scale,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'prestamos' 
  AND column_name = 'valor_activo';

-- 2. Verificar estructura de la tabla prestamos (mostrar todas las columnas de DATOS DEL PRÉSTAMO)
SELECT 
    column_name,
    data_type,
    numeric_precision,
    numeric_scale,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'prestamos' 
  AND column_name IN (
    'valor_activo',
    'total_financiamiento',
    'fecha_requerimiento',
    'modalidad_pago',
    'numero_cuotas',
    'cuota_periodo',
    'tasa_interes',
    'fecha_base_calculo',
    'producto',
    'producto_financiero'
  )
ORDER BY 
    CASE column_name
        WHEN 'valor_activo' THEN 1
        WHEN 'total_financiamiento' THEN 2
        WHEN 'fecha_requerimiento' THEN 3
        WHEN 'modalidad_pago' THEN 4
        WHEN 'numero_cuotas' THEN 5
        WHEN 'cuota_periodo' THEN 6
        WHEN 'tasa_interes' THEN 7
        WHEN 'fecha_base_calculo' THEN 8
        WHEN 'producto' THEN 9
        WHEN 'producto_financiero' THEN 10
    END;

-- 3. Verificar datos existentes (muestra valor_activo si existe en algunos registros)
SELECT 
    id,
    cedula,
    valor_activo,
    total_financiamiento,
    modelo_vehiculo,
    fecha_registro
FROM prestamos
ORDER BY fecha_registro DESC
LIMIT 10;

-- 4. Estadísticas de valor_activo
SELECT 
    COUNT(*) as total_prestamos,
    COUNT(valor_activo) as prestamos_con_valor_activo,
    COUNT(*) - COUNT(valor_activo) as prestamos_sin_valor_activo,
    AVG(valor_activo) as valor_activo_promedio,
    MIN(valor_activo) as valor_activo_minimo,
    MAX(valor_activo) as valor_activo_maximo
FROM prestamos;

