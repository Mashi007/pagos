-- ==========================================
-- CONSULTA SIMPLE: VER TODOS LOS CLIENTES
-- ==========================================
SELECT 
    id,
    cedula,
    nombres,
    telefono,
    email,
    estado,
    activo,
    modelo_vehiculo,
    concesionario,
    analista,
    fecha_registro
FROM clientes 
ORDER BY fecha_registro DESC;

-- ==========================================
-- CONTAR CLIENTES POR ESTADO
-- ==========================================
SELECT 
    estado,
    COUNT(*) as total,
    COUNT(CASE WHEN activo = true THEN 1 END) as activos
FROM clientes 
GROUP BY estado
ORDER BY total DESC;

-- ==========================================
-- VER ÚLTIMOS 10 CLIENTES REGISTRADOS
-- ==========================================
SELECT 
    id,
    cedula,
    nombres,
    telefono,
    email,
    estado,
    fecha_registro
FROM clientes 
ORDER BY fecha_registro DESC 
LIMIT 10;

-- ==========================================
-- VER CLIENTES ACTIVOS
-- ==========================================
SELECT 
    id,
    cedula,
    nombres,
    telefono,
    email,
    estado,
    modelo_vehiculo,
    concesionario,
    analista,
    fecha_registro
FROM clientes 
WHERE activo = true
ORDER BY nombres;

-- ==========================================
-- ESTADÍSTICAS POR ANALISTA
-- ==========================================
SELECT 
    analista,
    COUNT(*) as total_clientes,
    COUNT(CASE WHEN estado = 'ACTIVO' THEN 1 END) as activos,
    COUNT(CASE WHEN estado = 'INACTIVO' THEN 1 END) as inactivos,
    COUNT(CASE WHEN estado = 'FINALIZADO' THEN 1 END) as finalizados
FROM clientes 
GROUP BY analista
ORDER BY total_clientes DESC;

-- ==========================================
-- ESTADÍSTICAS POR CONCESIONARIO
-- ==========================================
SELECT 
    concesionario,
    COUNT(*) as total_clientes,
    COUNT(CASE WHEN activo = true THEN 1 END) as activos
FROM clientes 
GROUP BY concesionario
ORDER BY total_clientes DESC;

