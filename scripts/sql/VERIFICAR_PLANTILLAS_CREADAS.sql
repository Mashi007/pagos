-- ============================================
-- VERIFICAR PLANTILLAS CREADAS
-- ============================================

-- Verificar que la tabla existe
SELECT 
    table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
    AND table_name = 'notificacion_plantillas';

-- Ver todas las plantillas
SELECT 
    id,
    nombre,
    tipo,
    activa,
    zona_horaria,
    fecha_creacion
FROM notificacion_plantillas
ORDER BY tipo;

-- Contar plantillas por tipo
SELECT 
    tipo,
    COUNT(*) as cantidad,
    SUM(CASE WHEN activa THEN 1 ELSE 0 END) as activas
FROM notificacion_plantillas
GROUP BY tipo
ORDER BY tipo;

