-- ============================================
-- VERIFICACIÓN: CONEXIÓN DASHBOARD PAGOS
-- ============================================
-- Diagnóstico de datos necesarios para el dashboard de pagos
-- Verifica que existan datos para que el dashboard muestre información

-- ============================================
-- PARTE 1: VERIFICAR DATOS EN TABLA PAGOS
-- ============================================
SELECT 
    '=== DATOS EN TABLA PAGOS ===' AS verificacion,
    COUNT(*) AS total_pagos,
    COUNT(CASE WHEN fecha_pago >= DATE_TRUNC('month', CURRENT_DATE) THEN 1 END) AS pagos_mes_actual,
    COUNT(CASE WHEN conciliado = TRUE THEN 1 END) AS pagos_conciliados,
    COUNT(CASE WHEN conciliado = FALSE THEN 1 END) AS pagos_no_conciliados,
    COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END) AS pagos_estado_pagado,
    COUNT(CASE WHEN estado = 'PENDIENTE' THEN 1 END) AS pagos_estado_pendiente,
    SUM(monto_pagado) AS total_monto_pagado,
    AVG(monto_pagado) AS promedio_monto_pagado
FROM pagos;

-- ============================================
-- PARTE 2: VERIFICAR DATOS PARA KPIs
-- ============================================
-- Estos datos son necesarios para /api/v1/pagos/kpis

-- 1. Monto Cobrado en el Mes (actual)
SELECT 
    '=== KPI: MONTO COBRADO EN EL MES ===' AS verificacion,
    COUNT(*) AS total_pagos_mes,
    SUM(monto_pagado) AS monto_cobrado_mes,
    MIN(fecha_pago) AS primera_fecha_pago,
    MAX(fecha_pago) AS ultima_fecha_pago
FROM pagos
WHERE fecha_pago >= DATE_TRUNC('month', CURRENT_DATE)
  AND fecha_pago < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month';

-- 2. Saldo por Cobrar
SELECT 
    '=== KPI: SALDO POR COBRAR ===' AS verificacion,
    COUNT(*) AS total_cuotas_pendientes,
    SUM(capital_pendiente + interes_pendiente + COALESCE(monto_mora, 0)) AS saldo_por_cobrar,
    SUM(capital_pendiente) AS capital_pendiente_total,
    SUM(interes_pendiente) AS interes_pendiente_total,
    SUM(COALESCE(monto_mora, 0)) AS mora_total
FROM cuotas c
JOIN prestamos p ON c.prestamo_id = p.id
WHERE c.estado != 'PAGADO'
  AND p.estado = 'APROBADO';

-- 3. Clientes en Mora
SELECT 
    '=== KPI: CLIENTES EN MORA ===' AS verificacion,
    COUNT(DISTINCT p.cedula) AS clientes_en_mora,
    COUNT(c.id) AS total_cuotas_en_mora
FROM prestamos p
JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.estado = 'APROBADO'
  AND c.fecha_vencimiento < CURRENT_DATE
  AND c.estado IN ('PENDIENTE', 'ATRASADO', 'PARCIAL');

-- 4. Clientes al Día
WITH clientes_con_cuotas AS (
    SELECT DISTINCT p.cedula
    FROM prestamos p
    JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.estado = 'APROBADO'
),
clientes_en_mora AS (
    SELECT DISTINCT p.cedula
    FROM prestamos p
    JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.estado = 'APROBADO'
      AND c.fecha_vencimiento < CURRENT_DATE
      AND c.estado IN ('PENDIENTE', 'ATRASADO', 'PARCIAL')
)
SELECT 
    '=== KPI: CLIENTES AL DÍA ===' AS verificacion,
    COUNT(DISTINCT cc.cedula) AS total_clientes_con_cuotas,
    COUNT(DISTINCT cm.cedula) AS total_clientes_en_mora,
    COUNT(DISTINCT cc.cedula) - COUNT(DISTINCT cm.cedula) AS clientes_al_dia
