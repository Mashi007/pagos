-- ==========================================
-- SCRIPT PARA VERIFICAR Y AGREGAR COLUMNAS
-- EN LA TABLA prestamos
-- ==========================================
-- Este script verifica y agrega las columnas:
-- - concesionario
-- - analista  
-- - modelo_vehiculo
-- - usuario_autoriza
-- ==========================================

BEGIN;

-- Verificar y agregar columna 'concesionario'
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'prestamos' AND column_name = 'concesionario'
    ) THEN
        ALTER TABLE prestamos ADD COLUMN concesionario VARCHAR(100);
        RAISE NOTICE 'Columna concesionario agregada';
    ELSE
        RAISE NOTICE 'Columna concesionario ya existe';
    END IF;
END $$;

-- Verificar y agregar columna 'analista'
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'prestamos' AND column_name = 'analista'
    ) THEN
        ALTER TABLE prestamos ADD COLUMN analista VARCHAR(100);
        RAISE NOTICE 'Columna analista agregada';
    ELSE
        RAISE NOTICE 'Columna analista ya existe';
    END IF;
END $$;

-- Verificar y agregar columna 'modelo_vehiculo'
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'prestamos' AND column_name = 'modelo_vehiculo'
    ) THEN
        ALTER TABLE prestamos ADD COLUMN modelo_vehiculo VARCHAR(100);
        RAISE NOTICE 'Columna modelo_vehiculo agregada';
    ELSE
        RAISE NOTICE 'Columna modelo_vehiculo ya existe';
    END IF;
END $$;

-- Verificar y agregar columna 'usuario_autoriza'
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'prestamos' AND column_name = 'usuario_autoriza'
    ) THEN
        ALTER TABLE prestamos ADD COLUMN usuario_autoriza VARCHAR(100);
        RAISE NOTICE 'Columna usuario_autoriza agregada';
    ELSE
        RAISE NOTICE 'Columna usuario_autoriza ya existe';
    END IF;
END $$;

COMMIT;

-- Verificar resultado
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns
WHERE table_name = 'prestamos' 
    AND column_name IN ('concesionario', 'analista', 'modelo_vehiculo', 'usuario_autoriza')
ORDER BY column_name;

