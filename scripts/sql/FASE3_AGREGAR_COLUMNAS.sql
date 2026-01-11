-- ============================================================================
-- SCRIPT SQL: FASE 3 - AGREGAR COLUMNAS FALTANTES
-- Objetivo: Agregar columnas faltantes en tablas pagos y cuotas
-- Fecha: 2026-01-11
-- ============================================================================
-- INSTRUCCIONES:
-- 1. Ejecutar este script después de ejecutar FASE3_DIAGNOSTICO_COLUMNAS.sql
-- 2. Revisar qué columnas realmente faltan antes de ejecutar
-- 3. Este script usa IF NOT EXISTS para evitar errores si las columnas ya existen
-- ============================================================================

-- ============================================================================
-- TABLA PAGOS: Agregar 21 columnas faltantes
-- ============================================================================

-- Información bancaria y método de pago
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'pagos' AND column_name = 'banco') THEN
        ALTER TABLE pagos ADD COLUMN banco VARCHAR(100);
        RAISE NOTICE '✅ Columna banco agregada a tabla pagos';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'pagos' AND column_name = 'metodo_pago') THEN
        ALTER TABLE pagos ADD COLUMN metodo_pago VARCHAR(50);
        RAISE NOTICE '✅ Columna metodo_pago agregada a tabla pagos';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'pagos' AND column_name = 'tipo_pago') THEN
        ALTER TABLE pagos ADD COLUMN tipo_pago VARCHAR(50);
        RAISE NOTICE '✅ Columna tipo_pago agregada a tabla pagos';
    END IF;
END $$;

-- Códigos y referencias
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'pagos' AND column_name = 'codigo_pago') THEN
        ALTER TABLE pagos ADD COLUMN codigo_pago VARCHAR(30);
        RAISE NOTICE '✅ Columna codigo_pago agregada a tabla pagos';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'pagos' AND column_name = 'numero_operacion') THEN
        ALTER TABLE pagos ADD COLUMN numero_operacion VARCHAR(50);
        RAISE NOTICE '✅ Columna numero_operacion agregada a tabla pagos';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'pagos' AND column_name = 'referencia_pago') THEN
        ALTER TABLE pagos ADD COLUMN referencia_pago VARCHAR(100);
        RAISE NOTICE '✅ Columna referencia_pago agregada a tabla pagos';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'pagos' AND column_name = 'comprobante') THEN
        ALTER TABLE pagos ADD COLUMN comprobante VARCHAR(200);
        RAISE NOTICE '✅ Columna comprobante agregada a tabla pagos';
    END IF;
END $$;

-- Documentación
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'pagos' AND column_name = 'documento') THEN
        ALTER TABLE pagos ADD COLUMN documento VARCHAR(50);
        RAISE NOTICE '✅ Columna documento agregada a tabla pagos';
    END IF;
END $$;

-- Montos detallados
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'pagos' AND column_name = 'monto') THEN
        ALTER TABLE pagos ADD COLUMN monto NUMERIC(12, 2);
        RAISE NOTICE '✅ Columna monto agregada a tabla pagos';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'pagos' AND column_name = 'monto_capital') THEN
        ALTER TABLE pagos ADD COLUMN monto_capital NUMERIC(12, 2);
        RAISE NOTICE '✅ Columna monto_capital agregada a tabla pagos';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'pagos' AND column_name = 'monto_interes') THEN
        ALTER TABLE pagos ADD COLUMN monto_interes NUMERIC(12, 2);
        RAISE NOTICE '✅ Columna monto_interes agregada a tabla pagos';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'pagos' AND column_name = 'monto_cuota_programado') THEN
        ALTER TABLE pagos ADD COLUMN monto_cuota_programado NUMERIC(12, 2);
        RAISE NOTICE '✅ Columna monto_cuota_programado agregada a tabla pagos';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'pagos' AND column_name = 'monto_mora') THEN
        ALTER TABLE pagos ADD COLUMN monto_mora NUMERIC(12, 2);
        RAISE NOTICE '✅ Columna monto_mora agregada a tabla pagos';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'pagos' AND column_name = 'monto_total') THEN
        ALTER TABLE pagos ADD COLUMN monto_total NUMERIC(12, 2);
        RAISE NOTICE '✅ Columna monto_total agregada a tabla pagos';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'pagos' AND column_name = 'descuento') THEN
        ALTER TABLE pagos ADD COLUMN descuento NUMERIC(12, 2);
        RAISE NOTICE '✅ Columna descuento agregada a tabla pagos';
    END IF;
