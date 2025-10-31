-- ============================================
-- ✅ VERIFICACIÓN DE DATOS DE PAGOS CARGADOS
-- ============================================
-- Ejecutar en DBeaver para verificar si hay datos de pagos en la base de datos
-- Fecha: 2025-10-31

-- ============================================
-- 1. CONTAR TOTAL DE PAGOS
-- ============================================
SELECT 
    COUNT(*) AS total_pagos,
    COUNT(DISTINCT cedula_cliente) AS clientes_con_pagos,
    COUNT(DISTINCT prestamo_id) AS prestamos_con_pagos
FROM public.pagos;

-- ============================================
-- 2. VERIFICAR ESTRUCTURA DE LA TABLA PAGOS
-- ============================================
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'pagos'
ORDER BY ordinal_position;

-- ============================================
-- 3. PRIMEROS 10 PAGOS (MUESTRA)
-- ============================================
SELECT 
    id,
    cedula_cliente,
    prestamo_id,
    fecha_pago,
    monto_pagado,
    numero_documento,
    estado,
    fecha_registro,
    usuario_registro
FROM public.pagos
ORDER BY fecha_registro DESC
LIMIT 10;

-- ============================================
-- 4. RESUMEN DE PAGOS POR ESTADO
-- ============================================
SELECT 
    estado,
    COUNT(*) AS cantidad,
    SUM(monto_pagado) AS monto_total,
    AVG(monto_pagado) AS monto_promedio
FROM public.pagos
GROUP BY estado
ORDER BY cantidad DESC;

-- ============================================
-- 5. RESUMEN DE PAGOS POR FECHA (ÚLTIMOS 30 DÍAS)
-- ============================================
SELECT 
    DATE(fecha_pago) AS fecha,
    COUNT(*) AS cantidad_pagos,
    SUM(monto_pagado) AS monto_total,
    COUNT(DISTINCT cedula_cliente) AS clientes_unicos
FROM public.pagos
WHERE fecha_pago >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(fecha_pago)
ORDER BY fecha DESC;

-- ============================================
-- 6. VERIFICAR PAGOS CON PRESTAMO ASOCIADO
-- ============================================
SELECT 
    COUNT(*) AS total_pagos,
    COUNT(prestamo_id) AS pagos_con_prestamo,
    COUNT(*) - COUNT(prestamo_id) AS pagos_sin_prestamo,
    ROUND(COUNT(prestamo_id) * 100.0 / COUNT(*), 2) AS porcentaje_con_prestamo
FROM public.pagos;

-- ============================================
-- 7. VERIFICAR SI EXISTE TABLA STAGING DE PAGOS
-- ============================================
SELECT 
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema = 'public' 
  AND table_name LIKE '%pago%'
ORDER BY table_name;

-- ============================================
-- 8. COMPARAR CON CLIENTES Y PRESTAMOS
-- ============================================
SELECT 
    'clientes' AS tabla,
    COUNT(*) AS total_registros
FROM public.clientes
UNION ALL
SELECT 
    'prestamos' AS tabla,
    COUNT(*) AS total_registros
FROM public.prestamos
UNION ALL
SELECT 
    'pagos' AS tabla,
    COUNT(*) AS total_registros
FROM public.pagos;

-- ============================================
-- 9. VERIFICAR PAGOS POR CLIENTE (TOP 10)
-- ============================================
SELECT 
    p.cedula_cliente,
    c.nombres,
    COUNT(p.id) AS cantidad_pagos,
    SUM(p.monto_pagado) AS monto_total_pagado,
    MIN(p.fecha_pago) AS primer_pago,
    MAX(p.fecha_pago) AS ultimo_pago
FROM public.pagos p
LEFT JOIN public.clientes c ON p.cedula_cliente = c.cedula
GROUP BY p.cedula_cliente, c.nombres
ORDER BY cantidad_pagos DESC
LIMIT 10;

-- ============================================
-- 10. VERIFICAR VALIDACIONES Y CONSTRAINTS
-- ============================================
SELECT 
    conname AS constraint_name,
    contype AS constraint_type,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid = 'public.pagos'::regclass
ORDER BY contype, conname;

