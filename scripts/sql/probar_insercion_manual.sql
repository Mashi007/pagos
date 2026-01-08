-- =====================================================
-- PROBAR INSERCIÓN MANUAL EN clientes_temp
-- Para verificar que la tabla funciona correctamente
-- =====================================================

-- Insertar un registro de prueba
INSERT INTO clientes_temp (
    cedula, nombres, telefono, email, direccion,
    fecha_nacimiento, ocupacion, estado, activo,
    fecha_registro, fecha_actualizacion, usuario_registro, notas
) VALUES (
    'V12345678', 
    'JUAN PEREZ GARCIA', 
    '+53555123456', 
    'test@email.com', 
    'Venezuela',
    '1990-01-01', 
    'Ingeniero', 
    'ACTIVO', 
    true,
    '2025-01-27 10:00:00', 
    '2025-01-27 10:00:00', 
    'SISTEMA', 
    'nn'
);

-- Verificar que se insertó
SELECT 
    'Registros después de insertar manualmente' as verificacion,
    COUNT(*) as cantidad
FROM clientes_temp;

-- Ver el registro insertado
SELECT * FROM clientes_temp;

