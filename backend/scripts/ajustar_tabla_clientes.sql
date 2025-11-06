-- ============================================
-- SCRIPT PARA AJUSTAR TABLA clientes
-- Sistema de Créditos y Cobranza
-- Fecha: 2025-10-26
-- ============================================

-- ⚠️ IMPORTANTE: Hacer BACKUP de la base de datos ANTES de ejecutar
-- ⚠️ Este script modifica estructura de tabla

-- ============================================
-- PASO 1: ELIMINAR COLUMNAS DUPLICADAS (filas 20-26)
-- ============================================

DO $$
BEGIN
    -- Eliminar columna duplicada 20: CEDULA IDENTIDAD
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'clientes' AND column_name = 'CEDULA IDENTIDAD') THEN
        ALTER TABLE clientes DROP COLUMN "CEDULA IDENTIDAD";
        RAISE NOTICE 'Columna CEDULA IDENTIDAD eliminada';
    END IF;

    -- Eliminar columna duplicada 21: nombre
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'clientes' AND column_name = 'nombre') THEN
        ALTER TABLE clientes DROP COLUMN nombre;
        RAISE NOTICE 'Columna nombre eliminada';
    END IF;

    -- Eliminar columna duplicada 22: apellido
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'clientes' AND column_name = 'apellido') THEN
        ALTER TABLE clientes DROP COLUMN apellido;
        RAISE NOTICE 'Columna apellido eliminada';
    END IF;

    -- Eliminar columna duplicada 23: movil
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'clientes' AND column_name = 'movil') THEN
        ALTER TABLE clientes DROP COLUMN movil;
        RAISE NOTICE 'Columna movil eliminada';
    END IF;

    -- Eliminar columna duplicada 24: CORREO ELECTRONICO
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'clientes' AND column_name = 'CORREO ELECTRONICO') THEN
        ALTER TABLE clientes DROP COLUMN "CORREO ELECTRONICO";
        RAISE NOTICE 'Columna CORREO ELECTRONICO eliminada';
    END IF;

    -- Eliminar columna duplicada 25: FECHA DE NACIMIENTO
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'clientes' AND column_name = 'FECHA DE NACIMIENTO') THEN
        ALTER TABLE clientes DROP COLUMN "FECHA DE NACIMIENTO";
        RAISE NOTICE 'Columna FECHA DE NACIMIENTO eliminada';
    END IF;

    -- Eliminar columna duplicada 26: MODELO VEHICULO
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'clientes' AND column_name = 'MODELO VEHICULO') THEN
        ALTER TABLE clientes DROP COLUMN "MODELO VEHICULO";
        RAISE NOTICE 'Columna MODELO VEHICULO eliminada';
    END IF;

    -- Eliminar columna duplicada 27: ESTADO DEL CASO
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'clientes' AND column_name = 'ESTADO DEL CASO') THEN
        ALTER TABLE clientes DROP COLUMN "ESTADO DEL CASO";
        RAISE NOTICE 'Columna ESTADO DEL CASO eliminada';
    END IF;

    RAISE NOTICE 'Columnas duplicadas eliminadas';
END $$;

-- ============================================
-- PASO 2: UNIFICAR nombres + apellidos EN nombres
-- ============================================

-- Antes de eliminar apellidos, migrar datos combinados a nombres
UPDATE clientes
SET nombres = TRIM(nombres || ' ' || apellidos)
WHERE apellidos IS NOT NULL 
  AND apellidos != '';

-- Ahora eliminar columna apellidos
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'clientes' AND column_name = 'apellidos') THEN
        ALTER TABLE clientes DROP COLUMN apellidos;
        RAISE NOTICE 'Columna apellidos eliminada (datos migrados a nombres)';
    END IF;
END $$;

-- ============================================
-- PASO 3: AJUSTAR fecha_actualizacion (NOT NULL con default)
-- ============================================

-- Si fecha_actualizacion es NULL, asignar fecha_registro o now()
UPDATE clientes
SET fecha_actualizacion = COALESCE(fecha_actualizacion, fecha_registro, NOW())
WHERE fecha_actualizacion IS NULL;

-- Cambiar a NOT NULL con default now()
ALTER TABLE clientes
ALTER COLUMN fecha_actualizacion SET NOT NULL;

ALTER TABLE clientes
ALTER COLUMN fecha_actualizacion SET DEFAULT NOW();

-- ============================================
-- PASO 4: AJUSTAR notas (NOT NULL con default 'NA')
-- ============================================

-- Si notas es NULL o vacío, asignar 'NA'
UPDATE clientes
SET notas = CASE 
    WHEN notas IS NULL OR TRIM(notas) = '' THEN 'NA'
    ELSE notas
END;

-- Cambiar a NOT NULL con default 'NA'
ALTER TABLE clientes
ALTER COLUMN notas SET NOT NULL;

ALTER TABLE clientes
ALTER COLUMN notas SET DEFAULT 'NA';

-- ============================================
-- PASO 5: VERIFICAR ESTRUCTURA FINAL
-- ============================================

-- Mostrar estructura final
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default,
    character_maximum_length
FROM information_schema.columns
WHERE table_name = 'clientes'
ORDER BY ordinal_position;

-- ============================================
-- VERIFICACIONES
-- ============================================

-- Verificar que todos los campos están NOT NULL
SELECT 
    column_name,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'clientes'
  AND is_nullable = 'YES';

-- Verificar registros sin fecha_registro
SELECT COUNT(*) as total_sin_fecha
FROM clientes
WHERE fecha_registro IS NULL;

-- Verificar registros sin nombres
SELECT COUNT(*) as total_sin_nombres
FROM clientes
WHERE nombres IS NULL OR TRIM(nombres) = '';

-- ============================================
-- FIN DEL SCRIPT
-- ============================================
RAISE NOTICE 'Script completado exitosamente';

