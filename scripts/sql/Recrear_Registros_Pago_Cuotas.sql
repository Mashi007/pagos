-- ================================================================
-- RECREAR REGISTROS EN pago_cuotas para Cuotas con Pagos
-- ================================================================
-- Este script intenta recrear los registros faltantes en pago_cuotas
-- basándose en los pagos existentes en la tabla pagos
-- ================================================================
-- ⚠️ IMPORTANTE: Ejecutar primero en modo de solo lectura (SELECT)
-- para verificar los resultados antes de aplicar cambios
-- ================================================================

-- ================================================================
-- PASO 1: IDENTIFICAR CUOTAS SIN REGISTRO EN pago_cuotas
-- ================================================================
CREATE OR REPLACE VIEW cuotas_sin_pago_cuotas_detalle AS
SELECT 
    c.id AS cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    c.total_pagado,
    c.monto_cuota,
    c.estado,
    c.fecha_vencimiento,
    (SELECT COUNT(*) FROM pagos p WHERE p.prestamo_id = c.prestamo_id) AS cantidad_pagos_prestamo,
    (SELECT COALESCE(SUM(monto_pagado), 0) FROM pagos p WHERE p.prestamo_id = c.prestamo_id) AS total_pagos_prestamo
FROM cuotas c
WHERE c.total_pagado > 0
  AND NOT EXISTS (
      SELECT 1 FROM pago_cuotas pc WHERE pc.cuota_id = c.id
  );

-- Ver resumen
SELECT 
    'PASO 1: Cuotas sin registro en pago_cuotas' AS paso,
    COUNT(*) AS total_cuotas,
    COUNT(DISTINCT prestamo_id) AS total_prestamos,
    SUM(total_pagado) AS total_pagado_sin_registro
FROM cuotas_sin_pago_cuotas_detalle;

-- ================================================================
-- PASO 2: VERIFICAR SI EXISTEN PAGOS PARA ESTOS PRÉSTAMOS
-- ================================================================
SELECT 
    'PASO 2: Verificación de pagos existentes' AS paso,
    c.prestamo_id,
    COUNT(DISTINCT c.id) AS cuotas_afectadas,
    SUM(c.total_pagado) AS total_pagado_cuotas,
    COUNT(DISTINCT p.id) AS cantidad_pagos_en_tabla,
    COALESCE(SUM(p.monto_pagado), 0) AS total_pagos_en_tabla,
    CASE 
        WHEN COUNT(DISTINCT p.id) > 0 THEN '✅ HAY PAGOS'
        ELSE '❌ NO HAY PAGOS'
    END AS estado
FROM cuotas c
LEFT JOIN pagos p ON p.prestamo_id = c.prestamo_id
WHERE c.total_pagado > 0
  AND NOT EXISTS (
      SELECT 1 FROM pago_cuotas pc WHERE pc.cuota_id = c.id
  )
GROUP BY c.prestamo_id
ORDER BY c.prestamo_id;

-- ================================================================
-- PASO 3: INTENTAR RECREAR REGISTROS (SOLO PREVIEW - NO EJECUTA)
-- ================================================================
-- Este query muestra QUÉ registros se crearían
SELECT 
    'PASO 3: PREVIEW - Registros que se crearían' AS paso,
    p.id AS pago_id,
    c.id AS cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    p.monto_pagado AS monto_pago,
    c.total_pagado AS total_pagado_cuota,
    CASE 
        WHEN c.total_pagado >= c.monto_cuota THEN c.monto_cuota - (c.total_pagado - c.monto_cuota)
        ELSE c.total_pagado
    END AS monto_aplicado_estimado,
    p.fecha_pago
FROM cuotas c
INNER JOIN pagos p ON p.prestamo_id = c.prestamo_id
WHERE c.total_pagado > 0
  AND NOT EXISTS (
      SELECT 1 FROM pago_cuotas pc WHERE pc.cuota_id = c.id
  )
ORDER BY c.prestamo_id, c.numero_cuota, p.fecha_pago
LIMIT 50;

-- ================================================================
-- PASO 4: RECREAR REGISTROS (EJECUTAR SOLO SI PASO 3 ES CORRECTO)
-- ================================================================
-- ⚠️ ADVERTENCIA: Este script intenta recrear los registros
-- pero puede no ser 100% preciso si los pagos se aplicaron
-- de forma diferente al orden esperado
--
-- ESTRATEGIA:
-- 1. Para cada préstamo con cuotas sin registro
-- 2. Obtener los pagos ordenados por fecha
-- 3. Aplicar los pagos a las cuotas más antiguas primero
-- 4. Crear registros en pago_cuotas

