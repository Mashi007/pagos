-- =============================================================================
-- Comprobación integral por cédula (PostgreSQL) — ejecutar el archivo completo
-- =============================================================================
-- Cambia SOLO el literal en la línea INSERT (ej. V13442440).
-- Crea tablas temporales de sesión y luego corre los SELECT de verificación.
--
-- Nota: CURRENT_DATE es la fecha del servidor PostgreSQL.
-- =============================================================================

BEGIN;

DROP TABLE IF EXISTS tmp_chk_cu;
DROP TABLE IF EXISTS tmp_chk_pr;
DROP TABLE IF EXISTS tmp_chk_cl;
DROP TABLE IF EXISTS tmp_chk_cedula;

CREATE TEMP TABLE tmp_chk_cedula (cedula_norm text NOT NULL);
-- <<< Cambiar cédula aquí >>>
INSERT INTO tmp_chk_cedula (cedula_norm) VALUES (
    upper(replace(replace(trim('V13442440'), '-', ''), ' ', ''))
);

CREATE TEMP TABLE tmp_chk_cl AS
SELECT c.*
FROM clientes c
JOIN tmp_chk_cedula p
  ON upper(replace(replace(trim(coalesce(c.cedula, '')), '-', ''), ' ', '')) = p.cedula_norm;

CREATE TEMP TABLE tmp_chk_pr AS
SELECT pr.*
FROM prestamos pr
JOIN tmp_chk_cedula p ON true
WHERE pr.cliente_id IN (SELECT id FROM tmp_chk_cl)
   OR upper(replace(replace(trim(coalesce(pr.cedula, '')), '-', ''), ' ', '')) = p.cedula_norm;

CREATE TEMP TABLE tmp_chk_cu AS
SELECT cu.*
FROM cuotas cu
WHERE cu.prestamo_id IN (SELECT id FROM tmp_chk_pr);

COMMIT;

-- ---------------------------------------------------------------------------
-- 1) Cabecera
-- ---------------------------------------------------------------------------
SELECT
    '1_cliente_encontrado' AS seccion,
    (SELECT count(*)::int FROM tmp_chk_cl) AS filas_cliente,
    (SELECT count(*)::int FROM tmp_chk_pr) AS filas_prestamo,
    (SELECT count(*)::int FROM tmp_chk_cu) AS filas_cuota,
    (SELECT cedula_norm FROM tmp_chk_cedula) AS cedula_buscada;

-- ---------------------------------------------------------------------------
-- 2) Ficha cliente
-- ---------------------------------------------------------------------------
SELECT
    '2_ficha_cliente' AS seccion,
    c.id AS cliente_id,
    c.cedula,
    c.nombres,
    c.email,
    c.telefono,
    c.estado AS estado_cliente,
    c.fecha_registro,
    c.fecha_actualizacion
FROM tmp_chk_cl c
ORDER BY c.id;

-- ---------------------------------------------------------------------------
-- 3) Préstamos
-- ---------------------------------------------------------------------------
SELECT
    '3_prestamos' AS seccion,
    p.id AS prestamo_id,
    p.cliente_id,
    p.cedula AS cedula_en_prestamo,
    p.estado,
    p.total_financiamiento,
    p.numero_cuotas,
    p.fecha_requerimiento,
    p.fecha_aprobacion,
    p.fecha_liquidado,
    p.modalidad_pago,
    p.producto,
    p.modelo_vehiculo,
    p.concesionario
FROM tmp_chk_pr p
ORDER BY p.id;

-- ---------------------------------------------------------------------------
-- 4) Cuotas — agregado por préstamo
-- ---------------------------------------------------------------------------
SELECT
    '4_cuotas_por_prestamo' AS seccion,
    cu.prestamo_id,
    count(*)::int AS total_cuotas,
    count(*) FILTER (WHERE cu.fecha_pago IS NULL)::int AS pendientes,
    count(*) FILTER (WHERE cu.fecha_pago IS NOT NULL)::int AS pagadas,
    coalesce(sum(cu.monto_cuota), 0) AS suma_monto_cuotas,
    coalesce(sum(cu.total_pagado) FILTER (WHERE cu.fecha_pago IS NULL), 0) AS suma_abonos_sobre_pendientes,
    min(cu.fecha_vencimiento) FILTER (WHERE cu.fecha_pago IS NULL) AS primera_fv_pendiente,
    max(cu.fecha_vencimiento) FILTER (WHERE cu.fecha_pago IS NULL) AS ultima_fv_pendiente
FROM tmp_chk_cu cu
GROUP BY cu.prestamo_id
ORDER BY cu.prestamo_id;

