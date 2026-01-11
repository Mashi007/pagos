-- ============================================================================
-- SCRIPT SQL: FASE 3 - DIAGNÓSTICO DE COLUMNAS
-- Objetivo: Verificar qué columnas existen en BD vs Modelo ORM
-- Fecha: 2026-01-11
-- ============================================================================

-- ============================================================================
-- PASO 1: Verificar columnas ML en tabla prestamos
-- ============================================================================

SELECT 
    'PASO 1: Columnas ML en prestamos' AS paso,
    column_name,
    data_type,
    is_nullable,
    CASE 
        WHEN column_name IN (
            'ml_impago_calculado_en',
            'ml_impago_modelo_id',
            'ml_impago_nivel_riesgo_calculado',
            'ml_impago_probabilidad_calculada'
        ) THEN '✅ Existe en BD'
        ELSE '❌ No existe en BD'
    END AS estado_modelo
FROM information_schema.columns
WHERE table_name = 'prestamos'
  AND column_name LIKE 'ml_impago%'
ORDER BY column_name;

-- ============================================================================
-- PASO 2: Verificar columnas faltantes en tabla pagos
-- ============================================================================

SELECT 
    'PASO 2: Columnas faltantes en pagos' AS paso,
    CASE 
        WHEN column_name IN (
            'banco', 'codigo_pago', 'comprobante', 'creado_en', 'descuento',
            'dias_mora', 'documento', 'fecha_vencimiento', 'hora_pago', 'metodo_pago',
            'monto', 'monto_capital', 'monto_cuota_programado', 'monto_interes',
            'monto_mora', 'monto_total', 'numero_operacion', 'observaciones',
            'referencia_pago', 'tasa_mora', 'tipo_pago'
        ) THEN column_name
        ELSE NULL
    END AS columna_esperada,
    CASE 
        WHEN column_name IN (
            'banco', 'codigo_pago', 'comprobante', 'creado_en', 'descuento',
            'dias_mora', 'documento', 'fecha_vencimiento', 'hora_pago', 'metodo_pago',
            'monto', 'monto_capital', 'monto_cuota_programado', 'monto_interes',
            'monto_mora', 'monto_total', 'numero_operacion', 'observaciones',
            'referencia_pago', 'tasa_mora', 'tipo_pago'
        ) THEN '✅ Existe en BD'
        ELSE NULL
    END AS estado
FROM information_schema.columns
WHERE table_name = 'pagos'
  AND column_name IN (
    'banco', 'codigo_pago', 'comprobante', 'creado_en', 'descuento',
    'dias_mora', 'documento', 'fecha_vencimiento', 'hora_pago', 'metodo_pago',
    'monto', 'monto_capital', 'monto_cuota_programado', 'monto_interes',
    'monto_mora', 'monto_total', 'numero_operacion', 'observaciones',
    'referencia_pago', 'tasa_mora', 'tipo_pago'
  )
ORDER BY column_name;

-- ============================================================================
-- PASO 3: Verificar TODAS las columnas en tabla pagos (para referencia)
-- ============================================================================

SELECT 
    'PASO 3: Todas las columnas en pagos' AS paso,
    column_name,
    data_type,
    is_nullable,
    character_maximum_length
FROM information_schema.columns
WHERE table_name = 'pagos'
ORDER BY ordinal_position;

-- ============================================================================
-- PASO 4: Verificar columnas faltantes en tabla cuotas
-- ============================================================================

SELECT 
    'PASO 4: Columnas faltantes en cuotas' AS paso,
    CASE 
        WHEN column_name IN ('creado_en', 'actualizado_en') THEN column_name
        ELSE NULL
    END AS columna_esperada,
    CASE 
        WHEN column_name IN ('creado_en', 'actualizado_en') THEN '✅ Existe en BD'
        ELSE NULL
    END AS estado
FROM information_schema.columns
WHERE table_name = 'cuotas'
  AND column_name IN ('creado_en', 'actualizado_en')
ORDER BY column_name;

-- ============================================================================
-- PASO 5: Verificar TODAS las columnas en tabla cuotas (para referencia)
-- ============================================================================

SELECT 
    'PASO 5: Todas las columnas en cuotas' AS paso,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'cuotas'
ORDER BY ordinal_position;

-- ============================================================================
-- FIN DEL SCRIPT DE DIAGNÓSTICO
-- ============================================================================
