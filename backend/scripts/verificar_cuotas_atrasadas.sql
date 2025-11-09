-- Script SQL para verificar cuotas atrasadas y diagnosticar notificaciones prejudiciales

-- 1. Verificar total de cuotas atrasadas
SELECT 
    'Total cuotas atrasadas' as descripcion,
    COUNT(*) as total
FROM cuotas c
INNER JOIN prestamos p ON p.id = c.prestamo_id
WHERE c.estado = 'ATRASADO'
  AND c.fecha_vencimiento < CURRENT_DATE
  AND p.estado = 'APROBADO';

-- 2. Verificar distribución de cuotas atrasadas por cliente
SELECT 
    p.cliente_id,
    cl.nombres,
    cl.cedula,
    COUNT(*) as cuotas_atrasadas
FROM prestamos p
INNER JOIN cuotas c ON c.prestamo_id = p.id
INNER JOIN clientes cl ON cl.id = p.cliente_id
WHERE p.estado = 'APROBADO'
  AND c.estado = 'ATRASADO'
  AND c.fecha_vencimiento < CURRENT_DATE
  AND cl.estado != 'INACTIVO'
GROUP BY p.cliente_id, cl.nombres, cl.cedula
ORDER BY cuotas_atrasadas DESC
LIMIT 20;

-- 3. Verificar clientes con 2 cuotas atrasadas (casi cumplen criterio)
SELECT 
    p.cliente_id,
    cl.nombres,
    cl.cedula,
    COUNT(*) as cuotas_atrasadas
FROM prestamos p
INNER JOIN cuotas c ON c.prestamo_id = p.id
INNER JOIN clientes cl ON cl.id = p.cliente_id
WHERE p.estado = 'APROBADO'
  AND c.estado = 'ATRASADO'
  AND c.fecha_vencimiento < CURRENT_DATE
  AND cl.estado != 'INACTIVO'
GROUP BY p.cliente_id, cl.nombres, cl.cedula
HAVING COUNT(*) = 2
ORDER BY cuotas_atrasadas DESC
LIMIT 10;

-- 4. Verificar estados de cuotas
SELECT 
    estado,
    COUNT(*) as total
FROM cuotas
GROUP BY estado
ORDER BY total DESC;

-- 5. Verificar estados de préstamos
SELECT 
    estado,
    COUNT(*) as total
FROM prestamos
GROUP BY estado
ORDER BY total DESC;

-- 6. Verificar cuotas con fecha de vencimiento pasada pero estado diferente a ATRASADO
SELECT 
    c.estado,
    COUNT(*) as total
FROM cuotas c
INNER JOIN prestamos p ON p.id = c.prestamo_id
WHERE c.fecha_vencimiento < CURRENT_DATE
  AND p.estado = 'APROBADO'
GROUP BY c.estado
ORDER BY total DESC;

-- 7. Verificar si hay cuotas que deberían estar ATRASADO pero no lo están
SELECT 
    c.id,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.estado,
    p.id as prestamo_id,
    cl.nombres as cliente
FROM cuotas c
INNER JOIN prestamos p ON p.id = c.prestamo_id
INNER JOIN clientes cl ON cl.id = p.cliente_id
WHERE c.fecha_vencimiento < CURRENT_DATE
  AND c.estado != 'ATRASADO'
  AND c.estado != 'PAGADO'
  AND p.estado = 'APROBADO'
  AND cl.estado != 'INACTIVO'
ORDER BY c.fecha_vencimiento ASC
LIMIT 20;

