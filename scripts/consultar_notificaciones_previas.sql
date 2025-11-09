-- ============================================================================
-- SCRIPT PARA CONSULTAR NOTIFICACIONES PREVIAS EN DBEAVER
-- ============================================================================
-- Este script te permite verificar los datos de notificaciones previas
-- y entender cómo se calculan los resultados
-- ============================================================================

-- 0. VERIFICAR VALORES DEL ENUM tiponotificacion
-- ============================================================================
-- Primero verifica qué valores acepta el enum en la base de datos
SELECT 
    t.typname AS enum_name,
    e.enumlabel AS enum_value
FROM pg_type t 
JOIN pg_enum e ON t.oid = e.enumtypid  
WHERE t.typname = 'tiponotificacion'
ORDER BY e.enumsortorder;

-- Verificar si el campo tipo es enum o texto
SELECT 
    column_name,
    data_type,
    udt_name
FROM information_schema.columns
WHERE table_name = 'notificaciones' 
    AND column_name = 'tipo';

-- 1. VER CLIENTES CON CUOTAS PRÓXIMAS A VENCER (5, 3, 1 días)
-- ============================================================================
-- Muestra clientes SIN cuotas atrasadas que tienen cuotas próximas a vencer
SELECT 
    p.id AS prestamo_id,
    p.cedula,
    c.nombres AS nombre_cliente,
    c.email AS correo,
    c.telefono,
    p.modelo_vehiculo,
    p.producto,
    cu.id AS cuota_id,
    cu.numero_cuota,
    cu.fecha_vencimiento,
    cu.estado AS estado_cuota,
    cu.monto_cuota,
    (cu.fecha_vencimiento - CURRENT_DATE) AS dias_antes_vencimiento
FROM prestamos p
INNER JOIN clientes c ON c.id = p.cliente_id
INNER JOIN cuotas cu ON cu.prestamo_id = p.id
WHERE 
    p.estado = 'APROBADO'
    AND cu.fecha_vencimiento IN (
        CURRENT_DATE + INTERVAL '5 days',
        CURRENT_DATE + INTERVAL '3 days',
        CURRENT_DATE + INTERVAL '1 day'
    )
    AND cu.estado IN ('PENDIENTE', 'ADELANTADO')
    -- Verificar que NO tenga cuotas atrasadas
    AND NOT EXISTS (
        SELECT 1 
        FROM cuotas cu_atrasadas
        WHERE cu_atrasadas.prestamo_id = p.id
            AND cu_atrasadas.fecha_vencimiento < CURRENT_DATE
            AND cu_atrasadas.estado != 'PAGADO'
    )
ORDER BY 
    dias_antes_vencimiento ASC,
    cu.fecha_vencimiento ASC;

-- ============================================================================
-- 2. VERIFICAR CUOTAS ATRASADAS POR PRÉSTAMO
-- ============================================================================
-- Muestra préstamos que tienen cuotas atrasadas (NO deberían aparecer en notificaciones previas)
SELECT 
    p.id AS prestamo_id,
    p.cedula,
    c.nombres AS nombre_cliente,
    COUNT(cu_atrasadas.id) AS total_cuotas_atrasadas,
    MIN(cu_atrasadas.fecha_vencimiento) AS primera_cuota_atrasada,
    MAX(cu_atrasadas.fecha_vencimiento) AS ultima_cuota_atrasada
FROM prestamos p
INNER JOIN clientes c ON c.id = p.cliente_id
INNER JOIN cuotas cu_atrasadas ON cu_atrasadas.prestamo_id = p.id
WHERE 
    p.estado = 'APROBADO'
    AND cu_atrasadas.fecha_vencimiento < CURRENT_DATE
    AND cu_atrasadas.estado != 'PAGADO'
GROUP BY p.id, p.cedula, c.nombres
ORDER BY total_cuotas_atrasadas DESC;

-- ============================================================================
-- 3. VER NOTIFICACIONES RELACIONADAS CON NOTIFICACIONES PREVIAS
-- ============================================================================
-- Muestra las notificaciones enviadas relacionadas con los tipos de notificación previa
-- NOTA: Si created_at no existe, la query funcionará igual ordenando por ID
SELECT 
    n.id AS notificacion_id,
    n.cliente_id,
    c.nombres AS nombre_cliente,
    n.tipo::text AS tipo,
    n.estado AS estado_notificacion,
    n.asunto,
    n.enviada_en AS fecha_envio,
    n.error_mensaje,
    CASE 
        WHEN n.tipo::text = 'PAGO_5_DIAS_ANTES' THEN '5 días antes'
        WHEN n.tipo::text = 'PAGO_3_DIAS_ANTES' THEN '3 días antes'
        WHEN n.tipo::text = 'PAGO_1_DIA_ANTES' THEN '1 día antes'
        ELSE n.tipo::text
    END AS tipo_descripcion