-- ---------------------------------------------------------------------------
-- 5) Cuotas — detalle
-- ---------------------------------------------------------------------------
SELECT
    '5_cuotas_detalle' AS seccion,
    cu.id AS cuota_id,
    cu.prestamo_id,
    cu.cliente_id,
    cu.numero_cuota,
    cu.fecha_vencimiento,
    cu.fecha_pago,
    cu.monto_cuota,
    cu.total_pagado,
    cu.dias_mora,
    cu.estado,
    cu.pago_id,
    CASE
        WHEN cu.fecha_pago IS NOT NULL THEN 'pagada'
        WHEN cu.fecha_vencimiento IS NULL THEN 'sin_fv'
        WHEN cu.fecha_vencimiento >= current_date THEN 'al_corriente_o_futura'
        ELSE 'vencida_sin_pago'
    END AS bucket_vencimiento_hoy,
    CASE
        WHEN cu.fecha_pago IS NOT NULL OR cu.fecha_vencimiento IS NULL THEN NULL
        ELSE (current_date - cu.fecha_vencimiento)::int
    END AS dias_desde_vencimiento_hasta_hoy
FROM tmp_chk_cu cu
ORDER BY cu.prestamo_id, cu.numero_cuota;

-- ---------------------------------------------------------------------------
-- 6) Pagos
-- ---------------------------------------------------------------------------
SELECT
    '6_pagos' AS seccion,
    pg.id AS pago_id,
    pg.prestamo_id,
    pg.cedula,
    pg.fecha_pago,
    pg.monto_pagado,
    pg.referencia_pago,
    pg.numero_documento,
    pg.conciliado,
    pg.estado AS estado_pago,
    pg.moneda_registro
FROM pagos pg
CROSS JOIN tmp_chk_cedula p
WHERE upper(replace(replace(trim(coalesce(pg.cedula, '')), '-', ''), ' ', '')) = p.cedula_norm
   OR pg.prestamo_id IN (SELECT id FROM tmp_chk_pr)
ORDER BY pg.fecha_pago DESC NULLS LAST, pg.id DESC;

-- ---------------------------------------------------------------------------
-- 7) cuota_pagos (aplicaciones a cuotas del cliente)
-- ---------------------------------------------------------------------------
SELECT
    '7_cuota_pagos' AS seccion,
    cp.id AS cuota_pago_id,
    cp.cuota_id,
    cp.pago_id,
    cp.monto_aplicado,
    cp.fecha_aplicacion,
    cp.es_pago_completo,
    cu.prestamo_id,
    cu.numero_cuota
FROM cuota_pagos cp
JOIN tmp_chk_cu cu ON cu.id = cp.cuota_id
ORDER BY cp.fecha_aplicacion DESC NULLS LAST, cp.id DESC;

-- ---------------------------------------------------------------------------
-- 8) Envíos notificación
-- ---------------------------------------------------------------------------
SELECT
    '8_envios_notificacion' AS seccion,
    e.id AS envio_id,
    e.fecha_envio,
    e.tipo_tab,
    e.asunto,
    e.email,
    e.nombre,
    e.cedula,
    e.exito,
    left(coalesce(e.error_mensaje, ''), 200) AS error_mensaje_corto,
    e.prestamo_id,
    e.correlativo,
    (e.mensaje_html IS NOT NULL AND length(trim(e.mensaje_html)) > 0) AS tiene_mensaje_html,
    (e.mensaje_texto IS NOT NULL AND length(trim(e.mensaje_texto)) > 0) AS tiene_mensaje_texto,
    (e.comprobante_pdf IS NOT NULL) AS tiene_comprobante_pdf
FROM envios_notificacion e
JOIN tmp_chk_cedula p
  ON upper(replace(replace(trim(coalesce(e.cedula, '')), '-', ''), ' ', '')) = p.cedula_norm
ORDER BY e.fecha_envio DESC NULLS LAST, e.id DESC;

-- ---------------------------------------------------------------------------
-- 9) Adjuntos de envíos
-- ---------------------------------------------------------------------------
SELECT
    '9_envios_adjuntos' AS seccion,
    e.id AS envio_id,
    e.fecha_envio,
    e.tipo_tab,
    count(a.id)::int AS num_adjuntos,
    coalesce(string_agg(a.nombre_archivo, ', ' ORDER BY a.orden), '') AS nombres_adjuntos
FROM envios_notificacion e
JOIN tmp_chk_cedula p
  ON upper(replace(replace(trim(coalesce(e.cedula, '')), '-', ''), ' ', '')) = p.cedula_norm
LEFT JOIN envios_notificacion_adjuntos a ON a.envio_notificacion_id = e.id
GROUP BY e.id, e.fecha_envio, e.tipo_tab
ORDER BY e.fecha_envio DESC;

-- ---------------------------------------------------------------------------
-- 10) Alerta: LIQUIDADO pero cuotas sin fecha_pago
-- ---------------------------------------------------------------------------
SELECT
    '10_alertas_coherencia' AS seccion,
    p.id AS prestamo_id,
    p.estado AS estado_prestamo,
    count(*) FILTER (WHERE c.fecha_pago IS NULL)::int AS cuotas_sin_fecha_pago
FROM tmp_chk_pr p
LEFT JOIN cuotas c ON c.prestamo_id = p.id
GROUP BY p.id, p.estado
HAVING p.estado = 'LIQUIDADO' AND count(*) FILTER (WHERE c.fecha_pago IS NULL) > 0
ORDER BY p.id;
