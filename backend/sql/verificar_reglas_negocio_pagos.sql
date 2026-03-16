-- =============================================================================
-- VERIFICAR QUE TODOS LOS PAGOS CUMPLEN REGLAS DE NEGOCIO
-- =============================================================================
-- Reglas tomadas del modelo Pago, schemas y endpoint pagos.py.
-- Ejecutar cada bloque y revisar que los conteos de "incumplen" sean 0.
-- =============================================================================

-- 0) Total de pagos
SELECT COUNT(*) AS total_pagos FROM pagos;

-- ========== 1) MONTO > 0 (mínimo 0.01, máximo 999,999,999,999.99) ==========
SELECT COUNT(*) AS incumplen_monto
  FROM pagos
 WHERE monto_pagado IS NULL
    OR monto_pagado < 0.01
    OR monto_pagado > 999999999999.99;

-- Detalle (si hay filas, hay incumplimientos)
SELECT id, cedula, fecha_pago, monto_pagado, numero_documento
  FROM pagos
 WHERE monto_pagado IS NULL
    OR monto_pagado < 0.01
    OR monto_pagado > 999999999999.99
 ORDER BY id
 LIMIT 50;

-- ========== 2) FECHA_PAGO NOT NULL ==========
SELECT COUNT(*) AS incumplen_fecha_pago_null FROM pagos WHERE fecha_pago IS NULL;

-- ========== 3) REFERENCIA_PAGO NOT NULL (en BD tiene default '') ==========
SELECT COUNT(*) AS incumplen_referencia_null FROM pagos WHERE referencia_pago IS NULL;

-- ========== 4) NUMERO_DOCUMENTO sin duplicados (no dos filas con mismo doc no vacío) ==========
SELECT COUNT(*) AS duplicados_numero_documento
  FROM (
    SELECT numero_documento, COUNT(*) AS cnt
      FROM pagos
     WHERE TRIM(COALESCE(numero_documento, '')) <> ''
     GROUP BY numero_documento
    HAVING COUNT(*) > 1
  ) t;

-- Listar documentos duplicados (si hay)
SELECT numero_documento, COUNT(*) AS veces
  FROM pagos
 WHERE TRIM(COALESCE(numero_documento, '')) <> ''
 GROUP BY numero_documento
HAVING COUNT(*) > 1
 ORDER BY 2 DESC;

-- ========== 5) LONGITUD numero_documento y referencia_pago <= 100 ==========
SELECT COUNT(*) AS incumplen_longitud_100
  FROM pagos
 WHERE LENGTH(COALESCE(numero_documento, '')) > 100
    OR LENGTH(COALESCE(referencia_pago, '')) > 100;

-- ========== 6) PRESTAMO_ID en rango (1 .. 2147483647) si está informado ==========
SELECT COUNT(*) AS incumplen_prestamo_id_rango
  FROM pagos
 WHERE prestamo_id IS NOT NULL
   AND (prestamo_id < 1 OR prestamo_id > 2147483647);

-- ========== 7) PRESTAMO_ID existe en tabla prestamos (integridad referencial) ==========
SELECT COUNT(*) AS prestamo_id_huérfanos
  FROM pagos p
  LEFT JOIN prestamos pr ON pr.id = p.prestamo_id
 WHERE p.prestamo_id IS NOT NULL
   AND pr.id IS NULL;

-- ========== 8) CONCILIADO coherente con ESTADO (si conciliado=true, estado debería ser PAGADO) ==========
SELECT COUNT(*) AS conciliado_true_estado_distinto_pagado
  FROM pagos
 WHERE conciliado = true
   AND (estado IS NULL OR TRIM(estado) <> 'PAGADO');

-- Detalle
SELECT id, cedula, estado, conciliado, verificado_concordancia
  FROM pagos
 WHERE conciliado = true
   AND (estado IS NULL OR TRIM(estado) <> 'PAGADO')
 ORDER BY id
 LIMIT 50;

-- ========== 9) ESTADO solo valores esperados (PENDIENTE, PAGADO o NULL) ==========
SELECT COUNT(*) AS estado_no_reconocido
  FROM pagos
 WHERE estado IS NOT NULL
   AND TRIM(estado) NOT IN ('PENDIENTE', 'PAGADO');

-- Valores distintos de estado (revisar a mano)
SELECT estado, COUNT(*) AS cantidad FROM pagos GROUP BY estado ORDER BY estado;

-- ========== 10) FECHA_REGISTRO NOT NULL ==========
SELECT COUNT(*) AS incumplen_fecha_registro_null FROM pagos WHERE fecha_registro IS NULL;

-- ========== RESUMEN: CUÁNTOS PAGOS INCUMPLEN ALGUNA REGLA ==========
-- (Pago incumple si falla al menos una de las reglas anteriores)
WITH incumplimientos AS (
  SELECT id FROM pagos WHERE monto_pagado IS NULL OR monto_pagado < 0.01 OR monto_pagado > 999999999999.99
  UNION
  SELECT id FROM pagos WHERE fecha_pago IS NULL
  UNION
  SELECT id FROM pagos WHERE referencia_pago IS NULL
  UNION
  SELECT p.id
    FROM pagos p
   WHERE TRIM(COALESCE(p.numero_documento, '')) <> ''
     AND (SELECT COUNT(*) FROM pagos p2
          WHERE TRIM(COALESCE(p2.numero_documento, '')) = TRIM(COALESCE(p.numero_documento, ''))) > 1
  UNION
  SELECT id FROM pagos
   WHERE LENGTH(COALESCE(numero_documento, '')) > 100 OR LENGTH(COALESCE(referencia_pago, '')) > 100
  UNION
  SELECT id FROM pagos
   WHERE prestamo_id IS NOT NULL AND (prestamo_id < 1 OR prestamo_id > 2147483647)
  UNION
  SELECT p.id FROM pagos p LEFT JOIN prestamos pr ON pr.id = p.prestamo_id
   WHERE p.prestamo_id IS NOT NULL AND pr.id IS NULL
  UNION
  SELECT id FROM pagos
   WHERE estado IS NOT NULL AND TRIM(estado) NOT IN ('PENDIENTE', 'PAGADO')
  UNION
  SELECT id FROM pagos WHERE fecha_registro IS NULL
)
SELECT COUNT(DISTINCT id) AS total_pagos_que_incumplen_algunas_reglas FROM incumplimientos;