FROM notificaciones n
LEFT JOIN clientes c ON c.id = n.cliente_id
WHERE 
    n.tipo::text IN ('PAGO_5_DIAS_ANTES', 'PAGO_3_DIAS_ANTES', 'PAGO_1_DIA_ANTES')
    -- Si el enum no permite estos valores, buscar por LIKE o usar CAST
    -- OR n.tipo::text LIKE '%PAGO%'
ORDER BY 
    n.id DESC,
    n.cliente_id;

-- FIN: Detener procesamiento aquí

-- ============================================================================
-- 4. RESUMEN DE NOTIFICACIONES PREVIAS POR ESTADO
-- ============================================================================
-- Muestra un resumen de las notificaciones previas agrupadas por estado
-- NOTA: Usa n.id para ordenar si created_at no existe
SELECT 
    n.estado,
    n.tipo,
    COUNT(*) AS total,
    COUNT(DISTINCT n.cliente_id) AS clientes_unicos,
    MIN(n.id) AS primera_notificacion_id,
    MAX(n.id) AS ultima_notificacion_id
FROM notificaciones n
WHERE 
    n.tipo::text IN ('PAGO_5_DIAS_ANTES', 'PAGO_3_DIAS_ANTES', 'PAGO_1_DIA_ANTES')
    -- Si el enum no permite estos valores, buscar por LIKE
    -- OR n.tipo::text LIKE '%PAGO%'
GROUP BY 
    n.estado,
    n.tipo
ORDER BY 
    n.tipo,
    n.estado;

-- ============================================================================
-- 5. CLIENTES QUE DEBERÍAN APARECER EN NOTIFICACIONES PREVIAS HOY
-- ============================================================================
-- Query que replica la lógica del servicio para verificar resultados
WITH cuotas_proximas AS (
    SELECT 
        p.id AS prestamo_id,
        p.cliente_id,
        p.cedula,
        c.nombres,
        c.email,
        c.telefono,
        p.modelo_vehiculo,
        p.producto,
        cu.id AS cuota_id,
        cu.numero_cuota,
        cu.fecha_vencimiento,
        cu.monto_cuota,
        (cu.fecha_vencimiento - CURRENT_DATE) AS dias_antes
    FROM prestamos p
    INNER JOIN clientes c ON c.id = p.cliente_id
    INNER JOIN cuotas cu ON cu.prestamo_id = p.id
    WHERE 
        p.estado = 'APROBADO'
        AND cu.fecha_vencimiento IN (
            CURRENT_DATE + INTERVAL '5 days',
            CURRENT_DATE + INTERVAL '3 days',
            CURRENT_DATE + INTERVAL '1 day'
        )
        AND cu.estado IN ('PENDIENTE', 'ADELANTADO')
        -- Verificar que NO tenga cuotas atrasadas
        AND NOT EXISTS (
            SELECT 1 
            FROM cuotas cu_atrasadas
            WHERE cu_atrasadas.prestamo_id = p.id
                AND cu_atrasadas.fecha_vencimiento < CURRENT_DATE
                AND cu_atrasadas.estado != 'PAGADO'
        )
)
SELECT 
    cp.*,
    CASE 
        WHEN cp.dias_antes = 5 THEN 'PAGO_5_DIAS_ANTES'
        WHEN cp.dias_antes = 3 THEN 'PAGO_3_DIAS_ANTES'
        WHEN cp.dias_antes = 1 THEN 'PAGO_1_DIA_ANTES'
    END AS tipo_notificacion_esperado,
    n.id AS notificacion_id,
    n.estado AS estado_notificacion,
    n.enviada_en AS fecha_envio_notificacion,
    n.error_mensaje,
    CASE 
        WHEN n.id IS NULL THEN 'PENDIENTE'
        ELSE n.estado
    END AS estado_final
FROM cuotas_proximas cp
LEFT JOIN notificaciones n ON 
    n.cliente_id = cp.cliente_id
    AND n.tipo::text = CASE 
        WHEN cp.dias_antes = 5 THEN 'PAGO_5_DIAS_ANTES'
        WHEN cp.dias_antes = 3 THEN 'PAGO_3_DIAS_ANTES'
        WHEN cp.dias_antes = 1 THEN 'PAGO_1_DIA_ANTES'
    END
    -- Notificaciones recientes (usando ID como aproximación si created_at no existe)
    AND n.id >= (SELECT COALESCE(MAX(id) - 1000, 1) FROM notificaciones)  -- Últimas ~1000 notificaciones
ORDER BY 
    cp.dias_antes ASC,
    cp.fecha_vencimiento ASC;

-- ============================================================================
-- 6. ESTADÍSTICAS DE NOTIFICACIONES PREVIAS
-- ============================================================================
SELECT 
    'Total clientes con cuotas próximas' AS descripcion,
    COUNT(DISTINCT p.cliente_id) AS valor
