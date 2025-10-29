-- ============================================
-- ACTUALIZAR CONDICIONES DE CAMPOS EN TABLA CLIENTES
-- ============================================
-- Ejecutar en DBeaver para actualizar las condiciones de los campos

-- 1. ACTUALIZAR CAMPOS OBLIGATORIOS (NOT NULL)
-- ============================================

-- Hacer campos obligatorios
ALTER TABLE clientes ALTER COLUMN cedula SET NOT NULL;
ALTER TABLE clientes ALTER COLUMN nombres SET NOT NULL;
ALTER TABLE clientes ALTER COLUMN apellidos SET NOT NULL;
ALTER TABLE clientes ALTER COLUMN telefono SET NOT NULL;
ALTER TABLE clientes ALTER COLUMN email SET NOT NULL;
ALTER TABLE clientes ALTER COLUMN direccion SET NOT NULL;
ALTER TABLE clientes ALTER COLUMN fecha_nacimiento SET NOT NULL;
ALTER TABLE clientes ALTER COLUMN ocupacion SET NOT NULL;
ALTER TABLE clientes ALTER COLUMN modelo_vehiculo SET NOT NULL;
ALTER TABLE clientes ALTER COLUMN concesionario SET NOT NULL;
ALTER TABLE clientes ALTER COLUMN analista SET NOT NULL;
ALTER TABLE clientes ALTER COLUMN estado SET NOT NULL;
ALTER TABLE clientes ALTER COLUMN usuario_registro SET NOT NULL;

-- 2. ACTUALIZAR VALORES POR DEFECTO
-- ============================================

-- Estado por defecto
ALTER TABLE clientes ALTER COLUMN estado SET DEFAULT 'ACTIVO';

-- Activo por defecto
ALTER TABLE clientes ALTER COLUMN activo SET DEFAULT true;

-- Notas por defecto
ALTER TABLE clientes ALTER COLUMN notas SET DEFAULT 'NA';

-- 3. AGREGAR CONSTRAINTS DE VALIDACIÓN
-- ============================================

-- Constraint para estado válido
ALTER TABLE clientes ADD CONSTRAINT chk_estado_valido 
CHECK (estado IN ('ACTIVO', 'INACTIVO', 'FINALIZADO'));

-- Constraint para cédula (8-20 caracteres)
ALTER TABLE clientes ADD CONSTRAINT chk_cedula_longitud 
CHECK (LENGTH(cedula) >= 8 AND LENGTH(cedula) <= 20);

-- Constraint para teléfono (8-15 caracteres)
ALTER TABLE clientes ADD CONSTRAINT chk_telefono_longitud 
CHECK (LENGTH(telefono) >= 8 AND LENGTH(telefono) <= 15);

-- Constraint para email válido
ALTER TABLE clientes ADD CONSTRAINT chk_email_valido 
CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

-- Constraint para nombres (máximo 2 palabras)
ALTER TABLE clientes ADD CONSTRAINT chk_nombres_palabras 
CHECK (array_length(string_to_array(trim(nombres), ' '), 1) <= 2);

-- Constraint para apellidos (máximo 2 palabras)
ALTER TABLE clientes ADD CONSTRAINT chk_apellidos_palabras 
CHECK (array_length(string_to_array(trim(apellidos), ' '), 1) <= 2);

-- Constraint para fecha de nacimiento (no futura)
ALTER TABLE clientes ADD CONSTRAINT chk_fecha_nacimiento_valida 
CHECK (fecha_nacimiento <= CURRENT_DATE);

-- 4. ACTUALIZAR DATOS EXISTENTES
-- ============================================

-- Actualizar registros con campos NULL a valores por defecto
UPDATE clientes SET estado = 'ACTIVO' WHERE estado IS NULL;
UPDATE clientes SET activo = true WHERE activo IS NULL;
UPDATE clientes SET notas = 'NA' WHERE notas IS NULL OR notas = '';
UPDATE clientes SET usuario_registro = 'SISTEMA' WHERE usuario_registro IS NULL;

-- 5. VERIFICAR ESTRUCTURA FINAL
-- ============================================

-- Mostrar estructura de la tabla
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'clientes' 
ORDER BY ordinal_position;

-- Mostrar constraints
SELECT 
    constraint_name,
    constraint_type,
    check_clause
FROM information_schema.table_constraints tc
LEFT JOIN information_schema.check_constraints cc 
    ON tc.constraint_name = cc.constraint_name
WHERE tc.table_name = 'clientes';

-- 6. VERIFICAR DATOS
-- ============================================

-- Contar registros por estado
SELECT estado, COUNT(*) as cantidad 
FROM clientes 
GROUP BY estado;

-- Verificar campos obligatorios
SELECT 
    COUNT(*) as total_registros,
    COUNT(cedula) as cedulas_completas,
    COUNT(nombres) as nombres_completos,
    COUNT(apellidos) as apellidos_completos,
    COUNT(telefono) as telefonos_completos,
    COUNT(email) as emails_completos,
    COUNT(direccion) as direcciones_completas,
    COUNT(fecha_nacimiento) as fechas_completas,
    COUNT(ocupacion) as ocupaciones_completas,
    COUNT(modelo_vehiculo) as modelos_completos,
    COUNT(concesionario) as concesionarios_completos,
    COUNT(analista) as analistas_completos
FROM clientes;

PRINT '✅ Actualización de campos completada exitosamente';
