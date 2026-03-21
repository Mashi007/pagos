-- Script SQL: Migrar pagos aprobados a tabla temporal
-- 
-- Este script copia todos los pagos en estado "aprobado" 
-- a la tabla pagos_pendiente_descargar, evitando duplicados.
--
-- IMPORTANTE: Ejecutar DESPUÉS de aplicar migración Alembic 021
--
-- Uso en PostgreSQL:
--   psql -U usuario -d base_datos -f backend/sql_migrate_pagos_aprobados.sql

BEGIN;

-- 1. Obtener cantidad de pagos aprobados antes de migrar
SELECT 
    COUNT(*) as total_aprobados,
    COUNT(CASE WHEN id IN (SELECT pago_reportado_id FROM pagos_reportados_exportados) THEN 1 END) as ya_descargados,
    COUNT(CASE WHEN id IN (SELECT pago_reportado_id FROM pagos_pendiente_descargar) THEN 1 END) as ya_en_tabla_temporal
FROM pagos_reportados
WHERE estado = 'aprobado';

-- 2. Insertar pagos aprobados no-exportados a la tabla temporal
-- (evita duplicados con ON CONFLICT)
INSERT INTO pagos_pendiente_descargar (pago_reportado_id, created_at)
SELECT 
    pr.id,
    NOW()
FROM pagos_reportados pr
WHERE 
    -- Solo pagos aprobados
    pr.estado = 'aprobado'
    -- Que NO estén ya en la tabla temporal
    AND pr.id NOT IN (SELECT pago_reportado_id FROM pagos_pendiente_descargar)
    -- Que NO hayan sido descargados antes (no están marcados como exportados)
    AND pr.id NOT IN (SELECT pago_reportado_id FROM pagos_reportados_exportados)
ON CONFLICT (id) DO NOTHING;

-- 3. Reporte de migración
SELECT 
    'Pagos aprobados migrados: ' || COUNT(*) as resultado
FROM pagos_pendiente_descargar
WHERE created_at >= NOW() - INTERVAL '1 minute';

-- 4. Verificación final
SELECT 
    COUNT(*) as total_en_tabla_temporal,
    MIN(created_at) as mas_antiguo,
    MAX(created_at) as mas_nuevo
FROM pagos_pendiente_descargar;

COMMIT;
