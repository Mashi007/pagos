-- ============================================================================
-- 📋 VERIFICAR ESTRUCTURA DE TABLAS - PRÉSTAMOS Y CUOTAS
-- ============================================================================
-- Script para DBeaver: Muestra solo la estructura de las tablas
-- Tablas: prestamos, cuotas, clientes
-- ============================================================================

-- ============================================================================
-- 1. ESTRUCTURA DE TABLA: prestamos
-- ============================================================================
-- Campos importantes:
--   - fecha_aprobacion: TIMESTAMP (fecha cuando se aprueba el préstamo)
--   - fecha_base_calculo: DATE (fecha base para generar tabla de amortización)
--   - estado: VARCHAR (DRAFT, EN_REVISION, APROBADO, RECHAZADO, FINALIZADO)
-- ============================================================================
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default,
    CASE 
        WHEN column_name = 'fecha_aprobacion' THEN '✅ Fecha cuando se aprueba el préstamo'
        WHEN column_name = 'fecha_base_calculo' THEN '✅ Fecha base para generar tabla de amortización'
        WHEN column_name = 'estado' THEN '✅ Estado del préstamo (DRAFT, APROBADO, etc.)'
        WHEN column_name = 'id' THEN '✅ ID único del préstamo (autoincremento)'
        WHEN column_name = 'cliente_id' THEN '✅ Foreign Key a tabla clientes'
        ELSE ''
    END as descripcion
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'prestamos'
ORDER BY ordinal_position;

-- ============================================================================
-- 2. ESTRUCTURA DE TABLA: cuotas
-- ============================================================================
-- Campos importantes:
--   - fecha_vencimiento: DATE (fecha de vencimiento de cada cuota)
--   - prestamo_id: INTEGER (Foreign Key a tabla prestamos)
--   - numero_cuota: INTEGER (número de cuota)
-- ============================================================================
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default,
    CASE 
        WHEN column_name = 'fecha_vencimiento' THEN '✅ Fecha de vencimiento calculada desde fecha_base_calculo'
        WHEN column_name = 'prestamo_id' THEN '✅ Foreign Key a tabla prestamos'
        WHEN column_name = 'numero_cuota' THEN '✅ Número de cuota (1, 2, 3, ...)'
        WHEN column_name = 'estado' THEN '✅ Estado de la cuota (PENDIENTE, PAGADO, PARCIAL, etc.)'
        WHEN column_name = 'monto_cuota' THEN '✅ Monto total de la cuota'
        WHEN column_name = 'total_pagado' THEN '✅ Monto total pagado en esta cuota'
        ELSE ''
    END as descripcion
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'cuotas'
ORDER BY ordinal_position;

-- ============================================================================
-- 3. ESTRUCTURA DE TABLA: clientes
-- ============================================================================
-- Campos importantes:
--   - estado: VARCHAR (ACTIVO, INACTIVO, FINALIZADO)
--   - activo: BOOLEAN (sincronizado con estado)
-- ============================================================================
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default,
    CASE 
        WHEN column_name = 'estado' THEN '✅ Estado del cliente (ACTIVO, INACTIVO, FINALIZADO)'
        WHEN column_name = 'activo' THEN '✅ Boolean sincronizado con estado'
        WHEN column_name = 'id' THEN '✅ ID único del cliente'
        WHEN column_name = 'cedula' THEN '✅ Cédula del cliente (usado para búsqueda)'
        ELSE ''
    END as descripcion
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'clientes'
ORDER BY ordinal_position;

-- ============================================================================
-- 4. VERIFICAR RELACIONES (Foreign Keys)
-- ============================================================================
SELECT 
    tc.table_name as tabla_origen,
    kcu.column_name as columna_origen,
    ccu.table_name as tabla_destino,
    ccu.column_name as columna_destino,
    tc.constraint_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
  AND tc.table_name IN ('prestamos', 'cuotas')
ORDER BY tc.table_name, kcu.column_name;

-- ============================================================================
-- 5. RESUMEN DE CAMPOS CLAVE
-- ============================================================================
SELECT 
    'prestamos' as tabla,
    'fecha_aprobacion' as campo,
    'TIMESTAMP' as tipo,
    'Fecha cuando se aprueba el préstamo' as descripcion
UNION ALL
SELECT 
    'prestamos' as tabla,
    'fecha_base_calculo' as campo,
    'DATE' as tipo,
    'Fecha base para generar tabla de amortización' as descripcion
UNION ALL
SELECT 
    'prestamos' as tabla,
    'estado' as campo,
    'VARCHAR' as tipo,
    'Estado del préstamo (DRAFT, APROBADO, etc.)' as descripcion
UNION ALL
SELECT 
    'prestamos' as tabla,
    'id' as campo,
    'INTEGER' as tipo,
    'ID único del préstamo (autoincremento)' as descripcion
UNION ALL
SELECT 
    'cuotas' as tabla,
    'fecha_vencimiento' as campo,
    'DATE' as tipo,
    'Fecha de vencimiento calculada desde fecha_base_calculo' as descripcion
UNION ALL
SELECT 
    'cuotas' as tabla,
    'prestamo_id' as campo,
    'INTEGER' as tipo,
    'Foreign Key a tabla prestamos' as descripcion
UNION ALL
SELECT 
    'clientes' as tabla,
    'estado' as campo,
    'VARCHAR' as tipo,
    'Estado del cliente (ACTIVO, INACTIVO, FINALIZADO)' as descripcion
ORDER BY tabla, campo;

