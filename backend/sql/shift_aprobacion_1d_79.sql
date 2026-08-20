-- +1 día a fecha_aprobacion (solo 79 cédulas, solo APROBADO),
-- alinea fecha_base_calculo, recalcula fecha_vencimiento y cuotas.estado.
-- Misma regla que _recalcular_fechas_vencimiento_cuotas + clasificar_estado_cuota.
-- No inventa fechas: solo +1 día sobre lo que ya está en BD.
--
-- Uso en Render Shell / psql (URL externa):
--   1) Revisar el SELECT de preview.
--   2) Si cuadra, descomentar BEGIN/COMMIT y los UPDATE.
--
-- Hoy de negocio = date en America/Caracas.

BEGIN;

CREATE TEMP TABLE _cedulas_shift_79 (cedula text PRIMARY KEY);
INSERT INTO _cedulas_shift_79 (cedula) VALUES
('V10404030'),('V25220221'),('V18818120'),('V18820705'),('V25268389'),
('V10936731'),('V19004584'),('V25572166'),('V19066608'),('V25795469'),
('V25880430'),('V19314246'),('V26144241'),('V19343724'),('V19467169'),
('V13259428'),('V19653031'),('V19720227'),('V26339024'),('V26596941'),
('V13807082'),('V19785727'),('V26612896'),('V19812798'),('V26632069'),
('V19940650'),('V14097080'),('V14148854'),('V20055566'),('V26836439'),
('V20172177'),('V14604055'),('V26968938'),('V20260355'),('V20266368'),
('V14665523'),('V15101606'),('V27472650'),('V20740955'),('V15882247'),
('V27630526'),('V20824761'),('V16042471'),('V20866599'),('V20870139'),
('V28291751'),('V16436412'),('V28413845'),('V28560001'),('V16542804'),
('V21248685'),('V21337782'),('V16592844'),('V16640577'),('V22286567'),
('V17060829'),('V17262972'),('V17263164'),('V17283689'),('V22822972'),
('V22942555'),('V17512986'),('V17529703'),('V23610150'),('V23633651'),
('V30610111'),('V17875084'),('V17932674'),('V30798806'),('V30836758'),
('V24419435'),('V18116506'),('V32080422'),('V24643517'),('V18376867'),
('V18389920'),('V18476425'),('V18677236'),('V9086999');

-- Dígitos de la lista (E/V/G/J + número cruzan igual).
CREATE TEMP TABLE _digitos_shift_79 AS
SELECT regexp_replace(cedula, '[^0-9]', '', 'g') AS digitos
FROM _cedulas_shift_79;

-- PREVIEW: préstamos APROBADO que se tocarían
SELECT
  p.id AS prestamo_id,
  p.cedula,
  p.estado,
  p.modalidad_pago,
  p.fecha_aprobacion::date AS aprobacion_actual,
  (p.fecha_aprobacion + interval '1 day')::date AS aprobacion_nueva,
  (SELECT count(*) FROM cuotas c WHERE c.prestamo_id = p.id) AS n_cuotas
FROM prestamos p
WHERE upper(trim(p.estado)) = 'APROBADO'
  AND p.fecha_aprobacion IS NOT NULL
  AND regexp_replace(coalesce(p.cedula, ''), '[^0-9]', '', 'g') IN (
    SELECT digitos FROM _digitos_shift_79
  )
ORDER BY p.cedula, p.id;

-- Cédulas de la lista sin préstamo APROBADO con fecha_aprobacion
SELECT t.cedula
FROM _cedulas_shift_79 t
WHERE regexp_replace(t.cedula, '[^0-9]', '', 'g') NOT IN (
  SELECT regexp_replace(coalesce(p.cedula, ''), '[^0-9]', '', 'g')
  FROM prestamos p
  WHERE upper(trim(p.estado)) = 'APROBADO'
    AND p.fecha_aprobacion IS NOT NULL
);

