-- Diagnostico: prestamos con la misma "huella" de negocio (posibles duplicados sin sentido).
-- Ejecutar en PostgreSQL (produccion: usar sesion de solo lectura si aplica).
--
-- Criterios:
-- A) Huella estricta: cedula normalizada + fecha requerimiento + total + N cuotas + cuota periodo + tasa + modalidad + producto
-- B) Huella fuerte (sin producto/modalidad): a veces cambian por error de captura
-- C) Mismo cliente_id + fecha_requerimiento + total + cuotas (redundante con cedula si cliente es unico)

-- ---------------------------------------------------------------------------
-- A) Grupos con mas de un prestamo (huella estricta)
-- ---------------------------------------------------------------------------
WITH norm AS (
  SELECT
    id,
    cliente_id,
    btrim(upper(cedula)) AS cedula_n,
    fecha_requerimiento,
    total_financiamiento,
    numero_cuotas,
    cuota_periodo,
    tasa_interes,
    btrim(upper(modalidad_pago)) AS modalidad_n,
    btrim(upper(producto)) AS producto_n,
    estado,
    fecha_registro
  FROM prestamos
)
SELECT
  cedula_n,
  fecha_requerimiento,
  total_financiamiento,
  numero_cuotas,
  cuota_periodo,
  tasa_interes,
  modalidad_n,
  producto_n,
  COUNT(*) AS n_prestamos,
  array_agg(id ORDER BY id) AS prestamo_ids,
  array_agg(estado ORDER BY id) AS estados,
  MIN(fecha_registro) AS primera_fecha_registro,
  MAX(fecha_registro) AS ultima_fecha_registro
FROM norm
GROUP BY
  cedula_n,
  fecha_requerimiento,
  total_financiamiento,
  numero_cuotas,
  cuota_periodo,
  tasa_interes,
  modalidad_n,
  producto_n
HAVING COUNT(*) > 1
ORDER BY n_prestamos DESC, cedula_n, fecha_requerimiento
LIMIT 500;

-- ---------------------------------------------------------------------------
-- B) Huella fuerte (sin producto ni modalidad) — mas sensible a falsos positivos
-- ---------------------------------------------------------------------------
WITH norm AS (
  SELECT
    id,
    cliente_id,
    btrim(upper(cedula)) AS cedula_n,
    fecha_requerimiento,
    total_financiamiento,
    numero_cuotas,
    cuota_periodo,
    estado,
    fecha_registro
  FROM prestamos
)
SELECT
  cedula_n,
  fecha_requerimiento,
  total_financiamiento,
  numero_cuotas,
  cuota_periodo,
  COUNT(*) AS n_prestamos,
  array_agg(id ORDER BY id) AS prestamo_ids,
  array_agg(estado ORDER BY id) AS estados
FROM norm
GROUP BY
  cedula_n,
  fecha_requerimiento,
  total_financiamiento,
  numero_cuotas,
  cuota_periodo
HAVING COUNT(*) > 1
ORDER BY n_prestamos DESC
LIMIT 500;

-- ---------------------------------------------------------------------------
-- Detalle de un grupo (reemplazar valores del WHERE segun filas sospechosas)
-- ---------------------------------------------------------------------------
-- SELECT id, cliente_id, cedula, nombres, estado, total_financiamiento,
--        fecha_requerimiento, numero_cuotas, cuota_periodo, producto, modalidad_pago,
--        fecha_registro, observaciones
-- FROM prestamos
-- WHERE id = ANY (ARRAY[123, 456]);

