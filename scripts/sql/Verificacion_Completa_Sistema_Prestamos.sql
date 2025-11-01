-- ============================================================================
-- VERIFICACIÓN COMPLETA DEL SISTEMA DE PRÉSTAMOS
-- Script para verificar paso a paso todos los componentes del sistema
-- Usar en DBeaver para validar que todo funciona correctamente
-- ============================================================================

-- ============================================================================
-- PASO 1: VERIFICAR ESTRUCTURA DE TABLAS
-- ============================================================================
SELECT 
    'PASO 1: Verificación de Estructura de Tablas' AS seccion;

-- Verificar que todas las tablas necesarias existen
SELECT 
    table_name,
    'EXISTE' AS estado
FROM information_schema.tables 
WHERE table_schema = 'public' 
    AND table_name IN (
        'clientes',
        'prestamos', 
        'cuotas',
        'pagos',
        'analistas',
        'concesionarios',
        'modelos_vehiculos',
        'users'
    )
ORDER BY table_name;

-- ============================================================================
-- PASO 2: VERIFICAR CLIENTES
-- ============================================================================
SELECT 
    'PASO 2: Verificación de Clientes' AS seccion;

-- Total de clientes
SELECT 
    'Total de clientes' AS metrica,
    COUNT(*) AS valor
FROM clientes;

-- Clientes activos
SELECT 
    'Clientes activos' AS metrica,
    COUNT(*) AS valor
FROM clientes 
WHERE activo = true;

-- Clientes con préstamos
SELECT 
    'Clientes con préstamos' AS metrica,
    COUNT(DISTINCT prestamos.cedula) AS valor
FROM prestamos
JOIN clientes ON prestamos.cedula = clientes.cedula;

-- Ejemplo de clientes
SELECT 
    cedula,
    nombres AS nombre_completo,
    activo,
    fecha_registro,
    fecha_actualizacion
FROM clientes 
ORDER BY fecha_registro DESC
LIMIT 10;

-- ============================================================================
-- PASO 3: VERIFICAR PRÉSTAMOS CREADOS
-- ============================================================================
SELECT 
    'PASO 3: Verificación de Préstamos Creados' AS seccion;

-- Total de préstamos por estado
SELECT 
    estado,
    COUNT(*) AS cantidad,
    COALESCE(SUM(total_financiamiento), 0) AS total_financiamiento
FROM prestamos
GROUP BY estado
ORDER BY estado;

-- Total general de préstamos
SELECT 
    'Total préstamos' AS metrica,
    COUNT(*) AS valor
FROM prestamos;

-- Préstamos con todos los campos requeridos
SELECT 
    'Préstamos con campos completos' AS metrica,
    COUNT(*) AS valor
FROM prestamos
WHERE cedula IS NOT NULL 
    AND total_financiamiento IS NOT NULL
    AND numero_cuotas IS NOT NULL
    AND estado IS NOT NULL
    AND concesionario IS NOT NULL 
    AND concesionario != ''
    AND analista IS NOT NULL 
    AND analista != ''
    AND modelo_vehiculo IS NOT NULL 
    AND modelo_vehiculo != '';

-- Préstamos recientes (últimos 10)
SELECT 
    id,
    cedula,
    producto,
    total_financiamiento,
    numero_cuotas,
    estado,
    concesionario,
    analista,
    modelo_vehiculo,
    fecha_registro
FROM prestamos
ORDER BY fecha_registro DESC
LIMIT 10;

-- Préstamos por analista
SELECT 
    analista,
    COUNT(*) AS cantidad_prestamos,
    COALESCE(SUM(total_financiamiento), 0) AS total_financiamiento
FROM prestamos
WHERE analista IS NOT NULL AND analista != ''
GROUP BY analista
ORDER BY cantidad_prestamos DESC;

-- Préstamos por concesionario
SELECT 
    concesionario,
    COUNT(*) AS cantidad_prestamos,
    COALESCE(SUM(total_financiamiento), 0) AS total_financiamiento
FROM prestamos
WHERE concesionario IS NOT NULL AND concesionario != ''
GROUP BY concesionario
ORDER BY cantidad_prestamos DESC;

-- ============================================================================
-- PASO 4: VERIFICAR APROBACIONES
-- ============================================================================
SELECT 
    'PASO 4: Verificación de Aprobaciones' AS seccion;

