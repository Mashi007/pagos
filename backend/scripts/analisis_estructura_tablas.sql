-- ============================================
-- SCRIPT SQL PARA ANÁLISIS COMPLETO DE ESTRUCTURA DE TABLAS
-- ============================================
-- Análisis detallado de todas las columnas de cada tabla del sistema
-- Para configuración completa del sistema de auditoría

-- 1. ANÁLISIS DE ESTRUCTURA DE TODAS LAS TABLAS
-- ============================================

-- Mostrar todas las tablas del sistema
SELECT 
    'TABLAS DEL SISTEMA' as analisis,
    table_name,
    table_type
FROM information_schema.tables 
WHERE table_schema = 'public' 
    AND table_name NOT LIKE 'pg_%'
    AND table_name NOT LIKE 'sql_%'
ORDER BY table_name;

-- 2. ESTRUCTURA DETALLADA DE CADA TABLA
-- ============================================

-- TABLA: usuarios
SELECT 
    'USUARIOS' as tabla,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns 
WHERE table_name = 'usuarios'
ORDER BY ordinal_position;

-- TABLA: clientes
SELECT 
    'CLIENTES' as tabla,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns 
WHERE table_name = 'clientes'
ORDER BY ordinal_position;

-- TABLA: prestamos
SELECT 
    'PRESTAMOS' as tabla,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns 
WHERE table_name = 'prestamos'
ORDER BY ordinal_position;

-- TABLA: pagos
SELECT 
    'PAGOS' as tabla,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns 
WHERE table_name = 'pagos'
ORDER BY ordinal_position;

-- TABLA: auditorias
SELECT 
    'AUDITORIAS' as tabla,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns 
WHERE table_name = 'auditorias'
ORDER BY ordinal_position;

-- TABLA: configuracion_sistema
SELECT 
    'CONFIGURACION_SISTEMA' as tabla,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns 
WHERE table_name = 'configuracion_sistema'
ORDER BY ordinal_position;

-- TABLA: amortizacion (si existe)
SELECT 
    'AMORTIZACION' as tabla,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns 
WHERE table_name = 'amortizacion'
ORDER BY ordinal_position;

-- TABLA: conciliacion (si existe)
SELECT 
    'CONCILIACION' as tabla,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns 
WHERE table_name = 'conciliacion'
ORDER BY ordinal_position;

-- TABLA: notificaciones (si existe)
SELECT 
    'NOTIFICACIONES' as tabla,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns 
WHERE table_name = 'notificaciones'
ORDER BY ordinal_position;

-- TABLA: aprobaciones (si existe)
SELECT 
    'APROBACIONES' as tabla,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns 
WHERE table_name = 'aprobaciones'
ORDER BY ordinal_position;

-- TABLA: analistas (si existe)
SELECT 
    'ANALISTAS' as tabla,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns 
WHERE table_name = 'analistas'
ORDER BY ordinal_position;

-- TABLA: concesionarios (si existe)
SELECT 
    'CONCESIONARIOS' as tabla,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns 
WHERE table_name = 'concesionarios'
ORDER BY ordinal_position;

-- TABLA: modelos_vehiculos (si existe)
SELECT 
    'MODELOS_VEHICULOS' as tabla,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns 
WHERE table_name = 'modelos_vehiculos'
ORDER BY ordinal_position;

-- 3. ANÁLISIS DE RELACIONES (FOREIGN KEYS)
-- ============================================

-- Mostrar todas las relaciones entre tablas
SELECT 
    'RELACIONES ENTRE TABLAS' as analisis,
    tc.table_name as tabla_origen,
    kcu.column_name as columna_origen,
    ccu.table_name AS tabla_destino,
    ccu.column_name AS columna_destino,
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
ORDER BY tc.table_name, kcu.column_name;

-- 4. ANÁLISIS DE ÍNDICES
-- ============================================

-- Mostrar todos los índices del sistema
SELECT 
    'INDICES DEL SISTEMA' as analisis,
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- 5. ANÁLISIS DE ENUMS Y TIPOS PERSONALIZADOS
-- ============================================

-- Mostrar tipos personalizados (enums)
SELECT 
    'TIPOS PERSONALIZADOS' as analisis,
    t.typname as nombre_tipo,
    e.enumlabel as valor_enum
FROM pg_type t 
JOIN pg_enum e ON t.oid = e.enumtypid  
WHERE t.typname LIKE '%role%' OR t.typname LIKE '%estado%' OR t.typname LIKE '%tipo%'
ORDER BY t.typname, e.enumsortorder;

-- 6. RESUMEN DE COLUMNAS POR TABLA
-- ============================================

-- Resumen de columnas por tabla
SELECT 
    'RESUMEN DE COLUMNAS' as analisis,
    table_name,
    COUNT(*) as total_columnas,
    COUNT(CASE WHEN is_nullable = 'NO' THEN 1 END) as columnas_obligatorias,
    COUNT(CASE WHEN column_default IS NOT NULL THEN 1 END) as columnas_con_default,
    COUNT(CASE WHEN data_type LIKE '%CHAR%' THEN 1 END) as columnas_texto,
    COUNT(CASE WHEN data_type IN ('integer', 'bigint', 'smallint') THEN 1 END) as columnas_enteras,
    COUNT(CASE WHEN data_type IN ('numeric', 'decimal') THEN 1 END) as columnas_decimales,
    COUNT(CASE WHEN data_type LIKE '%date%' OR data_type LIKE '%time%' THEN 1 END) as columnas_fecha
