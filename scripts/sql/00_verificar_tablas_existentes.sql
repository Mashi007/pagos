-- =====================================================
-- SCRIPT DE VERIFICACIÓN DE TABLAS EXISTENTES
-- Ejecutar PRIMERO para ver qué tablas existen
-- =====================================================

-- Verificar todas las tablas relacionadas con auditoría y pagos
SELECT 
    table_name,
    CASE 
        WHEN table_name IN ('pagos', 'prestamos', 'clientes', 'prestamos_evaluacion') THEN '✅ CRÍTICA'
        WHEN table_name IN ('pagos_auditoria', 'prestamos_auditoria') THEN '⚠️ OPCIONAL'
        ELSE 'ℹ️ OTRA'
    END as tipo,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as num_columnas
FROM information_schema.tables t
WHERE table_schema = 'public'
  AND table_name IN (
    'pagos',
    'prestamos',
    'clientes',
    'prestamos_evaluacion',
    'pagos_auditoria',
    'prestamos_auditoria',
    'concesionarios',
    'analistas',
    'modelos_vehiculos'
  )
ORDER BY 
    CASE 
        WHEN table_name IN ('pagos', 'prestamos', 'clientes', 'prestamos_evaluacion') THEN 1
        WHEN table_name IN ('pagos_auditoria', 'prestamos_auditoria') THEN 2
        ELSE 3
    END,
    table_name;

-- Verificar si las tablas de auditoría existen
SELECT 
    CASE 
        WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'pagos_auditoria') 
        THEN '✅ EXISTE' 
        ELSE '❌ NO EXISTE' 
    END as pagos_auditoria,
    CASE 
        WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'prestamos_auditoria') 
        THEN '✅ EXISTE' 
        ELSE '❌ NO EXISTE' 
    END as prestamos_auditoria;

