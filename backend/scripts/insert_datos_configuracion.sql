-- Script SQL para insertar datos de configuración necesarios
-- para que el formulario funcione correctamente

-- Insertar concesionarios
INSERT INTO concesionarios (nombre, direccion, telefono, email, responsable, activo, created_at, updated_at)
VALUES 
('AutoCenter Caracas', 'Av. Francisco de Miranda, Caracas', '+58 212-555-0101', 'caracas@autocenter.com', 'María González', true, NOW(), NOW()),
('Motors Valencia', 'Zona Industrial Norte, Valencia', '+58 241-555-0202', 'valencia@motors.com', 'Carlos Rodríguez', true, NOW(), NOW()),
('Vehiculos Maracaibo', 'Av. 5 de Julio, Maracaibo', '+58 261-555-0303', 'maracaibo@vehiculos.com', 'Ana Pérez', true, NOW(), NOW())
ON CONFLICT (nombre) DO NOTHING;

-- Insertar analistaes
INSERT INTO analistaes (nombre, apellido, email, telefono, especialidad, comision_porcentaje, activo, notas, created_at, updated_at)
VALUES 
('Roberto', 'Martínez', 'roberto.martinez@rapicredit.com', '+58 414-555-0404', 'Vehículos Nuevos', 2.5, true, 'Especialista en vehículos de gama alta', NOW(), NOW()),
('Sandra', 'López', 'sandra.lopez@rapicredit.com', '+58 424-555-0505', 'Vehículos Usados', 3.0, true, 'Experta en financiamiento de vehículos usados', NOW(), NOW()),
('Miguel', 'Hernández', 'miguel.hernandez@rapicredit.com', '+58 414-555-0606', 'Motocicletas', 4.0, true, 'Especialista en financiamiento de motocicletas', NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

-- Verificar inserción
SELECT 'Concesionarios insertados:' as resultado, COUNT(*) as total FROM concesionarios WHERE activo = true;
SELECT 'Asesores insertados:' as resultado, COUNT(*) as total FROM analistaes WHERE activo = true;