-- Préstamos aprobados
SELECT 
    'Préstamos aprobados' AS metrica,
    COUNT(*) AS cantidad,
    COALESCE(SUM(total_financiamiento), 0) AS total_financiamiento
FROM prestamos
WHERE estado = 'APROBADO';

-- Préstamos aprobados con detalles
SELECT 
    p.id,
    p.cedula,
    c.nombres AS nombre_cliente,
    p.total_financiamiento,
    p.numero_cuotas,
    p.tasa_interes,
    p.usuario_autoriza,
    p.fecha_registro,
    p.fecha_aprobacion
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula
WHERE p.estado = 'APROBADO'
ORDER BY p.fecha_aprobacion DESC NULLS LAST
LIMIT 10;

-- Préstamos aprobados sin cuotas generadas
SELECT 
    'Préstamos aprobados sin cuotas' AS metrica,
    COUNT(DISTINCT p.id) AS cantidad
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.estado = 'APROBADO' 
    AND c.id IS NULL;

-- Préstamos por estado detallado
SELECT 
    estado,
    COUNT(*) AS cantidad,
    COALESCE(SUM(total_financiamiento), 0) AS total_financiamiento,
    MIN(fecha_registro) AS primera_fecha,
    MAX(fecha_registro) AS ultima_fecha
FROM prestamos
GROUP BY estado
ORDER BY cantidad DESC;

-- ============================================================================
-- PASO 5: VERIFICAR AMORTIZACIONES (CUOTAS)
-- ============================================================================
SELECT 
    'PASO 5: Verificación de Amortizaciones (Cuotas)' AS seccion;

-- Total de cuotas generadas
SELECT 
    'Total cuotas generadas' AS metrica,
    COUNT(*) AS valor
FROM cuotas;

-- Cuotas por préstamo
SELECT 
    prestamo_id,
    COUNT(*) AS total_cuotas,
    COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
    COUNT(CASE WHEN estado IN ('PENDIENTE', 'ATRASADO', 'PARCIAL') THEN 1 END) AS cuotas_pendientes,
    COALESCE(SUM(capital_pendiente + interes_pendiente + monto_mora), 0) AS saldo_pendiente
FROM cuotas
GROUP BY prestamo_id
ORDER BY prestamo_id
LIMIT 10;

-- Cuotas por estado
SELECT 
    estado,
    COUNT(*) AS cantidad,
    COALESCE(SUM(monto_cuota), 0) AS total_monto_cuota,
    COALESCE(SUM(capital_pendiente + interes_pendiente + monto_mora), 0) AS saldo_pendiente
FROM cuotas
GROUP BY estado
ORDER BY estado;

-- Cuotas vencidas
SELECT 
    'Cuotas vencidas' AS metrica,
    COUNT(*) AS cantidad,
    COALESCE(SUM(capital_pendiente + interes_pendiente + monto_mora), 0) AS monto_vencido
FROM cuotas
WHERE fecha_vencimiento < CURRENT_DATE 
    AND estado IN ('PENDIENTE', 'ATRASADO', 'PARCIAL');

-- Distribución de cuotas por préstamo
WITH cuotas_por_prestamo AS (
    SELECT 
        prestamo_id,
        COUNT(*) AS total_cuotas
    FROM cuotas
    GROUP BY prestamo_id
),
rangos_cuotas AS (
    SELECT 
        CASE 
            WHEN total_cuotas = 0 THEN 'Sin cuotas'
            WHEN total_cuotas BETWEEN 1 AND 12 THEN '1-12 cuotas'
            WHEN total_cuotas BETWEEN 13 AND 24 THEN '13-24 cuotas'
            WHEN total_cuotas BETWEEN 25 AND 36 THEN '25-36 cuotas'
            ELSE 'Más de 36 cuotas'
        END AS rango_cuotas,
        CASE 
            WHEN total_cuotas = 0 THEN 1
            WHEN total_cuotas BETWEEN 1 AND 12 THEN 2
            WHEN total_cuotas BETWEEN 13 AND 24 THEN 3
            WHEN total_cuotas BETWEEN 25 AND 36 THEN 4
            ELSE 5
        END AS orden
    FROM cuotas_por_prestamo
)
SELECT 
    rango_cuotas,
    COUNT(*) AS cantidad_prestamos
FROM rangos_cuotas
GROUP BY rango_cuotas, orden
ORDER BY orden;

