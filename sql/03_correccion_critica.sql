-- SCRIPT DE CORRECCIÓN CRÍTICA: Problemas de conciliación
-- Ejecutar DESPUÉS de validar diagnóstico
-- Fecha: 2026-03-20

-- ============================================================================
-- PROBLEMA 1: 14,127 pagos sin asignar a cuotas (3,426,096.76 BS = 49.2%)
-- ============================================================================

-- Paso 1: Identificar pagos huérfanos (sin prestamo_id)
SELECT COUNT(*) as pagos_sin_prestamo, SUM(monto_pagado) as monto_total
FROM pagos
WHERE prestamo_id IS NULL
  AND NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = pagos.id);

-- Paso 2: Intentar asignar automáticamente a préstamos por cédula
-- (SOLO si el cliente tiene UN SOLO préstamo activo)
INSERT INTO cuota_pagos (cuota_id, pago_id, monto_aplicado, fecha_aplicacion)
SELECT 
  c.id,
  p.id,
  MIN(p.monto_pagado, c.monto - COALESCE(SUM(cp2.monto_aplicado), 0)),
  NOW()
FROM pagos p
JOIN clientes cl ON p.cedula = cl.cedula
JOIN prestamos pr ON cl.id = pr.cliente_id AND pr.estado = 'APROBADO'
JOIN cuotas c ON pr.id = c.prestamo_id AND c.estado IN ('PENDIENTE', 'MORA', 'PARCIAL')
LEFT JOIN cuota_pagos cp2 ON c.id = cp2.cuota_id
WHERE p.prestamo_id IS NULL
  AND NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)
  AND (SELECT COUNT(*) FROM prestamos pr2 WHERE pr2.cliente_id = cl.id AND pr2.estado = 'APROBADO') = 1
GROUP BY c.id, p.id, c.monto
ON CONFLICT DO NOTHING;

-- Paso 3: Registrar asignaciones automáticas en auditoría
INSERT INTO auditoria_conciliacion_manual (pago_id, cuota_id, monto_asignado, tipo_asignacion, resultado)
SELECT cp.pago_id, cp.cuota_id, cp.monto_aplicado, 'AUTOMATICA', 'EXITOSA'
FROM cuota_pagos cp
WHERE NOT EXISTS (SELECT 1 FROM auditoria_conciliacion_manual acm WHERE acm.pago_id = cp.pago_id AND acm.cuota_id = cp.cuota_id)
  AND cp.fecha_aplicacion > NOW() - INTERVAL '5 minutes';  -- últimos 5 minutos

-- ============================================================================
-- PROBLEMA 2: Cuota 216933 sobre-aplicada (96 BS exceso)
-- ============================================================================

-- Paso 1: Verificar el exceso exacto
SELECT 
  c.id,
  c.monto,
  COALESCE(SUM(cp.monto_aplicado), 0) as total_aplicado,
  COALESCE(SUM(cp.monto_aplicado), 0) - c.monto as exceso
FROM cuotas c
LEFT JOIN cuota_pagos cp ON c.id = cp.cuota_id
WHERE c.id = 216933
GROUP BY c.id, c.monto;

-- Paso 2: Obtener historial de pagos aplicados
SELECT 
  cp.id,
  cp.pago_id,
  cp.monto_aplicado,
  p.fecha_pago,
  p.referencia_pago,
  cp.fecha_aplicacion
FROM cuota_pagos cp
JOIN pagos p ON cp.pago_id = p.id
WHERE cp.cuota_id = 216933
ORDER BY cp.fecha_aplicacion;

-- Paso 3: CORRECCIÓN - Reducir el último pago por el exceso
-- Obtener el ID del último cuota_pago
WITH ultimo_pago AS (
  SELECT cp.id, cp.monto_aplicado
  FROM cuota_pagos cp
  WHERE cp.cuota_id = 216933
  ORDER BY cp.fecha_aplicacion DESC
  LIMIT 1
),
exceso_calc AS (
  SELECT COALESCE(SUM(cp.monto_aplicado), 0) - c.monto as exceso
  FROM cuotas c
  LEFT JOIN cuota_pagos cp ON c.id = cp.cuota_id
  WHERE c.id = 216933
  GROUP BY c.monto
)
UPDATE cuota_pagos cp
SET monto_aplicado = (SELECT monto_aplicado FROM ultimo_pago LIMIT 1) - (SELECT exceso FROM exceso_calc LIMIT 1)
WHERE cp.id = (SELECT id FROM ultimo_pago LIMIT 1);

-- Paso 4: Registrar corrección en auditoría
INSERT INTO auditoria_conciliacion_manual (pago_id, cuota_id, monto_asignado, tipo_asignacion, resultado, motivo)
SELECT 
  cp.pago_id,
  cp.cuota_id,
  96.00,  -- El exceso exacto
  'MANUAL',
  'EXITOSA',
  'Corrección de sobre-aplicación: reducción del exceso'
FROM cuota_pagos cp
WHERE cp.cuota_id = 216933
ORDER BY cp.fecha_aplicacion DESC
LIMIT 1
ON CONFLICT DO NOTHING;

-- ============================================================================
-- PROBLEMA 3: Estados inconsistentes (MORA no documentado)
-- ============================================================================

