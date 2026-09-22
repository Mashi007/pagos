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
    cl.nombres                 AS cliente_nombre,   -- columna real: clientes.nombres
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
GROUP BY cl.id, cl.nombres, p.id
HAVING COALESCE(SUM(c.monto_cuota - COALESCE(c.total_pagado, 0))
        FILTER (WHERE c.fecha_vencimiento <= CURRENT_DATE), 0) > 0
ORDER BY total DESC;


-- =====================================================================
-- RESUMEN GENERAL: Total general de préstamos, Total por cobrar y
-- Total cobrado. Pensado como los 3 KPIs principales del dashboard.
--
--   * total_general_prestamos: suma de `total_financiamiento` de todos
--     los préstamos APROBADOS de clientes ACTIVOS (monto financiado
--     total de la cartera).
--   * total_por_cobrar: suma del saldo pendiente de todas las cuotas
--     no pagadas/anuladas (monto_cuota - total_pagado), sin importar
--     si están al día, del día o atrasadas (incluye futuras).
--   * total_cobrado: suma de lo efectivamente pagado (total_pagado)
--     en todas las cuotas.
--
-- Nota: total_general_prestamos = total_por_cobrar + total_cobrado
-- (aprox.), salvo diferencias por redondeo, cuotas especiales o
-- ajustes manuales.
-- =====================================================================

SELECT
    -- Total general de préstamos (monto financiado de la cartera activa)
    (
        SELECT COALESCE(SUM(p.total_financiamiento), 0)
        FROM prestamos p
        JOIN clientes cl ON cl.id = p.cliente_id
        WHERE cl.estado = 'ACTIVO'
          AND p.estado = 'APROBADO'
    ) AS total_general_prestamos,

    -- Total por cobrar (saldo pendiente de todas las cuotas, incluye futuras)
    (
        SELECT COALESCE(SUM(c.monto_cuota - COALESCE(c.total_pagado, 0)), 0)
        FROM cuotas c
        JOIN prestamos p ON p.id = c.prestamo_id
        JOIN clientes cl ON cl.id = p.cliente_id
        WHERE cl.estado = 'ACTIVO'
          AND p.estado = 'APROBADO'
          AND c.estado NOT IN ('PAGADO', 'ANULADA')
    ) AS total_por_cobrar,

    -- Total cobrado (suma de lo efectivamente pagado en las cuotas)
    (
        SELECT COALESCE(SUM(COALESCE(c.total_pagado, 0)), 0)
        FROM cuotas c
        JOIN prestamos p ON p.id = c.prestamo_id
        JOIN clientes cl ON cl.id = p.cliente_id
        WHERE cl.estado = 'ACTIVO'
          AND p.estado = 'APROBADO'
    ) AS total_cobrado;


-- =====================================================================
-- Misma consulta anterior pero en una sola pasada (más eficiente que
-- 3 subconsultas), útil para tablas grandes.
-- =====================================================================

SELECT
    COALESCE(SUM(prest.total_financiamiento), 0)                              AS total_general_prestamos,
    COALESCE(SUM(cuo.por_cobrar), 0)                                          AS total_por_cobrar,
    COALESCE(SUM(cuo.cobrado), 0)                                             AS total_cobrado
FROM (
    SELECT p.id, p.total_financiamiento
    FROM prestamos p
    JOIN clientes cl ON cl.id = p.cliente_id
    WHERE cl.estado = 'ACTIVO'
      AND p.estado = 'APROBADO'
) prest
LEFT JOIN (
    SELECT
        c.prestamo_id,
        SUM(CASE WHEN c.estado NOT IN ('PAGADO', 'ANULADA')
                 THEN c.monto_cuota - COALESCE(c.total_pagado, 0)
                 ELSE 0 END) AS por_cobrar,
        SUM(COALESCE(c.total_pagado, 0)) AS cobrado
    FROM cuotas c
    GROUP BY c.prestamo_id
) cuo ON cuo.prestamo_id = prest.id;


-- =====================================================================
-- TABLA RESUMEN (3 FILAS): Total General Préstamos / Total por Cobrar /
-- Total Cobrado. Formato listo para mostrar como tabla en un reporte
-- (concepto + monto), en lugar de columnas.
-- =====================================================================