-- ---------------------------------------------------------------------------
-- C) Misma huella estricta: detalle por prestamo_id con actividad (elegir cual conservar)
--    Prioridad sugerida: mas pagos > mas cuotas > menor id (mas antiguo).
-- ---------------------------------------------------------------------------
WITH norm AS (
  SELECT
    id,
    cliente_id,
    btrim(upper(cedula)) AS cedula_n,
    fecha_requerimiento,
    total_financiamiento,
    numero_cuotas,
    cuota_periodo,
    tasa_interes,
    btrim(upper(modalidad_pago)) AS modalidad_n,
    btrim(upper(producto)) AS producto_n,
    estado,
    fecha_registro,
    fecha_liquidado
  FROM prestamos
),
grp AS (
  SELECT
    cedula_n,
    fecha_requerimiento,
    total_financiamiento,
    numero_cuotas,
    cuota_periodo,
    tasa_interes,
    modalidad_n,
    producto_n
  FROM norm
  GROUP BY
    cedula_n,
    fecha_requerimiento,
    total_financiamiento,
    numero_cuotas,
    cuota_periodo,
    tasa_interes,
    modalidad_n,
    producto_n
  HAVING COUNT(*) > 1
),
base AS (
  SELECT n.*
  FROM norm n
  INNER JOIN grp g
    ON n.cedula_n = g.cedula_n
    AND n.fecha_requerimiento = g.fecha_requerimiento
    AND n.total_financiamiento = g.total_financiamiento
    AND n.numero_cuotas = g.numero_cuotas
    AND n.cuota_periodo = g.cuota_periodo
    AND n.tasa_interes = g.tasa_interes
    AND n.modalidad_n = g.modalidad_n
    AND n.producto_n = g.producto_n
)
SELECT
  b.id AS prestamo_id,
  b.cedula_n,
  b.fecha_requerimiento,
  b.total_financiamiento,
  b.estado AS estado_prestamo,
  b.fecha_registro,
  b.fecha_liquidado,
  (SELECT COUNT(*) FROM cuotas c WHERE c.prestamo_id = b.id) AS n_cuotas,
  (SELECT COUNT(*)::bigint FROM pagos p WHERE p.prestamo_id = b.id) AS n_pagos,
  (SELECT COALESCE(SUM(p.monto_pagado), 0) FROM pagos p WHERE p.prestamo_id = b.id) AS sum_monto_pagos
FROM base b
ORDER BY
  b.cedula_n,
  b.fecha_requerimiento,
  b.total_financiamiento,
  b.id;

-- ---------------------------------------------------------------------------
-- D) Igual que C pero filtrada por UNA cedula (copiar bloque completo).
--     No anadas WHERE suelto: el filtro va en "norm" como abajo.
--     Si esa cedula no tiene duplicados (huella estricta), el resultado sera vacio.
-- ---------------------------------------------------------------------------
WITH norm AS (
  SELECT
    id,
    cliente_id,
    btrim(upper(cedula)) AS cedula_n,
    fecha_requerimiento,
    total_financiamiento,
    numero_cuotas,
    cuota_periodo,
    tasa_interes,
    btrim(upper(modalidad_pago)) AS modalidad_n,
    btrim(upper(producto)) AS producto_n,
    estado,
    fecha_registro,
    fecha_liquidado
  FROM prestamos
  WHERE btrim(upper(cedula)) = 'V6240236'
),
grp AS (
  SELECT
    cedula_n,
    fecha_requerimiento,
    total_financiamiento,
    numero_cuotas,
    cuota_periodo,
    tasa_interes,
    modalidad_n,
    producto_n
  FROM norm
  GROUP BY
    cedula_n,
    fecha_requerimiento,
    total_financiamiento,
    numero_cuotas,
    cuota_periodo,
    tasa_interes,
    modalidad_n,
    producto_n
  HAVING COUNT(*) > 1
),
base AS (
  SELECT n.*
  FROM norm n
  INNER JOIN grp g
    ON n.cedula_n = g.cedula_n
    AND n.fecha_requerimiento = g.fecha_requerimiento
    AND n.total_financiamiento = g.total_financiamiento
    AND n.numero_cuotas = g.numero_cuotas
    AND n.cuota_periodo = g.cuota_periodo
    AND n.tasa_interes = g.tasa_interes
    AND n.modalidad_n = g.modalidad_n
    AND n.producto_n = g.producto_n
)
SELECT
  b.id AS prestamo_id,
  b.cedula_n,
  b.fecha_requerimiento,
  b.total_financiamiento,
  b.estado AS estado_prestamo,
  b.fecha_registro,
  b.fecha_liquidado,
  (SELECT COUNT(*) FROM cuotas c WHERE c.prestamo_id = b.id) AS n_cuotas,
  (SELECT COUNT(*)::bigint FROM pagos p WHERE p.prestamo_id = b.id) AS n_pagos,
  (SELECT COALESCE(SUM(p.monto_pagado), 0) FROM pagos p WHERE p.prestamo_id = b.id) AS sum_monto_pagos
FROM base b
ORDER BY
  b.fecha_requerimiento,
  b.total_financiamiento,
  b.id;
