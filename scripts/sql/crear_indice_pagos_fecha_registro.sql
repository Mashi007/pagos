-- Script SQL para crear el índice ix_pagos_fecha_registro
-- Detectado como faltante en auditoría integral del endpoint /pagos
-- Fecha: 2026-01-10

-- Verificar si el índice ya existe antes de crearlo
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM pg_indexes 
        WHERE tablename = 'pagos' 
        AND indexname = 'ix_pagos_fecha_registro'
    ) THEN
        CREATE INDEX ix_pagos_fecha_registro ON pagos (fecha_registro);
        RAISE NOTICE '✅ Índice ix_pagos_fecha_registro creado exitosamente';
    ELSE
        RAISE NOTICE 'ℹ️ Índice ix_pagos_fecha_registro ya existe, omitiendo...';
    END IF;
END $$;

-- Verificar que el índice fue creado
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'pagos' 
AND indexname = 'ix_pagos_fecha_registro';