FROM clientes_con_cuotas cc
LEFT JOIN clientes_en_mora cm ON cc.cedula = cm.cedula;

-- ============================================
-- PARTE 3: VERIFICAR DATOS PARA /stats
-- ============================================
-- Estos datos son necesarios para /api/v1/pagos/stats

SELECT 
    '=== STATS: RESUMEN GENERAL ===' AS verificacion,
    COUNT(*) AS total_pagos,
    SUM(monto_pagado) AS total_pagado,
    COUNT(CASE WHEN fecha_pago::date = CURRENT_DATE THEN 1 END) AS pagos_hoy,
    AVG(monto_pagado) AS promedio_monto
FROM pagos;

SELECT 
    '=== STATS: PAGOS POR ESTADO ===' AS verificacion,
    estado,
    COUNT(*) AS cantidad,
    SUM(monto_pagado) AS total_monto
FROM pagos
GROUP BY estado
ORDER BY cantidad DESC;

-- Cuotas pagadas vs pendientes
SELECT 
    '=== STATS: CUOTAS PAGADAS VS PENDIENTES ===' AS verificacion,
    COUNT(CASE WHEN c.estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
    COUNT(CASE WHEN c.estado IN ('PENDIENTE', 'ATRASADO', 'PARCIAL') THEN 1 END) AS cuotas_pendientes,
    COUNT(CASE WHEN c.fecha_vencimiento < CURRENT_DATE AND c.estado != 'PAGADO' THEN 1 END) AS cuotas_atrasadas,
    COUNT(*) AS total_cuotas
FROM cuotas c
JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO';

-- ============================================
-- PARTE 4: VERIFICAR PROBLEMAS POTENCIALES
-- ============================================
-- Pagos sin fecha_pago válida
SELECT 
    '=== PROBLEMAS: PAGOS SIN FECHA VÁLIDA ===' AS verificacion,
    COUNT(*) AS pagos_sin_fecha_valida
FROM pagos
WHERE fecha_pago IS NULL 
   OR fecha_pago < '2000-01-01'
   OR fecha_pago > CURRENT_DATE + INTERVAL '1 year';

-- Pagos con monto_pagado NULL o <= 0
SELECT 
    '=== PROBLEMAS: PAGOS CON MONTO INVÁLIDO ===' AS verificacion,
    COUNT(*) AS pagos_con_monto_invalido
FROM pagos
WHERE monto_pagado IS NULL 
   OR monto_pagado <= 0;

-- Cuotas sin prestamo_id válido
SELECT 
    '=== PROBLEMAS: CUOTAS SIN PRESTAMO VÁLIDO ===' AS verificacion,
    COUNT(*) AS cuotas_sin_prestamo_valido
FROM cuotas c
LEFT JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.id IS NULL
   OR p.estado != 'APROBADO';

-- ============================================
-- PARTE 5: MUESTRA DE DATOS RECIENTES
-- ============================================
-- Últimos 10 pagos registrados
SELECT 
    '=== MUESTRA: ÚLTIMOS 10 PAGOS ===' AS verificacion,
    id,
    cedula_cliente,
    prestamo_id,
    fecha_pago,
    monto_pagado,
    estado,
    conciliado,
    fecha_registro
FROM pagos
ORDER BY fecha_registro DESC NULLS LAST, id DESC
LIMIT 10;

-- Últimas 10 cuotas (para verificar estados)
SELECT 
    '=== MUESTRA: ÚLTIMAS 10 CUOTAS ===' AS verificacion,
    c.id,
    c.prestamo_id,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.estado,
    c.capital_pendiente,
    c.interes_pendiente,
    c.monto_mora,
    p.cedula,
    p.estado AS estado_prestamo
FROM cuotas c
JOIN prestamos p ON c.prestamo_id = p.id
ORDER BY c.id DESC
LIMIT 10;

-- ============================================
-- PARTE 6: RESUMEN FINAL
-- ============================================
SELECT 
    '=== RESUMEN: CONEXIÓN DASHBOARD PAGOS ===' AS verificacion,
    CASE 
        WHEN (SELECT COUNT(*) FROM pagos) > 0 THEN '✅ Hay datos de pagos'
        ELSE '❌ NO hay datos de pagos - Dashboard mostrará vacío'
    END AS estado_pagos,
    CASE 
        WHEN (SELECT COUNT(*) FROM cuotas) > 0 THEN '✅ Hay datos de cuotas'
        ELSE '❌ NO hay datos de cuotas - KPIs de mora no funcionarán'
    END AS estado_cuotas,
    CASE 
        WHEN (SELECT COUNT(*) FROM prestamos WHERE estado = 'APROBADO') > 0 THEN '✅ Hay préstamos aprobados'
        ELSE '❌ NO hay préstamos aprobados - No se pueden calcular KPIs'
    END AS estado_prestamos,
    CASE 
        WHEN (SELECT COUNT(*) FROM pagos WHERE fecha_pago >= DATE_TRUNC('month', CURRENT_DATE)) > 0 THEN '✅ Hay pagos del mes actual'
        ELSE '⚠️ NO hay pagos del mes actual - Monto Cobrado será 0'
    END AS estado_pagos_mes,
    CASE 
        WHEN (SELECT COUNT(*) FROM cuotas WHERE estado != 'PAGADO') > 0 THEN '✅ Hay cuotas pendientes'
        ELSE '⚠️ NO hay cuotas pendientes - Saldo por Cobrar será 0'
    END AS estado_cuotas_pendientes;

-- ============================================
-- PARTE 7: VERIFICAR ENDPOINTS REQUERIDOS
-- ============================================
-- Confirmar que los datos necesarios para cada endpoint existan

-- Endpoint: GET /api/v1/pagos/ (listar pagos)
SELECT 
    '=== ENDPOINT: GET /api/v1/pagos/ ===' AS verificacion,
    CASE 
        WHEN (SELECT COUNT(*) FROM pagos) > 0 THEN '✅ Hay pagos - El endpoint devolverá datos'
        ELSE '❌ NO hay pagos - El endpoint devolverá array vacío'
    END AS estado_datos,
    (SELECT COUNT(*) FROM pagos) AS total_pagos_disponibles,
    'Este endpoint lista pagos con paginación (page, per_page)' AS nota;

-- Endpoint: GET /api/v1/pagos/kpis
SELECT 
    '=== ENDPOINT: GET /api/v1/pagos/kpis ===' AS verificacion,
    CASE 
        WHEN (SELECT COUNT(*) FROM pagos WHERE fecha_pago >= DATE_TRUNC('month', CURRENT_DATE)) > 0 
        THEN '✅ Hay pagos del mes - montoCobradoMes tendrá valor'
        ELSE '⚠️ NO hay pagos del mes - montoCobradoMes será 0'
    END AS estado_monto_cobrado,
    CASE 
        WHEN (SELECT COUNT(*) FROM cuotas WHERE estado != 'PAGADO') > 0 
        THEN '✅ Hay cuotas pendientes - saldoPorCobrar tendrá valor'
        ELSE '⚠️ NO hay cuotas pendientes - saldoPorCobrar será 0'
    END AS estado_saldo_por_cobrar,
    CASE 
        WHEN (SELECT COUNT(DISTINCT p.cedula) FROM prestamos p JOIN cuotas c ON p.id = c.prestamo_id WHERE p.estado = 'APROBADO' AND c.fecha_vencimiento < CURRENT_DATE AND c.estado IN ('PENDIENTE', 'ATRASADO', 'PARCIAL')) > 0 
        THEN '✅ Hay clientes en mora - clientesEnMora tendrá valor'
        ELSE '⚠️ NO hay clientes en mora - clientesEnMora será 0'
    END AS estado_clientes_en_mora;

-- Endpoint: GET /api/v1/pagos/stats
SELECT 
    '=== ENDPOINT: GET /api/v1/pagos/stats ===' AS verificacion,
    CASE 
        WHEN (SELECT COUNT(*) FROM pagos) > 0 
        THEN '✅ Hay pagos - stats mostrará datos'
        ELSE '❌ NO hay pagos - stats mostrará todos en 0'
    END AS estado_datos,
    (SELECT COUNT(DISTINCT estado) FROM pagos) AS estados_diferentes,
    'Este endpoint devuelve total_pagos, pagos_por_estado, total_pagado, cuotas_pagadas, cuotas_pendientes' AS nota;

-- ============================================
-- PARTE 8: RECOMENDACIONES
-- ============================================
SELECT 
    '=== RECOMENDACIONES ===' AS verificacion,
    CASE 
        WHEN (SELECT COUNT(*) FROM pagos) = 0 THEN '⚠️ Registrar al menos un pago para que el dashboard muestre datos'
        WHEN (SELECT COUNT(*) FROM pagos WHERE fecha_pago >= DATE_TRUNC('month', CURRENT_DATE)) = 0 THEN '⚠️ Registrar pagos del mes actual para que "Monto Cobrado Mes" muestre datos'
        ELSE '✅ Hay datos suficientes para mostrar el dashboard'
    END AS recomendacion_pagos,
    CASE 
        WHEN (SELECT COUNT(*) FROM cuotas) = 0 THEN '⚠️ Generar tablas de amortización para que los KPIs de mora funcionen'
        WHEN (SELECT COUNT(*) FROM cuotas WHERE estado != 'PAGADO') = 0 THEN '⚠️ Las cuotas están todas pagadas - KPIs mostrarán valores mínimos'
        ELSE '✅ Hay cuotas pendientes - KPIs funcionarán correctamente'
    END AS recomendacion_cuotas;

-- ============================================
-- PARTE 9: VERIFICAR PROBLEMAS COMUNES
-- ============================================
-- Errores que pueden causar que el dashboard no muestre datos

SELECT 
    '=== PROBLEMAS COMUNES ===' AS verificacion,
    'Causa posible' AS problema,
    'Solución' AS solucion
UNION ALL
SELECT 
    'PROBLEMAS',
    'Tabla pagos está vacía',
    'Registrar al menos un pago usando el formulario o carga masiva'
UNION ALL
SELECT 
    'PROBLEMAS',
    'Pagos con fecha_pago NULL o inválida',
    'Corregir fechas usando script Corregir_Errores_Pagos.sql'
UNION ALL
SELECT 
    'PROBLEMAS',
    'Error de conexión al backend',
    'Verificar que el servidor backend esté corriendo y accesible'
UNION ALL
SELECT 
    'PROBLEMAS',
    'Error de autenticación (401)',
    'Verificar token de autenticación, hacer login nuevamente'
UNION ALL
SELECT 
    'PROBLEMAS',
    'Filtros muy restrictivos',
    'Limpiar filtros en el dashboard para ver todos los pagos'
UNION ALL
SELECT 
    'PROBLEMAS',
    'Fecha de pagos fuera del rango visible',
    'Ajustar filtros de fecha o verificar fechas en la BD';

-- ============================================
-- FIN DEL DIAGNÓSTICO
-- ============================================
-- Si el dashboard muestra "No se encontraron pagos", verifica:
-- 1. Si hay datos en la tabla pagos (PARTE 1)
-- 2. Si hay pagos del mes actual (PARTE 2)
-- 3. Si hay problemas con los datos (PARTE 4)
-- 4. Revisa las recomendaciones finales (PARTE 6)
-- 5. Verifica endpoints requeridos (PARTE 7)
-- 6. Revisa problemas comunes (PARTE 9)

