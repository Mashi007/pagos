-- ============================================
-- SCRIPT PARA ELIMINAR COLUMNAS DUPLICADAS EN TABLA clientes
-- ============================================
-- FILAS A ELIMINAR: 19, 20, 21, 22, 23, 24, 25, 26
-- Columnas duplicadas/obsoletas

-- ⚠️ IMPORTANTE: Hacer BACKUP de la base de datos ANTES de ejecutar
-- ⚠️ Este script eliminará datos irreversiblemente

-- Verificar que existen las columnas antes de eliminarlas
DO $$
BEGIN
    -- Eliminar columna duplicada 19: CEDULA IDENTIDAD
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'clientes' AND column_name = 'CEDULA IDENTIDAD') THEN
        ALTER TABLE clientes DROP COLUMN "CEDULA IDENTIDAD";
        RAISE NOTICE 'Columna CEDULA IDENTIDAD eliminada';
    END IF;

    -- Eliminar columna duplicada 20: nombre
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'clientes' AND column_name = 'nombre') THEN
        ALTER TABLE clientes DROP COLUMN nombre;
        RAISE NOTICE 'Columna nombre eliminada';
    END IF;

    -- Eliminar columna duplicada 21: apellido
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'clientes' AND column_name = 'apellido') THEN
        ALTER TABLE clientes DROP COLUMN apellido;
        RAISE NOTICE 'Columna apellido eliminada';
    END IF;

    -- Eliminar columna duplicada 22: movil
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'clientes' AND column_name = 'movil') THEN
        ALTER TABLE clientes DROP COLUMN movil;
        RAISE NOTICE 'Columna movil eliminada';
    END IF;

    -- Eliminar columna duplicada 23: CORREO ELECTRONICO
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'clientes' AND column_name = 'CORREO ELECTRONICO') THEN
        ALTER TABLE clientes DROP COLUMN "CORREO ELECTRONICO";
        RAISE NOTICE 'Columna CORREO ELECTRONICO eliminada';
    END IF;

    -- Eliminar columna duplicada 24: FECHA DE NACIMIENTO
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'clientes' AND column_name = 'FECHA DE NACIMIENTO') THEN
        ALTER TABLE clientes DROP COLUMN "FECHA DE NACIMIENTO";
        RAISE NOTICE 'Columna FECHA DE NACIMIENTO eliminada';
    END IF;

    -- Eliminar columna duplicada 25: MODELO VEHICULO
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'clientes' AND column_name = 'MODELO VEHICULO') THEN
        ALTER TABLE clientes DROP COLUMN "MODELO VEHICULO";
        RAISE NOTICE 'Columna MODELO VEHICULO eliminada';
    END IF;

    -- Eliminar columna duplicada 26: ESTADO DEL CASO
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'clientes' AND column_name = 'ESTADO DEL CASO') THEN
        ALTER TABLE clientes DROP COLUMN "ESTADO DEL CASO";
        RAISE NOTICE 'Columna ESTADO DEL CASO eliminada';
    END IF;

    RAISE NOTICE 'Proceso de limpieza completado';
END $$;

-- Verificar columnas restantes
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'clientes'
ORDER BY ordinal_position;

