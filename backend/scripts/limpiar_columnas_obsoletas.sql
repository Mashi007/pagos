-- Script para eliminar columnas obsoletas de las tablas
-- Ejecutar con cuidado: BACKUP de la base de datos antes

-- =====================================================
-- TABLA: analistas
-- Columnas actuales según modelo: id, nombre, activo
-- Eliminar columnas que no existen en el modelo
-- =====================================================

-- Ejemplo: Si existe columna 'email' (que no está en el modelo)
-- ALTER TABLE analistas DROP COLUMN IF EXISTS email;
-- ALTER TABLE analistas DROP COLUMN IF EXISTS apellido;
-- ALTER TABLE analistas DROP COLUMN IF EXISTS telefono;
-- ALTER TABLE analistas DROP COLUMN IF EXISTS especialidad;
-- ALTER TABLE analistas DROP COLUMN IF EXISTS comision_porcentaje;
-- ALTER TABLE analistas DROP COLUMN IF EXISTS notas;
-- ALTER TABLE analistas DROP COLUMN IF EXISTS fecha_creacion;
-- ALTER TABLE analistas DROP COLUMN IF EXISTS fecha_modificacion;
-- ALTER TABLE analistas DROP COLUMN IF EXISTS updated_at;

-- =====================================================
-- TABLA: concesionarios
-- Columnas actuales según modelo: id, nombre, activo, updated_at
-- Eliminar columnas que no existen en el modelo
-- =====================================================

-- Ejemplo: Si existe columna 'direccion' (que no está en el modelo)
-- ALTER TABLE concesionarios DROP COLUMN IF EXISTS direccion;
-- ALTER TABLE concesionarios DROP COLUMN IF EXISTS telefono;
-- ALTER TABLE concesionarios DROP COLUMN IF EXISTS contacto;
-- ALTER TABLE concesionarios DROP COLUMN IF EXISTS fecha_creacion;
-- ALTER TABLE concesionarios DROP COLUMN IF EXISTS fecha_modificacion;

-- =====================================================
-- TABLA: modelos_vehiculos
-- Columnas actuales según modelo: id, modelo, activo, updated_at
-- Eliminar columnas que no existen en el modelo
-- =====================================================

-- Ejemplo: Si existe columna 'marca' (que no está en el modelo)
-- ALTER TABLE modelos_vehiculos DROP COLUMN IF EXISTS marca;
-- ALTER TABLE modelos_vehiculos DROP COLUMN IF EXISTS categoria;
-- ALTER TABLE modelos_vehiculos DROP COLUMN IF EXISTS precio;
-- ALTER TABLE modelos_vehiculos DROP COLUMN IF EXISTS fecha_creacion;
-- ALTER TABLE modelos_vehiculos DROP COLUMN IF EXISTS fecha_modificacion;

-- =====================================================
-- INSTRUCCIONES DE USO:
-- =====================================================
-- 1. Verificar qué columnas existen en tu BD con:
--    SELECT column_name, data_type 
--    FROM information_schema.columns 
--    WHERE table_name = 'analistas';
--
-- 2. Descomentar las líneas de DROP COLUMN que necesites
--
-- 3. Ejecutar este script en tu base de datos
--
-- 4. Verificar que las tablas queden solo con las columnas del modelo
-- =====================================================