WITH base AS (
    SELECT
        p.id                                            AS prestamo_id,
        p.total_financiamiento                          AS total_financiamiento,
        COALESCE(c.monto_cuota, 0)                       AS monto_cuota,
        COALESCE(c.total_pagado, 0)                      AS total_pagado,
        c.estado                                         AS estado_cuota
    FROM prestamos p
    JOIN clientes cl ON cl.id = p.cliente_id
    LEFT JOIN cuotas c ON c.prestamo_id = p.id
    WHERE cl.estado = 'ACTIVO'
      AND p.estado = 'APROBADO'
),
totales AS (
    SELECT
        (SELECT COALESCE(SUM(total_financiamiento), 0)
         FROM prestamos p
         JOIN clientes cl ON cl.id = p.cliente_id
         WHERE cl.estado = 'ACTIVO' AND p.estado = 'APROBADO')          AS total_general_prestamos,
        COALESCE(SUM(monto_cuota - total_pagado)
            FILTER (WHERE estado_cuota NOT IN ('PAGADO', 'ANULADA')), 0) AS total_por_cobrar,
        COALESCE(SUM(total_pagado), 0)                                  AS total_cobrado
    FROM base
)
SELECT 'Total General Préstamos' AS concepto, total_general_prestamos AS monto FROM totales
UNION ALL
SELECT 'Total por Cobrar'        AS concepto, total_por_cobrar        AS monto FROM totales
UNION ALL
SELECT 'Total Cobrado'           AS concepto, total_cobrado           AS monto FROM totales;


-- =====================================================================
-- VALIDACIÓN: por qué Total General Préstamos no coincide exacto con
-- (Total por Cobrar + Total Cobrado). La diferencia suele venir de
-- cuotas PAGADO/ANULADA cuyo total_pagado no coincide con monto_cuota
-- (pago parcial antes de anular, redondeos, cuotas especiales, etc.),
-- porque esas cuotas quedan fuera del filtro de "por cobrar".
-- =====================================================================

SELECT
    tg.total_general_prestamos,
    tot.total_por_cobrar,
    tot.total_cobrado,
    (tot.total_por_cobrar + tot.total_cobrado)                       AS suma_por_cobrar_mas_cobrado,
    tg.total_general_prestamos - (tot.total_por_cobrar + tot.total_cobrado) AS diferencia,
    dif.total_no_contabilizado_en_cuotas_pagadas_anuladas
FROM (
    SELECT COALESCE(SUM(p.total_financiamiento), 0) AS total_general_prestamos
    FROM prestamos p
    JOIN clientes cl ON cl.id = p.cliente_id
    WHERE cl.estado = 'ACTIVO' AND p.estado = 'APROBADO'
) tg
CROSS JOIN (
    SELECT
        COALESCE(SUM(c.monto_cuota - COALESCE(c.total_pagado, 0))
            FILTER (WHERE c.estado NOT IN ('PAGADO', 'ANULADA')), 0) AS total_por_cobrar,
        COALESCE(SUM(COALESCE(c.total_pagado, 0)), 0)                AS total_cobrado
    FROM cuotas c
    JOIN prestamos p ON p.id = c.prestamo_id
    JOIN clientes cl ON cl.id = p.cliente_id
    WHERE cl.estado = 'ACTIVO' AND p.estado = 'APROBADO'
) tot
CROSS JOIN (
    -- Saldo "perdido" en cuotas PAGADO/ANULADA donde total_pagado != monto_cuota
    SELECT COALESCE(SUM(c.monto_cuota - COALESCE(c.total_pagado, 0)), 0)
        AS total_no_contabilizado_en_cuotas_pagadas_anuladas
    FROM cuotas c
    JOIN prestamos p ON p.id = c.prestamo_id
    JOIN clientes cl ON cl.id = p.cliente_id
    WHERE cl.estado = 'ACTIVO' AND p.estado = 'APROBADO'
      AND c.estado IN ('PAGADO', 'ANULADA')
) dif;


-- =====================================================================
-- Detalle de cuotas PAGADO/ANULADA con desfase (para localizar el
-- origen exacto de la diferencia de $1,209.01 u otra que aparezca)
-- =====================================================================

SELECT
    c.id            AS cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    c.estado,
    c.monto_cuota,
    c.total_pagado,
    (c.monto_cuota - COALESCE(c.total_pagado, 0)) AS desfase
FROM cuotas c
JOIN prestamos p ON p.id = c.prestamo_id
JOIN clientes cl ON cl.id = p.cliente_id
WHERE cl.estado = 'ACTIVO'
  AND p.estado = 'APROBADO'
  AND c.estado IN ('PAGADO', 'ANULADA')
  AND (c.monto_cuota - COALESCE(c.total_pagado, 0)) <> 0
ORDER BY ABS(c.monto_cuota - COALESCE(c.total_pagado, 0)) DESC;