-- Ejemplo de cuotas de un préstamo aprobado
SELECT 
    c.id AS cuota_id,
    c.prestamo_id,
    p.cedula,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.fecha_pago,
    c.monto_cuota,
    c.capital_pendiente,
    c.interes_pendiente,
    c.monto_mora,
    c.estado,
    c.dias_mora
FROM cuotas c
JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
ORDER BY c.prestamo_id, c.numero_cuota
LIMIT 20;

-- ============================================================================
-- PASO 6: VERIFICAR RELACIONES Y CONSISTENCIA
-- ============================================================================
SELECT 
    'PASO 6: Verificación de Relaciones y Consistencia' AS seccion;

-- Préstamos sin cliente asociado
SELECT 
    'Préstamos sin cliente' AS metrica,
    COUNT(*) AS valor
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula
WHERE c.cedula IS NULL;

-- Préstamos aprobados sin cuotas
SELECT 
    'Préstamos aprobados sin cuotas' AS metrica,
    COUNT(DISTINCT p.id) AS valor
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.estado = 'APROBADO' 
    AND c.id IS NULL;

-- Cuotas sin préstamo asociado (NO DEBERÍA HABER)
SELECT 
    'Cuotas sin préstamo' AS metrica,
    COUNT(*) AS valor
FROM cuotas c
LEFT JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.id IS NULL;

-- Consistencia: número de cuotas vs cuotas reales
SELECT 
    p.id AS prestamo_id,
    p.numero_cuotas AS cuotas_planificadas,
    COUNT(c.id) AS cuotas_reales,
    CASE 
        WHEN p.numero_cuotas = COUNT(c.id) THEN 'OK'
        WHEN COUNT(c.id) = 0 THEN 'SIN CUOTAS'
        ELSE 'INCONSISTENTE'
    END AS estado
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.numero_cuotas
HAVING p.numero_cuotas != COUNT(c.id) OR COUNT(c.id) = 0
LIMIT 20;

-- ============================================================================
-- PASO 7: VERIFICAR PAGOS
-- ============================================================================
SELECT 
    'PASO 7: Verificación de Pagos' AS seccion;

-- Total de pagos
SELECT 
    'Total pagos' AS metrica,
    COUNT(*) AS cantidad,
    COALESCE(SUM(monto_pagado), 0) AS total_pagado
FROM pagos;

-- Pagos por estado
SELECT 
    estado,
    COUNT(*) AS cantidad,
    COALESCE(SUM(monto_pagado), 0) AS total_pagado
FROM pagos
GROUP BY estado
ORDER BY estado;

-- Pagos del mes actual
SELECT 
    'Pagos del mes actual' AS metrica,
    COUNT(*) AS cantidad,
    COALESCE(SUM(monto_pagado), 0) AS total_pagado
FROM pagos
WHERE DATE_TRUNC('month', fecha_pago) = DATE_TRUNC('month', CURRENT_DATE);

-- Últimos 10 pagos
SELECT 
    id,
    prestamo_id,
    cedula,
    monto_pagado,
    fecha_pago,
    estado,
    conciliado
FROM pagos
ORDER BY fecha_pago DESC
LIMIT 10;

-- ============================================================================
-- PASO 8: RESUMEN EJECUTIVO
-- ============================================================================
SELECT 
    'PASO 8: Resumen Ejecutivo' AS seccion;

-- Resumen completo del sistema
SELECT 
    'CLIENTES' AS categoria,
    COUNT(*) AS total,
    COUNT(CASE WHEN activo = true THEN 1 END) AS activos
FROM clientes

UNION ALL

SELECT 
    'PRESTAMOS' AS categoria,
    COUNT(*) AS total,
    COUNT(CASE WHEN estado = 'APROBADO' THEN 1 END) AS aprobados
FROM prestamos

UNION ALL

SELECT 
    'CUOTAS' AS categoria,
    COUNT(*) AS total,
    COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END) AS pagadas
FROM cuotas

UNION ALL

SELECT 
    'PAGOS' AS categoria,
    COUNT(*) AS total,
    COUNT(CASE WHEN estado = 'Pagado' THEN 1 END) AS confirmados
FROM pagos;

-- Resumen financiero
SELECT 
    'Resumen Financiero' AS seccion;

