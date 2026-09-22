-- =====================================================================
-- Cuánto debemos cobrar: dividido en DEL DÍA (vence hoy), ATRASADO
-- (vencidas y no pagadas / con saldo pendiente) y TOTAL a cobrar.
--
-- Se considera "saldo pendiente" de una cuota como:
--   monto_cuota - COALESCE(total_pagado, 0)
-- y solo se toman cuotas que aún tienen saldo pendiente > 0
-- (excluye cuotas 100% PAGADAS o ANULADAS).
--
-- Ajusta los estados excluidos según tu catálogo real de `cuotas.estado`
-- (PENDIENTE, PARCIAL, VENCIDO, MORA, PAGADO, PAGO_ADELANTADO, ANULADA, etc.)
-- =====================================================================

WITH cuotas_pendientes AS (
    SELECT
        c.id,
        c.prestamo_id,
        c.cliente_id,
        c.numero_cuota,
        c.fecha_vencimiento,
        c.monto_cuota,
        COALESCE(c.total_pagado, 0)                       AS total_pagado,
        (c.monto_cuota - COALESCE(c.total_pagado, 0))      AS saldo_pendiente,
        c.estado
    FROM cuotas c
    JOIN prestamos p ON p.id = c.prestamo_id
    JOIN clientes  cl ON cl.id = p.cliente_id
    WHERE cl.estado = 'ACTIVO'
      AND p.estado = 'APROBADO'
      AND (c.monto_cuota - COALESCE(c.total_pagado, 0)) > 0   -- solo lo que aún se debe
      AND c.estado NOT IN ('PAGADO', 'ANULADA')               -- ajustar según tu catálogo
)
SELECT
    -- Cobro del día: cuotas que vencen exactamente hoy
    COALESCE(SUM(saldo_pendiente) FILTER (WHERE fecha_vencimiento = CURRENT_DATE), 0) AS cobro_dia,

    -- Cobro atrasado: cuotas cuya fecha de vencimiento ya pasó
    COALESCE(SUM(saldo_pendiente) FILTER (WHERE fecha_vencimiento < CURRENT_DATE), 0) AS cobro_atrasado,

    -- (Opcional) Cobro futuro: cuotas que aún no vencen, útil para ver el total completo
    COALESCE(SUM(saldo_pendiente) FILTER (WHERE fecha_vencimiento > CURRENT_DATE), 0) AS cobro_futuro,

    -- Total general a cobrar (día + atrasado + futuro)
    COALESCE(SUM(saldo_pendiente), 0) AS total_a_cobrar,

    -- Conteos de cuotas por cada categoría, útil para validar
    COUNT(*) FILTER (WHERE fecha_vencimiento = CURRENT_DATE) AS cantidad_cuotas_dia,
    COUNT(*) FILTER (WHERE fecha_vencimiento < CURRENT_DATE)  AS cantidad_cuotas_atrasadas,
    COUNT(*) AS cantidad_cuotas_total
FROM cuotas_pendientes;


-- =====================================================================
-- Variante: mismo resultado pero solo con DEL DÍA + ATRASADO + TOTAL
-- (sin la columna de futuro), tal como se pidió explícitamente.
-- =====================================================================

WITH cuotas_pendientes AS (
    SELECT
        c.fecha_vencimiento,
        (c.monto_cuota - COALESCE(c.total_pagado, 0)) AS saldo_pendiente
    FROM cuotas c
    JOIN prestamos p ON p.id = c.prestamo_id
    JOIN clientes  cl ON cl.id = p.cliente_id
    WHERE cl.estado = 'ACTIVO'
      AND p.estado = 'APROBADO'
      AND (c.monto_cuota - COALESCE(c.total_pagado, 0)) > 0
      AND c.estado NOT IN ('PAGADO', 'ANULADA')
)
SELECT
    COALESCE(SUM(saldo_pendiente) FILTER (WHERE fecha_vencimiento = CURRENT_DATE), 0) AS cobro_del_dia,
    COALESCE(SUM(saldo_pendiente) FILTER (WHERE fecha_vencimiento < CURRENT_DATE), 0) AS cobro_atrasado,
    COALESCE(SUM(saldo_pendiente), 0) AS total_general
FROM cuotas_pendientes
WHERE fecha_vencimiento <= CURRENT_DATE;   -- si el "total" debe ser solo día+atrasado (sin futuro)


-- =====================================================================
-- Variante detallada: desglose por cliente/préstamo, útil para reportes
-- =====================================================================

SELECT
    cl.id                     AS cliente_id,
    cl.nombre                 AS cliente_nombre,   -- ajustar si el campo se llama distinto
    p.id                      AS prestamo_id,
    COALESCE(SUM(c.monto_cuota - COALESCE(c.total_pagado, 0))
        FILTER (WHERE c.fecha_vencimiento = CURRENT_DATE), 0)  AS del_dia,
    COALESCE(SUM(c.monto_cuota - COALESCE(c.total_pagado, 0))
        FILTER (WHERE c.fecha_vencimiento < CURRENT_DATE), 0)  AS atrasado,
    COALESCE(SUM(c.monto_cuota - COALESCE(c.total_pagado, 0))
        FILTER (WHERE c.fecha_vencimiento <= CURRENT_DATE), 0) AS total
FROM cuotas c
JOIN prestamos p ON p.id = c.prestamo_id
JOIN clientes  cl ON cl.id = p.cliente_id
WHERE cl.estado = 'ACTIVO'
  AND p.estado = 'APROBADO'
  AND (c.monto_cuota - COALESCE(c.total_pagado, 0)) > 0
  AND c.estado NOT IN ('PAGADO', 'ANULADA')
GROUP BY cl.id, cl.nombre, p.id
HAVING COALESCE(SUM(c.monto_cuota - COALESCE(c.total_pagado, 0))
        FILTER (WHERE c.fecha_vencimiento <= CURRENT_DATE), 0) > 0
ORDER BY total DESC;
