-- ============================================================================
-- INVESTIGACIÓN DE DISCREPANCIAS CRÍTICAS
-- ============================================================================
-- Script para investigar las cédulas con mayores discrepancias
-- ============================================================================

-- ----------------------------------------------------------------------------
-- INVESTIGAR: J50256769 (Diferencia: $4,079.00)
-- ----------------------------------------------------------------------------

SELECT 
    '=== INVESTIGACIÓN: J50256769 ===' AS info;

-- Abonos desde BD
SELECT 
    'Abonos desde BD (cuotas.total_pagado)' AS fuente,
    p.id AS prestamo_id,
    p.cedula,
    p.total_financiamiento,
    p.numero_cuotas,
    p.estado,
    COALESCE(SUM(c.total_pagado), 0) AS total_abonos_bd,
    COUNT(c.id) AS total_cuotas
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.cedula = 'J50256769'
GROUP BY p.id, p.cedula, p.total_financiamiento, p.numero_cuotas, p.estado;

-- Abonos desde pagos
SELECT 
    'Abonos desde BD (pagos.monto_pagado)' AS fuente,
    SUM(monto_pagado) AS total_abonos_pagos
FROM pagos
WHERE cedula = 'J50256769'
  AND monto_pagado IS NOT NULL
  AND monto_pagado > 0
  AND activo = TRUE;

-- Abonos desde abono_2026
SELECT 
    'Abonos desde abono_2026' AS fuente,
    id,
    cedula,
    abonos,
    fecha_creacion,
    fecha_actualizacion
FROM abono_2026
WHERE cedula = 'J50256769';

-- ----------------------------------------------------------------------------
-- INVESTIGAR: J503848898 (Diferencia: $3,120.00)
-- ----------------------------------------------------------------------------

SELECT 
    '=== INVESTIGACIÓN: J503848898 ===' AS info;

-- Abonos desde BD
SELECT 
    'Abonos desde BD (cuotas.total_pagado)' AS fuente,
    p.id AS prestamo_id,
    p.cedula,
    p.total_financiamiento,
    p.numero_cuotas,
    p.estado,
    COALESCE(SUM(c.total_pagado), 0) AS total_abonos_bd,
    COUNT(c.id) AS total_cuotas
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.cedula = 'J503848898'
GROUP BY p.id, p.cedula, p.total_financiamiento, p.numero_cuotas, p.estado;

-- Abonos desde pagos
SELECT 
    'Abonos desde BD (pagos.monto_pagado)' AS fuente,
    SUM(monto_pagado) AS total_abonos_pagos
FROM pagos
WHERE cedula = 'J503848898'
  AND monto_pagado IS NOT NULL
  AND monto_pagado > 0
  AND activo = TRUE;

-- Abonos desde abono_2026
SELECT 
    'Abonos desde abono_2026' AS fuente,
    id,
    cedula,
    abonos,
    fecha_creacion,
    fecha_actualizacion
FROM abono_2026
WHERE cedula = 'J503848898';

-- ----------------------------------------------------------------------------
-- INVESTIGAR: J501260087 (Diferencia: $1,536.00)
-- ----------------------------------------------------------------------------

SELECT 
    '=== INVESTIGACIÓN: J501260087 ===' AS info;

-- Abonos desde BD
SELECT 
    'Abonos desde BD (cuotas.total_pagado)' AS fuente,
    p.id AS prestamo_id,
    p.cedula,
    p.total_financiamiento,
    p.numero_cuotas,
    p.estado,
    COALESCE(SUM(c.total_pagado), 0) AS total_abonos_bd,
    COUNT(c.id) AS total_cuotas
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.cedula = 'J501260087'
GROUP BY p.id, p.cedula, p.total_financiamiento, p.numero_cuotas, p.estado;

-- Abonos desde pagos
SELECT 
    'Abonos desde BD (pagos.monto_pagado)' AS fuente,
    SUM(monto_pagado) AS total_abonos_pagos
FROM pagos
WHERE cedula = 'J501260087'
  AND monto_pagado IS NOT NULL
  AND monto_pagado > 0
  AND activo = TRUE;

-- Abonos desde abono_2026
SELECT 
    'Abonos desde abono_2026' AS fuente,
    id,
    cedula,
    abonos,
    fecha_creacion,
    fecha_actualizacion
FROM abono_2026
WHERE cedula = 'J501260087';

-- ----------------------------------------------------------------------------
-- VERIFICAR SI HAY MÚLTIPLES PRÉSTAMOS POR CÉDULA
-- ----------------------------------------------------------------------------

SELECT 
    '=== CÉDULAS CON MÚLTIPLES PRÉSTAMOS ===' AS info;

SELECT 
    cedula,
    COUNT(*) AS total_prestamos,
    SUM(total_financiamiento) AS total_financiamiento_sum,
    STRING_AGG(id::text, ', ') AS ids_prestamos
FROM prestamos
WHERE cedula IN ('J50256769', 'J503848898', 'J501260087')
GROUP BY cedula;
