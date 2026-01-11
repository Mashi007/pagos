
-- ============================================================================
-- Script SQL generado para auditoría de coherencia
-- Ejecutar este script para obtener estructura real de la base de datos
-- ============================================================================

-- Obtener todas las columnas de las tablas principales
SELECT 
    table_name AS tabla,
    column_name AS columna,
    data_type AS tipo_dato,
    character_maximum_length AS longitud_maxima,
    numeric_precision AS precision_numerica,
    numeric_scale AS escala_numerica,
    is_nullable AS nullable,
    column_default AS valor_por_defecto
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name IN ('pagos', 'cuotas', 'prestamos', 'clientes', 'amortizacion', 'notificaciones', 'users')
ORDER BY table_name, ordinal_position;
