-- Corregir fecha_pago en pagos usando la fecha de la cuota relacionada
-- Usa cuotas.fecha_pago si existe, sino usa cuotas.fecha_vencimiento

UPDATE pagos p
SET fecha_pago = COALESCE(
    c.fecha_pago::timestamp,
    c.fecha_vencimiento::timestamp,
    p.fecha_pago  -- Mantener la actual si no hay cuota relacionada
),
fecha_actualizacion = CURRENT_TIMESTAMP
FROM cuotas c
WHERE p.prestamo_id = c.prestamo_id
  AND p.numero_cuota = c.numero_cuota
  AND p.numero_documento LIKE 'ABONO_2026_%'
  AND p.activo = TRUE
  AND c.total_pagado > 0;
