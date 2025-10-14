-- ============================================
-- CREAR USUARIOS DE PRUEBA PARA RAPICREDIT
-- ============================================

-- Insertar usuarios de prueba en la base de datos
-- Password para todos: "admin123" (hash bcrypt)

INSERT INTO users (
    email, 
    password_hash, 
    nombre, 
    apellido, 
    rol, 
    activo, 
    creado_en, 
    actualizado_en
) VALUES 
(
    'admin@rapicredit.com',
    '$2b$12$LQv3c1yqBwEHXz2gG8K2vO8vG8K2vO8vG8K2vO8vG8K2vO8vG8K2vO',
    'Admin',
    'Sistema',
    'ADMIN',
    true,
    NOW(),
    NOW()
),
(
    'gerente@rapicredit.com',
    '$2b$12$LQv3c1yqBwEHXz2gG8K2vO8vG8K2vO8vG8K2vO8vG8K2vO8vG8K2vO',
    'Juan',
    'Pérez',
    'GERENTE',
    true,
    NOW(),
    NOW()
),
(
    'asesor@rapicredit.com',
    '$2b$12$LQv3c1yqBwEHXz2gG8K2vO8vG8K2vO8vG8K2vO8vG8K2vO8vG8K2vO',
    'María',
    'García',
    'ASESOR_COMERCIAL',
    true,
    NOW(),
    NOW()
),
(
    'contador@rapicredit.com',
    '$2b$12$LQv3c1yqBwEHXz2gG8K2vO8vG8K2vO8vG8K2vO8vG8K2vO8vG8K2vO',
    'Carlos',
    'López',
    'CONTADOR',
    true,
    NOW(),
    NOW()
),
(
    'cobranzas@rapicredit.com',
    '$2b$12$LQv3c1yqBwEHXz2gG8K2vO8vG8K2vO8vG8K2vO8vG8K2vO8vG8K2vO',
    'Ana',
    'Martínez',
    'COBRANZAS',
    true,
    NOW(),
    NOW()
);

-- Verificar usuarios creados
SELECT 
    id,
    email,
    nombre,
    apellido,
    rol,
    activo,
    creado_en
FROM users 
WHERE email IN (
    'admin@rapicredit.com',
    'gerente@rapicredit.com',
    'asesor@rapicredit.com',
    'contador@rapicredit.com',
    'cobranzas@rapicredit.com'
)
ORDER BY rol;

-- Crear concesionarios de prueba
INSERT INTO concesionarios (
    nombre,
    direccion,
    telefono,
    email,
    activo,
    creado_en,
    actualizado_en
) VALUES 
(
    'Concesionario Central',
    'Av. Principal 123, Caracas',
    '+58412123456',
    'central@concesionario.com',
    true,
    NOW(),
    NOW()
),
(
    'Auto Plaza Norte',
    'Calle Norte 456, Valencia',
    '+58412987654',
    'norte@autoplaza.com',
    true,
    NOW(),
    NOW()
);

-- Crear asesores de prueba
INSERT INTO asesores (
    user_id,
    concesionario_id,
    codigo_asesor,
    activo,
    creado_en,
    actualizado_en
) VALUES 
(
    (SELECT id FROM users WHERE email = 'asesor@rapicredit.com'),
    (SELECT id FROM concesionarios WHERE nombre = 'Concesionario Central'),
    'AS001',
    true,
    NOW(),
    NOW()
);

-- Crear clientes de prueba
INSERT INTO clientes (
    nombres,
    apellidos,
    cedula,
    telefono,
    email,
    direccion,
    anio_vehiculo,
    modelo_vehiculo,
    total_financiamiento,
    numero_amortizaciones,
    modalidad_pago,
    concesionario_id,
    asesor_id,
    estado,
    creado_en,
    actualizado_en
) VALUES 
(
    'Pedro',
    'González',
    '12345678',
    '+58412123456',
    'pedro@email.com',
    'Calle 1, Caracas',
    2020,
    'Toyota Corolla',
    15000.00,
    36,
    'MENSUAL',
    (SELECT id FROM concesionarios WHERE nombre = 'Concesionario Central'),
    (SELECT id FROM asesores WHERE codigo_asesor = 'AS001'),
    'ACTIVO',
    NOW(),
    NOW()
),
(
    'Laura',
    'Rodríguez',
    '87654321',
    '+58412987654',
    'laura@email.com',
    'Calle 2, Valencia',
    2021,
    'Honda Civic',
    18000.00,
    48,
    'MENSUAL',
    (SELECT id FROM concesionarios WHERE nombre = 'Auto Plaza Norte'),
    (SELECT id FROM asesores WHERE codigo_asesor = 'AS001'),
    'ACTIVO',
    NOW(),
    NOW()
);

-- Verificar datos creados
SELECT 
    'USUARIOS' as tabla,
    COUNT(*) as total
FROM users 
WHERE email LIKE '%@rapicredit.com'

UNION ALL

SELECT 
    'CONCESIONARIOS' as tabla,
    COUNT(*) as total
FROM concesionarios

UNION ALL

SELECT 
    'ASESORES' as tabla,
    COUNT(*) as total
FROM asesores

UNION ALL

SELECT 
    'CLIENTES' as tabla,
    COUNT(*) as total
FROM clientes;

-- Mostrar resumen
SELECT 
    u.email,
    u.nombre,
    u.apellido,
    u.rol,
    CASE 
        WHEN a.id IS NOT NULL THEN 'ASESOR'
        ELSE 'USUARIO'
    END as tipo,
    c.nombre as concesionario
FROM users u
LEFT JOIN asesores a ON u.id = a.user_id
LEFT JOIN concesionarios c ON a.concesionario_id = c.id
WHERE u.email LIKE '%@rapicredit.com'
ORDER BY u.rol, u.nombre;
