-- Migración 040: Agregar estado 'rechazado' a revision_manual_prestamos
-- Estados finales: pendiente | revisando | en_espera | rechazado | revisado
-- También agrega columna motivo_rechazo para guardar el motivo cuando se rechaza

BEGIN;

-- 1. Agregar columna motivo_rechazo si no existe
ALTER TABLE revision_manual_prestamos
    ADD COLUMN IF NOT EXISTS motivo_rechazo TEXT;

-- 2. Actualizar CHECK constraint para incluir 'rechazado'
DO $$
BEGIN
    ALTER TABLE revision_manual_prestamos
        DROP CONSTRAINT IF EXISTS check_estado_revision;
EXCEPTION WHEN OTHERS THEN
    NULL;
END $$;

ALTER TABLE revision_manual_prestamos
    ADD CONSTRAINT check_estado_revision
    CHECK (estado_revision IN ('pendiente', 'revisando', 'en_espera', 'rechazado', 'revisado'));

COMMIT;