-- === APLICAR (deja el BEGIN de arriba; si el preview está mal: ROLLBACK;) ===

UPDATE prestamos p
SET
  fecha_aprobacion = p.fecha_aprobacion + interval '1 day',
  fecha_base_calculo = (p.fecha_aprobacion + interval '1 day')::date
WHERE upper(trim(p.estado)) = 'APROBADO'
  AND p.fecha_aprobacion IS NOT NULL
  AND regexp_replace(coalesce(p.cedula, ''), '[^0-9]', '', 'g') IN (
    SELECT digitos FROM _digitos_shift_79
  );

-- Vencimientos: misma fórmula que _recalcular_fechas_vencimiento_cuotas
-- MENSUAL: base + numero_cuota meses (día recortado al último del mes)
-- QUINCENAL: base + (15*n - 1) días
-- SEMANAL: base + (7*n - 1) días
UPDATE cuotas c
SET fecha_vencimiento = CASE
  WHEN upper(trim(coalesce(p.modalidad_pago, 'MENSUAL'))) = 'QUINCENAL'
    THEN (p.fecha_base_calculo + ((c.numero_cuota * 15) - 1) * interval '1 day')::date
  WHEN upper(trim(coalesce(p.modalidad_pago, 'MENSUAL'))) = 'SEMANAL'
    THEN (p.fecha_base_calculo + ((c.numero_cuota * 7) - 1) * interval '1 day')::date
  ELSE (p.fecha_base_calculo + (c.numero_cuota::text || ' months')::interval)::date
END
FROM prestamos p
WHERE c.prestamo_id = p.id
  AND upper(trim(p.estado)) = 'APROBADO'
  AND p.fecha_base_calculo IS NOT NULL
  AND regexp_replace(coalesce(p.cedula, ''), '[^0-9]', '', 'g') IN (
    SELECT digitos FROM _digitos_shift_79
  );

-- Estado de cuota = clasificar_estado_cuota (Caracas, tolerancia 0.01).
-- Umbral MORA: copiar SQL_PG_INTERVAL_INICIO_MORA de backend/app/services/cuota_estado.py
-- (hoy: 4 months + 6 days). No cambiar el interval aqui sin cambiar Python.
UPDATE cuotas c
SET estado = CASE
  WHEN coalesce(c.monto_cuota, 0) > 0
       AND coalesce(c.total_pagado, 0) >= (c.monto_cuota - 0.01)
    THEN CASE
      WHEN c.fecha_vencimiento::date > ((CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date)
        THEN 'PAGO_ADELANTADO'
      ELSE 'PAGADO'
    END
  WHEN ((CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date - c.fecha_vencimiento::date) <= 0
    THEN CASE
      WHEN coalesce(c.total_pagado, 0) > 0.001 THEN 'PARCIAL'
      ELSE 'PENDIENTE'
    END
  WHEN ((CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date)
       >= (c.fecha_vencimiento::date + interval '4 months' + interval '6 days')::date
    THEN 'MORA'
  ELSE 'VENCIDO'
END
FROM prestamos p
WHERE c.prestamo_id = p.id
  AND upper(trim(p.estado)) = 'APROBADO'
  AND regexp_replace(coalesce(p.cedula, ''), '[^0-9]', '', 'g') IN (
    SELECT digitos FROM _digitos_shift_79
  );

-- Verificación
SELECT
  p.id,
  p.cedula,
  p.fecha_aprobacion::date AS aprobacion,
  p.fecha_base_calculo,
  c.numero_cuota,
  c.fecha_vencimiento::date AS vencimiento,
  c.estado
FROM prestamos p
JOIN cuotas c ON c.prestamo_id = p.id
WHERE upper(trim(p.estado)) = 'APROBADO'
  AND regexp_replace(coalesce(p.cedula, ''), '[^0-9]', '', 'g') IN (
    SELECT digitos FROM _digitos_shift_79
  )
ORDER BY p.cedula, p.id, c.numero_cuota;

COMMIT;