END $$;

-- Información de mora y vencimiento
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'pagos' AND column_name = 'dias_mora') THEN
        ALTER TABLE pagos ADD COLUMN dias_mora INTEGER;
        RAISE NOTICE '✅ Columna dias_mora agregada a tabla pagos';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'pagos' AND column_name = 'tasa_mora') THEN
        ALTER TABLE pagos ADD COLUMN tasa_mora NUMERIC(5, 2);
        RAISE NOTICE '✅ Columna tasa_mora agregada a tabla pagos';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'pagos' AND column_name = 'fecha_vencimiento') THEN
        ALTER TABLE pagos ADD COLUMN fecha_vencimiento TIMESTAMP;
        RAISE NOTICE '✅ Columna fecha_vencimiento agregada a tabla pagos';
    END IF;
END $$;

-- Fechas y horas adicionales
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'pagos' AND column_name = 'hora_pago') THEN
        ALTER TABLE pagos ADD COLUMN hora_pago VARCHAR(10);
        RAISE NOTICE '✅ Columna hora_pago agregada a tabla pagos';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'pagos' AND column_name = 'creado_en') THEN
        ALTER TABLE pagos ADD COLUMN creado_en TIMESTAMP;
        RAISE NOTICE '✅ Columna creado_en agregada a tabla pagos';
    END IF;
END $$;

-- Observaciones adicionales
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'pagos' AND column_name = 'observaciones') THEN
        ALTER TABLE pagos ADD COLUMN observaciones TEXT;
        RAISE NOTICE '✅ Columna observaciones agregada a tabla pagos';
    END IF;
END $$;

-- ============================================================================
-- TABLA CUOTAS: Agregar 2 columnas faltantes
-- ============================================================================

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'cuotas' AND column_name = 'creado_en') THEN
        ALTER TABLE cuotas ADD COLUMN creado_en DATE;
        RAISE NOTICE '✅ Columna creado_en agregada a tabla cuotas';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'cuotas' AND column_name = 'actualizado_en') THEN
        ALTER TABLE cuotas ADD COLUMN actualizado_en DATE;
        RAISE NOTICE '✅ Columna actualizado_en agregada a tabla cuotas';
    END IF;
END $$;

-- ============================================================================
-- VERIFICACIÓN FINAL
-- ============================================================================

SELECT 
    'VERIFICACIÓN FINAL' AS paso,
    'Columnas agregadas correctamente' AS resultado,
    COUNT(*) AS total_columnas_pagos
FROM information_schema.columns
WHERE table_name = 'pagos'
  AND column_name IN (
    'banco', 'metodo_pago', 'tipo_pago', 'codigo_pago', 'numero_operacion',
    'referencia_pago', 'comprobante', 'documento', 'monto', 'monto_capital',
    'monto_interes', 'monto_cuota_programado', 'monto_mora', 'monto_total',
    'descuento', 'dias_mora', 'tasa_mora', 'fecha_vencimiento', 'hora_pago',
    'creado_en', 'observaciones'
  );

SELECT 
    'VERIFICACIÓN FINAL' AS paso,
    'Columnas agregadas correctamente' AS resultado,
    COUNT(*) AS total_columnas_cuotas
FROM information_schema.columns
WHERE table_name = 'cuotas'
  AND column_name IN ('creado_en', 'actualizado_en');

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