FROM information_schema.columns 
WHERE table_schema = 'public'
GROUP BY table_name
ORDER BY table_name;

-- 7. ANÁLISIS DE DATOS DE AUDITORÍA
-- ============================================

-- Verificar si hay datos en auditoría
SELECT 
    'DATOS DE AUDITORIA' as analisis,
    COUNT(*) as total_registros,
    COUNT(DISTINCT usuario_email) as usuarios_unicos,
    COUNT(DISTINCT modulo) as modulos_afectados,
    COUNT(DISTINCT accion) as tipos_accion,
    MIN(fecha) as fecha_mas_antigua,
    MAX(fecha) as fecha_mas_reciente
FROM auditorias;

-- 8. CONFIGURACIÓN DE AUDITORÍA POR TABLA
-- ============================================

-- Mostrar configuración recomendada de auditoría por tabla
SELECT 
    'CONFIGURACION AUDITORIA POR TABLA' as analisis,
    table_name,
    CASE 
        WHEN table_name = 'usuarios' THEN 'USUARIOS'
        WHEN table_name = 'clientes' THEN 'CLIENTES'
        WHEN table_name = 'prestamos' THEN 'PRESTAMOS'
        WHEN table_name = 'pagos' THEN 'PAGOS'
        WHEN table_name = 'auditorias' THEN 'AUDITORIA'
        WHEN table_name = 'configuracion_sistema' THEN 'CONFIGURACION'
        ELSE UPPER(table_name)
    END as modulo_auditoria,
    CASE 
        WHEN table_name IN ('usuarios', 'clientes', 'prestamos', 'pagos') THEN 'ALTA'
        WHEN table_name IN ('auditorias', 'configuracion_sistema') THEN 'CRITICA'
        ELSE 'MEDIA'
    END as prioridad_auditoria,
    COUNT(*) as columnas_a_auditar
FROM information_schema.columns 
WHERE table_schema = 'public'
GROUP BY table_name
ORDER BY 
    CASE 
        WHEN table_name IN ('usuarios', 'clientes', 'prestamos', 'pagos') THEN 1
        WHEN table_name IN ('auditorias', 'configuracion_sistema') THEN 2
        ELSE 3
    END,
    table_name;

-- 9. VERIFICACIÓN DE INTEGRIDAD DE DATOS
-- ============================================

-- Verificar integridad de datos críticos
SELECT 
    'VERIFICACION INTEGRIDAD' as analisis,
    'usuarios' as tabla,
    COUNT(*) as total_registros,
    COUNT(CASE WHEN email IS NOT NULL THEN 1 END) as con_email,
    COUNT(CASE WHEN is_active = true THEN 1 END) as activos
FROM usuarios
UNION ALL
SELECT 
    'VERIFICACION INTEGRIDAD',
    'clientes',
    COUNT(*),
    COUNT(CASE WHEN cedula IS NOT NULL THEN 1 END),
    COUNT(CASE WHEN activo = true THEN 1 END)
FROM clientes
UNION ALL
SELECT 
    'VERIFICACION INTEGRIDAD',
    'prestamos',
    COUNT(*),
    COUNT(CASE WHEN cliente_id IS NOT NULL THEN 1 END),
    COUNT(CASE WHEN estado = 'ACTIVO' THEN 1 END)
FROM prestamos
UNION ALL
SELECT 
    'VERIFICACION INTEGRIDAD',
    'pagos',
    COUNT(*),
    COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END),
    COUNT(CASE WHEN estado = 'CONFIRMADO' THEN 1 END)
FROM pagos;

-- 10. REPORTE FINAL DE ESTRUCTURA
-- ============================================

-- Generar reporte final
SELECT 
    '🎯 REPORTE FINAL DE ESTRUCTURA DE BASE DE DATOS' as titulo,
    NOW() as fecha_analisis,
    'Sistema de Préstamos y Cobranza' as sistema,
    'Análisis completo para configuración de auditoría' as proposito;

-- Mostrar recomendaciones de auditoría
SELECT 
    'RECOMENDACIONES DE AUDITORIA' as seccion,
    'TABLAS CRÍTICAS' as categoria,
    'usuarios, clientes, prestamos, pagos' as tablas,
    'Auditoría completa - todas las operaciones' as recomendacion
UNION ALL
SELECT 
    'RECOMENDACIONES DE AUDITORIA',
    'TABLAS DE CONFIGURACIÓN',
    'configuracion_sistema, auditorias',
    'Auditoría de cambios - solo modificaciones'
UNION ALL
SELECT 
    'RECOMENDACIONES DE AUDITORIA',
    'TABLAS DE SOPORTE',
    'notificaciones, aprobaciones, analistas',
    'Auditoría básica - operaciones importantes';

-- ============================================
-- FIN DEL ANÁLISIS DE ESTRUCTURA
-- ============================================