-- =====================================================================
-- DESGLOSE: Total Préstamos, Liquidados, Desistimiento, Atrasados y
-- Al Día. Alineado a la lógica real de cobranzas (`prestamo_estados.py`
-- + `universo_analisis_service.py`), NO al filtro simple que usan las
-- consultas anteriores de este archivo.
--
--   * Total Préstamos: todos, sin filtrar por estado.
--   * Liquidados: p.estado = 'LIQUIDADO'.
--   * Desistimiento: p.estado IN ('DESISTIMIENTO','DESESTIMADO','DESISTIDO')
--     (variantes legacy, misma regla que ESTADOS_PRESTAMO_DESISTIMIENTO_VARIANTES).
--   * Atrasados: cartera "activa para cobranza" (no LIQUIDADO ni
--     DESISTIMIENTO) que tiene AL MENOS una cuota vencida con saldo
--     pendiente (fecha_vencimiento < hoy y monto_cuota > total_pagado).
--   * Al Día: cartera activa para cobranza SIN ninguna cuota vencida
--     con saldo pendiente (el resto de la cartera activa).
--
-- Nota: Total Préstamos = Liquidados + Desistimiento + Atrasados + Al Día
-- (deben cuadrar exacto, a diferencia de los montos USD anteriores).
-- =====================================================================

WITH prestamos_base AS (
    SELECT
        p.id,
        p.cliente_id,
        UPPER(TRIM(COALESCE(p.estado, ''))) AS estado_norm
    FROM prestamos p
),
prestamos_atraso AS (
    SELECT DISTINCT c.prestamo_id
    FROM cuotas c
    WHERE c.fecha_vencimiento < CURRENT_DATE
      AND (c.monto_cuota - COALESCE(c.total_pagado, 0)) > 0
)
SELECT 'Total Préstamos' AS concepto, COUNT(*) AS cantidad
FROM prestamos_base

UNION ALL

SELECT 'Préstamos Liquidados', COUNT(*)
FROM prestamos_base
WHERE estado_norm = 'LIQUIDADO'

UNION ALL

SELECT 'Préstamos Desistimiento', COUNT(*)
FROM prestamos_base
WHERE estado_norm IN ('DESISTIMIENTO', 'DESESTIMADO', 'DESISTIDO')

UNION ALL

SELECT 'Préstamos Atrasados', COUNT(*)
FROM prestamos_base pb
JOIN prestamos_atraso pa ON pa.prestamo_id = pb.id
WHERE pb.estado_norm NOT IN ('LIQUIDADO', 'DESISTIMIENTO', 'DESESTIMADO', 'DESISTIDO')

UNION ALL

SELECT 'Préstamos Al Día',
       COUNT(*) - (
           SELECT COUNT(*)
           FROM prestamos_base pb2
           JOIN prestamos_atraso pa2 ON pa2.prestamo_id = pb2.id
           WHERE pb2.estado_norm NOT IN ('LIQUIDADO', 'DESISTIMIENTO', 'DESESTIMADO', 'DESISTIDO')
       )
FROM prestamos_base
WHERE estado_norm NOT IN ('LIQUIDADO', 'DESISTIMIENTO', 'DESESTIMADO', 'DESISTIDO');


-- =====================================================================
-- Misma tabla anterior, en una sola pasada con CASE (más simple/rápida)
-- =====================================================================

WITH prestamos_base AS (
    SELECT
        p.id,
        UPPER(TRIM(COALESCE(p.estado, ''))) AS estado_norm
    FROM prestamos p
),
prestamos_atraso AS (
    SELECT DISTINCT c.prestamo_id
    FROM cuotas c
    WHERE c.fecha_vencimiento < CURRENT_DATE
      AND (c.monto_cuota - COALESCE(c.total_pagado, 0)) > 0
)
SELECT
    COUNT(*)                                                              AS total_prestamos,
    COUNT(*) FILTER (WHERE pb.estado_norm = 'LIQUIDADO')                  AS liquidados,
    COUNT(*) FILTER (WHERE pb.estado_norm IN ('DESISTIMIENTO','DESESTIMADO','DESISTIDO')) AS desistimiento,
    COUNT(*) FILTER (
        WHERE pb.estado_norm NOT IN ('LIQUIDADO','DESISTIMIENTO','DESESTIMADO','DESISTIDO')
          AND pa.prestamo_id IS NOT NULL
    )                                                                      AS atrasados,
    COUNT(*) FILTER (
        WHERE pb.estado_norm NOT IN ('LIQUIDADO','DESISTIMIENTO','DESESTIMADO','DESISTIDO')
          AND pa.prestamo_id IS NULL
    )                                                                      AS al_dia
FROM prestamos_base pb
LEFT JOIN prestamos_atraso pa ON pa.prestamo_id = pb.id;