-- Paso 1: Identificar cuotas con estado inconsistente
SELECT 
  c.id,
  c.estado as estado_registrado,
  CASE 
    WHEN COALESCE(SUM(cp.monto_aplicado), 0) >= c.monto - 0.01 THEN 'PAGADO'
    WHEN COALESCE(SUM(cp.monto_aplicado), 0) > 0 THEN 'PARCIAL'
    WHEN DATE(c.fecha_vencimiento) < CURRENT_DATE THEN 'MORA'
    ELSE 'PENDIENTE'
  END as estado_calculado,
  COUNT(*) as count
FROM cuotas c
LEFT JOIN cuota_pagos cp ON c.id = cp.cuota_id
GROUP BY c.id, c.estado, c.monto, c.fecha_vencimiento
HAVING c.estado != CASE 
    WHEN COALESCE(SUM(cp.monto_aplicado), 0) >= c.monto - 0.01 THEN 'PAGADO'
    WHEN COALESCE(SUM(cp.monto_aplicado), 0) > 0 THEN 'PARCIAL'
    WHEN DATE(c.fecha_vencimiento) < CURRENT_DATE THEN 'MORA'
    ELSE 'PENDIENTE'
  END
LIMIT 100;

-- Paso 2: CORRECCIÓN - Actualizar estados
UPDATE cuotas c
SET estado = CASE 
    WHEN COALESCE((SELECT SUM(cp.monto_aplicado) FROM cuota_pagos cp WHERE cp.cuota_id = c.id), 0) >= c.monto - 0.01 THEN 'PAGADO'
    WHEN COALESCE((SELECT SUM(cp.monto_aplicado) FROM cuota_pagos cp WHERE cp.cuota_id = c.id), 0) > 0 THEN 'PARCIAL'
    WHEN DATE(c.fecha_vencimiento) < CURRENT_DATE THEN 'MORA'
    ELSE 'PENDIENTE'
  END
WHERE c.estado != CASE 
    WHEN COALESCE((SELECT SUM(cp.monto_aplicado) FROM cuota_pagos cp WHERE cp.cuota_id = c.id), 0) >= c.monto - 0.01 THEN 'PAGADO'
    WHEN COALESCE((SELECT SUM(cp.monto_aplicado) FROM cuota_pagos cp WHERE cp.cuota_id = c.id), 0) > 0 THEN 'PARCIAL'
    WHEN DATE(c.fecha_vencimiento) < CURRENT_DATE THEN 'MORA'
    ELSE 'PENDIENTE'
  END;

-- ============================================================================
-- VERIFICACIÓN POST-CORRECCIÓN
-- ============================================================================

-- Verificar pagos sin asignar (debe ser 0 o muy bajo)
SELECT COUNT(*) as pagos_sin_asignar, COALESCE(SUM(p.monto_pagado), 0) as monto_no_asignado
FROM pagos p
WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id);

-- Verificar cuota 216933 (debe estar balanceada)
SELECT 
  c.monto,
  COALESCE(SUM(cp.monto_aplicado), 0) as total_aplicado,
  c.monto - COALESCE(SUM(cp.monto_aplicado), 0) as saldo
FROM cuotas c
LEFT JOIN cuota_pagos cp ON c.id = cp.cuota_id
WHERE c.id = 216933
GROUP BY c.monto;

-- Verificar consistencia de estados
SELECT 
  COUNT(*) as cuotas_inconsistentes
FROM cuotas c
LEFT JOIN cuota_pagos cp ON c.id = cp.cuota_id
GROUP BY c.id, c.estado, c.monto, c.fecha_vencimiento
HAVING c.estado != CASE 
    WHEN COALESCE(SUM(cp.monto_aplicado), 0) >= c.monto - 0.01 THEN 'PAGADO'
    WHEN COALESCE(SUM(cp.monto_aplicado), 0) > 0 THEN 'PARCIAL'
    WHEN DATE(c.fecha_vencimiento) < CURRENT_DATE THEN 'MORA'
    ELSE 'PENDIENTE'
  END;

-- Resumen final
SELECT 
  'PAGOS_SIN_ASIGNAR' as problema,
  COUNT(*) as cantidad,
  COALESCE(SUM(monto_pagado), 0) as monto
FROM pagos p
WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)
UNION ALL
SELECT 
  'CUOTAS_SOBRE_APLICADAS',
  COUNT(*),
  COALESCE(SUM((SELECT SUM(cp.monto_aplicado) - c.monto FROM cuota_pagos cp WHERE cp.cuota_id = c.id)), 0)
FROM cuotas c
WHERE (SELECT SUM(monto_aplicado) FROM cuota_pagos WHERE cuota_id = c.id) > c.monto + 0.01
UNION ALL
SELECT 
  'ESTADOS_INCONSISTENTES',
  COUNT(*),
  0
FROM cuotas c
LEFT JOIN cuota_pagos cp ON c.id = cp.cuota_id
GROUP BY c.id, c.estado, c.monto, c.fecha_vencimiento
HAVING c.estado != CASE 
    WHEN COALESCE(SUM(cp.monto_aplicado), 0) >= c.monto - 0.01 THEN 'PAGADO'
    WHEN COALESCE(SUM(cp.monto_aplicado), 0) > 0 THEN 'PARCIAL'
    WHEN DATE(c.fecha_vencimiento) < CURRENT_DATE THEN 'MORA'
    ELSE 'PENDIENTE'
  END;