-- ⚠️ COMENTAR ESTE BLOQUE HASTA VERIFICAR QUE ES CORRECTO
/*
DO $$
DECLARE
    rec_cuota RECORD;
    rec_pago RECORD;
    monto_restante NUMERIC;
    monto_aplicar NUMERIC;
    saldo_pago NUMERIC;
BEGIN
    -- Para cada préstamo con cuotas afectadas
    FOR rec_cuota IN 
        SELECT DISTINCT prestamo_id 
        FROM cuotas_sin_pago_cuotas_detalle
        ORDER BY prestamo_id
    LOOP
        -- Obtener pagos del préstamo ordenados por fecha
        FOR rec_pago IN 
            SELECT id, monto_pagado, fecha_pago
            FROM pagos
            WHERE prestamo_id = rec_cuota.prestamo_id
            ORDER BY fecha_pago, id
        LOOP
            saldo_pago := rec_pago.monto_pagado;
            
            -- Aplicar el pago a las cuotas más antiguas primero
            FOR rec_cuota IN 
                SELECT id, numero_cuota, total_pagado, monto_cuota, capital_pendiente, interes_pendiente
                FROM cuotas
                WHERE prestamo_id = rec_cuota.prestamo_id
                  AND total_pagado > 0
                  AND NOT EXISTS (
                      SELECT 1 FROM pago_cuotas WHERE cuota_id = cuotas.id
                  )
                ORDER BY numero_cuota
            LOOP
                IF saldo_pago <= 0 THEN
                    EXIT; -- Salir del loop de cuotas
                END IF;
                
                -- Calcular cuánto aplicar a esta cuota
                monto_aplicar := LEAST(
                    saldo_pago,
                    rec_cuota.total_pagado -- Usar el total_pagado como referencia
                );
                
                IF monto_aplicar > 0 THEN
                    -- Crear registro en pago_cuotas
                    INSERT INTO pago_cuotas (
                        pago_id,
                        cuota_id,
                        monto_aplicado,
                        aplicado_a_capital,
                        aplicado_a_interes,
                        aplicado_a_mora
                    )
                    VALUES (
                        rec_pago.id,
                        rec_cuota.id,
                        monto_aplicar,
                        monto_aplicar * (rec_cuota.capital_pendiente / NULLIF(rec_cuota.capital_pendiente + rec_cuota.interes_pendiente, 0)),
                        monto_aplicar * (rec_cuota.interes_pendiente / NULLIF(rec_cuota.capital_pendiente + rec_cuota.interes_pendiente, 0)),
                        0
                    );
                    
                    saldo_pago := saldo_pago - monto_aplicar;
                END IF;
            END LOOP;
        END LOOP;
    END LOOP;
END $$;
*/

-- ================================================================
-- PASO 5: VERIFICACIÓN POST-RECREACIÓN
-- ================================================================
-- Después de ejecutar el PASO 4, verificar que los registros se crearon
SELECT 
    'PASO 5: Verificación post-recreación' AS paso,
    COUNT(*) AS cuotas_sin_registro_restantes,
    COUNT(DISTINCT prestamo_id) AS prestamos_afectados
FROM cuotas c
WHERE c.total_pagado > 0
  AND NOT EXISTS (
      SELECT 1 FROM pago_cuotas pc WHERE pc.cuota_id = c.id
  );

-- ================================================================
-- PASO 6: ALTERNATIVA SIMPLE - Marcar como "Pago Histórico"
-- ================================================================
-- Si no se puede determinar la relación exacta, crear un registro
-- genérico que represente "pago histórico migrado"
--
-- ⚠️ SOLO EJECUTAR SI NO SE PUEDE RECREAR LOS REGISTROS EXACTOS
/*
-- Crear un pago "fantasma" para cada préstamo afectado
-- y asociarlo a todas las cuotas con pagos pero sin registro

INSERT INTO pagos (
    prestamo_id,
    monto_pagado,
    fecha_pago,
    estado,
    conciliado,
    observaciones
)
SELECT DISTINCT
    prestamo_id,
    0, -- Monto 0 porque ya está aplicado en cuotas
    MIN(fecha_pago) OVER (PARTITION BY prestamo_id),
    'PAGADO',
    true,
    'Pago histórico migrado - Recreado para integridad referencial'
FROM cuotas
WHERE total_pagado > 0
  AND NOT EXISTS (
      SELECT 1 FROM pago_cuotas WHERE cuota_id = cuotas.id
  );

-- Luego asociar este pago a las cuotas
-- (código adicional necesario)
*/