SELECT 
    'Cartera Total (Préstamos Aprobados)' AS concepto,
    COALESCE(SUM(total_financiamiento), 0) AS monto
FROM prestamos
WHERE estado = 'APROBADO'

UNION ALL

SELECT 
    'Saldo Pendiente (Cuotas)' AS concepto,
    COALESCE(SUM(capital_pendiente + interes_pendiente + monto_mora), 0) AS monto
FROM cuotas
WHERE estado IN ('PENDIENTE', 'ATRASADO', 'PARCIAL')

UNION ALL

SELECT 
    'Total Pagado (Cuotas)' AS concepto,
    COALESCE(SUM(capital_pagado + interes_pagado + mora_pagada), 0) AS monto
FROM cuotas

UNION ALL

SELECT 
    'Total Pagado (Pagos)' AS concepto,
    COALESCE(SUM(monto_pagado), 0) AS monto
FROM pagos
WHERE estado = 'Pagado';

-- ============================================================================
-- PASO 9: VERIFICAR CATÁLOGOS
-- ============================================================================
SELECT 
    'PASO 9: Verificación de Catálogos' AS seccion;

-- Analistas activos
SELECT 
    'Analistas activos' AS metrica,
    COUNT(*) AS valor
FROM analistas
WHERE activo = true;

-- Concesionarios activos
SELECT 
    'Concesionarios activos' AS metrica,
    COUNT(*) AS valor
FROM concesionarios
WHERE activo = true;

-- Modelos de vehículos activos
SELECT 
    'Modelos de vehículos activos' AS metrica,
    COUNT(*) AS valor
FROM modelos_vehiculos
WHERE activo = true;

-- ============================================================================
-- PASO 10: VERIFICAR DATOS ESPECÍFICOS POR PRÉSTAMO
-- ============================================================================
SELECT 
    'PASO 10: Verificación Detallada por Préstamo (Ejemplo)' AS seccion;

-- Detalle completo de un préstamo (reemplazar ID con uno existente)
SELECT 
    p.id AS prestamo_id,
    p.cedula,
    c.nombres AS nombre_cliente,
    p.producto,
    p.total_financiamiento,
    p.numero_cuotas,
    p.estado AS estado_prestamo,
    p.concesionario,
    p.analista,
    p.modelo_vehiculo,
    COUNT(cu.id) AS total_cuotas_generadas,
    COUNT(CASE WHEN cu.estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
    COUNT(CASE WHEN cu.estado IN ('PENDIENTE', 'ATRASADO', 'PARCIAL') THEN 1 END) AS cuotas_pendientes,
    COALESCE(SUM(cu.capital_pendiente + cu.interes_pendiente + cu.monto_mora), 0) AS saldo_pendiente,
    COALESCE(SUM(cu.capital_pagado + cu.interes_pagado + cu.mora_pagada), 0) AS total_pagado
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.id = (SELECT id FROM prestamos WHERE estado = 'APROBADO' LIMIT 1)
GROUP BY p.id, p.cedula, c.nombres, p.producto, p.total_financiamiento, 
         p.numero_cuotas, p.estado, p.concesionario, p.analista, p.modelo_vehiculo;

-- Cuotas detalladas de ese préstamo
SELECT 
    cu.numero_cuota,
    cu.fecha_vencimiento,
    cu.fecha_pago,
    cu.monto_cuota,
    cu.capital_pendiente,
    cu.interes_pendiente,
    cu.monto_mora,
    cu.capital_pagado,
    cu.interes_pagado,
    cu.mora_pagada,
    cu.estado,
    cu.dias_mora,
    CASE 
        WHEN cu.fecha_vencimiento < CURRENT_DATE AND cu.estado != 'PAGADO' THEN 'VENCIDA'
        WHEN cu.estado = 'PAGADO' THEN 'PAGADA'
        ELSE 'PENDIENTE'
    END AS estado_descripcion
FROM cuotas cu
JOIN prestamos p ON cu.prestamo_id = p.id
WHERE p.id = (SELECT id FROM prestamos WHERE estado = 'APROBADO' LIMIT 1)
ORDER BY cu.numero_cuota;

-- ============================================================================
-- FIN DEL SCRIPT DE VERIFICACIÓN
-- ============================================================================
SELECT 
    'VERIFICACIÓN COMPLETA FINALIZADA' AS mensaje,
    CURRENT_TIMESTAMP AS fecha_verificacion;

