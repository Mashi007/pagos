-- ============================================================================
-- ENCONTRAR PRESTAMOS CON PAGOS PARA PROBAR EN FRONTEND
-- ============================================================================

-- Encontrar préstamos que tienen cuotas PAGADAS para verificar en frontend
SELECT 
    'PRESTAMOS CON CUOTAS PAGADAS PARA PROBAR' AS seccion;

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    LEFT(p.nombres, 40) AS cliente,
    COUNT(DISTINCT CASE WHEN c.estado = 'PAGADO' THEN c.id END) AS cuotas_pagadas,
    COUNT(DISTINCT c.id) AS total_cuotas,
    COALESCE(SUM(pag.monto_pagado), 0) AS total_pagado,
    CASE 
        WHEN COUNT(DISTINCT CASE WHEN c.estado = 'PAGADO' THEN c.id END) = COUNT(DISTINCT c.id) THEN 'TODAS PAGADAS'
        WHEN COUNT(DISTINCT CASE WHEN c.estado = 'PAGADO' THEN c.id END) > 0 THEN 'PARCIALMENTE PAGADAS'
        ELSE 'SIN PAGAR'
    END AS estado_general
FROM prestamos p
INNER JOIN cuotas c ON p.id = c.prestamo_id
LEFT JOIN pagos pag ON p.id = pag.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, p.nombres
HAVING COUNT(DISTINCT CASE WHEN c.estado = 'PAGADO' THEN c.id END) > 0
ORDER BY cuotas_pagadas DESC, prestamo_id ASC
LIMIT 10;

