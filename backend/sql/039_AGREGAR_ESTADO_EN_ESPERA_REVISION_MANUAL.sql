-- Migración: Agregar soporte para estado "en_espera" en revisión manual de préstamos
-- Descripción: Extiende los estados de revisión de 3 a 4: pendiente, revisando, en_espera, revisado

-- Verificar que la tabla existe y actualizar documentación de restricción
-- NOTA: En PostgreSQL, los CHECK constraints con valores específicos se definen en la creación de tabla
-- Por ahora simplemente expandimos el rango de valores permitidos documentándolo

-- Si necesitas una restricción más estricta, ejecuta esto:
-- ALTER TABLE revision_manual_prestamos 
-- DROP CONSTRAINT IF EXISTS check_estado_revision;
-- 
-- ALTER TABLE revision_manual_prestamos
-- ADD CONSTRAINT check_estado_revision 
-- CHECK (estado_revision IN ('pendiente', 'revisando', 'en_espera', 'revisado'));

-- Para PostgreSQL (si ya existe la tabla y tienes constraint anterior):
BEGIN;

-- Intentar actualizar el constraint (si existe)
DO $$
BEGIN
    -- En caso de que existe uno anterior, lo droppeamos
    ALTER TABLE revision_manual_prestamos 
    DROP CONSTRAINT IF EXISTS check_estado_revision;
EXCEPTION WHEN OTHERS THEN
    NULL; -- Ignorar si no existe
END $$;

-- Agregar el nuevo constraint que permite los 4 estados
ALTER TABLE revision_manual_prestamos
ADD CONSTRAINT check_estado_revision 
CHECK (estado_revision IN ('pendiente', 'revisando', 'en_espera', 'revisado'));

COMMIT;