-- =====================================================================
-- DESGLOSE DE "TOTAL POR COBRAR": Cartera A Tiempo, Atrasada y en Mora.
--
-- Regla oficial de mora del sistema (backend/app/services/cuota_estado.py,
-- NO inventada): una cuota vencida entra en MORA cuando pasan 4 meses
-- calendario desde `fecha_vencimiento` + 6 días de buffer
-- (MORA_DESDE_MESES=4, MORA_BUFFER_DIAS=6). Antes de eso, sigue VENCIDA
-- ("Atrasada"), no en mora.
--
--   * A Tiempo: fecha_vencimiento >= hoy (aún no vence), con saldo pendiente.
--   * Atrasada (VENCIDO): fecha_vencimiento < hoy, pero todavía no cumple
--     los 4 meses + 6 días desde el vencimiento.
--   * Mora (MORA): fecha_vencimiento < hoy y ya cumplió 4 meses + 6 días
--     desde el vencimiento.
--
-- Nota: usa INTERVAL de PostgreSQL para sumar meses calendario, igual
-- que `_sumar_meses_calendario` + buffer en el código Python oficial.
-- =====================================================================

WITH cuotas_pendientes AS (
    SELECT
        c.fecha_vencimiento,
        (c.fecha_vencimiento + INTERVAL '4 months' + INTERVAL '6 days')::date AS inicio_mora,
        (c.monto_cuota - COALESCE(c.total_pagado, 0)) AS saldo_pendiente
    FROM cuotas c
    JOIN prestamos p ON p.id = c.prestamo_id
    JOIN clientes  cl ON cl.id = p.cliente_id
    WHERE cl.estado = 'ACTIVO'
      AND p.estado = 'APROBADO'
      AND (c.monto_cuota - COALESCE(c.total_pagado, 0)) > 0
      AND c.estado NOT IN ('PAGADO', 'ANULADA')
)
SELECT 'Cartera A Tiempo' AS concepto,
       COALESCE(SUM(saldo_pendiente) FILTER (WHERE fecha_vencimiento >= CURRENT_DATE), 0) AS monto
FROM cuotas_pendientes

UNION ALL

SELECT 'Cartera Atrasada (Vencido, aún sin Mora)',
       COALESCE(SUM(saldo_pendiente) FILTER (
           WHERE fecha_vencimiento < CURRENT_DATE
             AND CURRENT_DATE < inicio_mora
       ), 0)
FROM cuotas_pendientes

UNION ALL

SELECT 'Cartera en Mora',
       COALESCE(SUM(saldo_pendiente) FILTER (
           WHERE fecha_vencimiento < CURRENT_DATE
             AND CURRENT_DATE >= inicio_mora
       ), 0)
FROM cuotas_pendientes

UNION ALL

SELECT 'Total por Cobrar',
       COALESCE(SUM(saldo_pendiente), 0)
FROM cuotas_pendientes;


-- =====================================================================
-- Misma consulta anterior en una sola fila (columnas en vez de filas)
-- =====================================================================

WITH cuotas_pendientes AS (
    SELECT
        c.fecha_vencimiento,
        (c.fecha_vencimiento + INTERVAL '4 months' + INTERVAL '6 days')::date AS inicio_mora,
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
    COALESCE(SUM(saldo_pendiente) FILTER (WHERE fecha_vencimiento >= CURRENT_DATE), 0) AS cartera_a_tiempo,
    COALESCE(SUM(saldo_pendiente) FILTER (
        WHERE fecha_vencimiento < CURRENT_DATE AND CURRENT_DATE < inicio_mora
    ), 0) AS cartera_atrasada,
    COALESCE(SUM(saldo_pendiente) FILTER (
        WHERE fecha_vencimiento < CURRENT_DATE AND CURRENT_DATE >= inicio_mora
    ), 0) AS cartera_mora,
    COALESCE(SUM(saldo_pendiente), 0) AS total_por_cobrar
FROM cuotas_pendientes;


-- =====================================================================
-- Variante con desglose por préstamo (para tabla/listado, no solo KPI)
-- =====================================================================

SELECT
    p.id                              AS prestamo_id,
    cl.nombres                         AS cliente_nombre,  -- columna real: clientes.nombres
    p.total_financiamiento            AS total_general_prestamo,
    COALESCE(SUM(
        CASE WHEN c.estado NOT IN ('PAGADO', 'ANULADA')
             THEN c.monto_cuota - COALESCE(c.total_pagado, 0)
             ELSE 0 END
    ), 0)                             AS total_por_cobrar,
    COALESCE(SUM(COALESCE(c.total_pagado, 0)), 0) AS total_cobrado
FROM prestamos p
JOIN clientes cl ON cl.id = p.cliente_id
LEFT JOIN cuotas c ON c.prestamo_id = p.id
WHERE cl.estado = 'ACTIVO'
  AND p.estado = 'APROBADO'
GROUP BY p.id, cl.nombres, p.total_financiamiento
ORDER BY p.id;