FROM prestamos p
INNER JOIN cuotas cu ON cu.prestamo_id = p.id
WHERE 
    p.estado = 'APROBADO'
    AND cu.fecha_vencimiento IN (
        CURRENT_DATE + INTERVAL '5 days',
        CURRENT_DATE + INTERVAL '3 days',
        CURRENT_DATE + INTERVAL '1 day'
    )
    AND cu.estado IN ('PENDIENTE', 'ADELANTADO')
    AND NOT EXISTS (
        SELECT 1 
        FROM cuotas cu_atrasadas
        WHERE cu_atrasadas.prestamo_id = p.id
            AND cu_atrasadas.fecha_vencimiento < CURRENT_DATE
            AND cu_atrasadas.estado != 'PAGADO'
    )

UNION ALL

SELECT 
    '5 días antes',
    COUNT(*)
FROM prestamos p
INNER JOIN cuotas cu ON cu.prestamo_id = p.id
WHERE 
    p.estado = 'APROBADO'
    AND cu.fecha_vencimiento = CURRENT_DATE + INTERVAL '5 days'
    AND cu.estado IN ('PENDIENTE', 'ADELANTADO')
    AND NOT EXISTS (
        SELECT 1 
        FROM cuotas cu_atrasadas
        WHERE cu_atrasadas.prestamo_id = p.id
            AND cu_atrasadas.fecha_vencimiento < CURRENT_DATE
            AND cu_atrasadas.estado != 'PAGADO'
    )

UNION ALL

SELECT 
    '3 días antes',
    COUNT(*)
FROM prestamos p
INNER JOIN cuotas cu ON cu.prestamo_id = p.id
WHERE 
    p.estado = 'APROBADO'
    AND cu.fecha_vencimiento = CURRENT_DATE + INTERVAL '3 days'
    AND cu.estado IN ('PENDIENTE', 'ADELANTADO')
    AND NOT EXISTS (
        SELECT 1 
        FROM cuotas cu_atrasadas
        WHERE cu_atrasadas.prestamo_id = p.id
            AND cu_atrasadas.fecha_vencimiento < CURRENT_DATE
            AND cu_atrasadas.estado != 'PAGADO'
    )

UNION ALL

SELECT 
    '1 día antes',
    COUNT(*)
FROM prestamos p
INNER JOIN cuotas cu ON cu.prestamo_id = p.id
WHERE 
    p.estado = 'APROBADO'
    AND cu.fecha_vencimiento = CURRENT_DATE + INTERVAL '1 day'
    AND cu.estado IN ('PENDIENTE', 'ADELANTADO')
    AND NOT EXISTS (
        SELECT 1 
        FROM cuotas cu_atrasadas
        WHERE cu_atrasadas.prestamo_id = p.id
            AND cu_atrasadas.fecha_vencimiento < CURRENT_DATE
            AND cu_atrasadas.estado != 'PAGADO'
    );

-- ============================================================================
-- 7. VERIFICAR ESTRUCTURA DE TABLAS
-- ============================================================================
-- Verificar que las columnas necesarias existan
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE 
    table_name IN ('notificaciones', 'prestamos', 'cuotas', 'clientes')
    AND column_name IN (
        'estado', 'tipo', 'cliente_id', 
        'fecha_vencimiento', 'modelo_vehiculo', 'email', 'telefono'
    )
ORDER BY 
    table_name,
    column_name;

-- Verificar si existen columnas específicas en notificaciones
SELECT 
    column_name,
    data_type,
    CASE 
        WHEN column_name = 'canal' THEN 'La columna canal EXISTE'
        WHEN column_name = 'created_at' THEN 'La columna created_at EXISTE'
        WHEN column_name = 'fecha_creacion' THEN 'La columna fecha_creacion EXISTE'
        ELSE 'Columna encontrada'
    END AS estado
FROM information_schema.columns 
WHERE table_name = 'notificaciones' 
    AND column_name IN ('canal', 'created_at', 'fecha_creacion')
ORDER BY column_name;

-- ============================================================================
-- 8. ÚLTIMAS NOTIFICACIONES PREVIAS ENVIADAS
-- ============================================================================
SELECT 
    n.id,
    n.cliente_id,
    c.nombres AS cliente,
    n.tipo,
    n.estado,
    -- n.canal,  -- Columna puede no existir, comentada
    n.asunto,
    n.enviada_en,
    -- n.created_at,  -- Columna puede no existir, usando ID para ordenar
    n.error_mensaje
FROM notificaciones n
LEFT JOIN clientes c ON c.id = n.cliente_id
WHERE 
    n.tipo::text IN ('PAGO_5_DIAS_ANTES', 'PAGO_3_DIAS_ANTES', 'PAGO_1_DIA_ANTES')
    -- Si el enum no permite estos valores, buscar por LIKE
    -- OR n.tipo::text LIKE '%PAGO%'
ORDER BY 
    n.id DESC  -- Ordenar por ID descendente (más recientes primero)
LIMIT 50;

