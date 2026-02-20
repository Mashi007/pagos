-- ====================================================================
-- DEMOSTRACIÓN: El nuevo endpoint SÍ encuentra los pagos conciliados
-- ====================================================================
-- Este query simula exactamente lo que hace el nuevo endpoint
-- para el préstamo 4601

SELECT 
    c.numero_cuota,
    c.fecha_vencimiento,
    c.monto_cuota,
    c.pago_id,
    c.estado as cuota_estado,
    -- Búsqueda por rango de fechas (como lo hace el nuevo endpoint)
    COUNT(p.id) as pagos_encontrados,
    MAX(p.id) as pago_id_encontrado,
    MAX(p.monto_pagado) as pago_monto,
    MAX(p.conciliado)::text as pago_conciliado,
    MAX(p.verificado_concordancia) as verificado,
    STRING_AGG(
        'Pago: ' || p.id || ', Monto: $' || p.monto_pagado || ', Fecha: ' || p.fecha_pago || ', Conciliado: ' || p.conciliado,
        ' | '
    ) as detalles_pago
FROM public.cuotas c
LEFT JOIN public.pagos p ON (
    p.prestamo_id = 4601
    AND DATE(p.fecha_pago) >= (c.fecha_vencimiento - interval '15 days')
    AND DATE(p.fecha_pago) <= (c.fecha_vencimiento + interval '15 days')
    AND (p.conciliado = true OR p.verificado_concordancia = 'SI')
)
WHERE c.prestamo_id = 4601
GROUP BY 
    c.id, c.numero_cuota, c.fecha_vencimiento, c.monto_cuota, 
    c.pago_id, c.estado
ORDER BY c.numero_cuota;

-- Resultado esperado:
-- Cada cuota tendrá:
-- - pagos_encontrados = 1 (encontrará el pago conciliado) ✅
-- - pago_id_encontrado = el ID del pago ✅
-- - pago_monto = $240.00 ✅
-- - pago_conciliado = true ✅
