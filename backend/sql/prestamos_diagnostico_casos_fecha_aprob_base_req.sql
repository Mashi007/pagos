-- Diagnostico: casos donde no basta un solo COALESCE entre aprobacion, base y requerimiento.
--
-- Si el resumen muestra una sola fila "F_base_null" sin mas texto, es una VERSION ANTIGUA
-- del CASE: vuelve a ejecutar solo el bloque (1) de abajo. En la version actual:
--   H_base_null_con_aprobacion = base NULL pero hay fecha_aprobacion (ej. cohorte 2025-10-31 + ap 2026).
--   F_base_null_sin_aprobacion = base NULL y sin dia de aprobacion (riesgo si estado APROBADO).
--
-- Leyenda de casos (ejemplo de lectura con cifras parecidas a las tuyas):
--   A_todo_igual                 — Las tres fechas alineadas (objetivo tras normalizar).
--   A_aprob_igual_base_req_distinto — Aprob y base iguales; requerimiento distinto.
--   C_clasico_base_req_antes_aprob — Base = req, aprobacion posterior; cuotas suelen anclarse a base/req.
--   H_base_null_con_aprobacion   — Falta fecha_base_calculo pero si hay aprobacion; conviene UPDATE base = dia(aprob) o generar cuotas.
--   F_base_null_sin_aprobacion   — Sin base ni aprobacion; revisar estado / carga.
--   B_sin_fecha_aprobacion       — Sin fecha_aprobacion (con o sin base).
--   D_anomalo_aprob_antes_base   — Dia aprobacion < base; revisar manual.
--   E_base_distinto_req_y_aprob  — Triple desalineado; revisar manual.
--   Z_otro                       — Patron no cubierto arriba.

-- ---------------------------------------------------------------------------
-- 1) Resumen por tipo de caso
-- ---------------------------------------------------------------------------
WITH p AS (
  SELECT
    id,
    estado,
    fecha_aprobacion,
    fecha_base_calculo,
    fecha_requerimiento,
    CAST(fecha_aprobacion AS date) AS dia_aprobacion
  FROM prestamos
  WHERE estado IN ('APROBADO', 'LIQUIDADO', 'DESEMBOLSADO')
),
c AS (
  SELECT
    *,
    CASE
      WHEN dia_aprobacion IS NULL THEN 'B_sin_fecha_aprobacion'
      WHEN fecha_base_calculo IS NULL AND dia_aprobacion IS NOT NULL
        THEN 'H_base_null_con_aprobacion'
      WHEN fecha_base_calculo IS NULL THEN 'F_base_null_sin_aprobacion'
      WHEN dia_aprobacion = fecha_base_calculo
           AND fecha_base_calculo = fecha_requerimiento THEN 'A_todo_igual'
      WHEN dia_aprobacion = fecha_base_calculo THEN 'A_aprob_igual_base_req_distinto'
      WHEN fecha_base_calculo = fecha_requerimiento
           AND dia_aprobacion > fecha_base_calculo THEN 'C_clasico_base_req_antes_aprob'
      WHEN dia_aprobacion < fecha_base_calculo THEN 'D_anomalo_aprob_antes_base'
      WHEN fecha_base_calculo <> fecha_requerimiento
           AND dia_aprobacion <> fecha_base_calculo THEN 'E_base_distinto_req_y_aprob'
      ELSE 'Z_otro'
    END AS caso
  FROM p
)
SELECT caso, COUNT(*) AS n
FROM c
GROUP BY caso
ORDER BY n DESC;

-- Total filas clasificadas (debe coincidir con prestamos en esos estados)
-- SELECT COUNT(*) FROM prestamos WHERE estado IN ('APROBADO', 'LIQUIDADO', 'DESEMBOLSADO');

-- ---------------------------------------------------------------------------
-- 2) Cohortes por fecha de requerimiento (ej. 2025-10-31)
-- ---------------------------------------------------------------------------
-- Sustituir la fecha si buscas otro dia.
SELECT
  id,
  estado,
  CAST(fecha_aprobacion AS date) AS dia_aprobacion,
  fecha_base_calculo,
  fecha_requerimiento
FROM prestamos
WHERE fecha_requerimiento = DATE '2025-10-31'
ORDER BY id;

-- Solo APROBADO + misma fecha requerimiento (misma cohorte que mostraste)
SELECT COUNT(*) AS n
FROM prestamos
WHERE estado = 'APROBADO'
  AND fecha_requerimiento = DATE '2025-10-31';

-- ---------------------------------------------------------------------------
-- 3) Detalle por caso (descomentar y ajustar `caso`)
-- ---------------------------------------------------------------------------
/*
WITH p AS (
  SELECT
    id,
    estado,
    fecha_aprobacion,
    fecha_base_calculo,
    fecha_requerimiento,
    CAST(fecha_aprobacion AS date) AS dia_aprobacion
  FROM prestamos
  WHERE estado IN ('APROBADO', 'LIQUIDADO', 'DESEMBOLSADO')
),
c AS (
  SELECT
    *,
    CASE
      WHEN dia_aprobacion IS NULL THEN 'B_sin_fecha_aprobacion'
      WHEN fecha_base_calculo IS NULL AND dia_aprobacion IS NOT NULL
        THEN 'H_base_null_con_aprobacion'
      WHEN fecha_base_calculo IS NULL THEN 'F_base_null_sin_aprobacion'
      WHEN dia_aprobacion = fecha_base_calculo
           AND fecha_base_calculo = fecha_requerimiento THEN 'A_todo_igual'
      WHEN dia_aprobacion = fecha_base_calculo THEN 'A_aprob_igual_base_req_distinto'
      WHEN fecha_base_calculo = fecha_requerimiento
           AND dia_aprobacion > fecha_base_calculo THEN 'C_clasico_base_req_antes_aprob'
      WHEN dia_aprobacion < fecha_base_calculo THEN 'D_anomalo_aprob_antes_base'
      WHEN fecha_base_calculo <> fecha_requerimiento
           AND dia_aprobacion <> fecha_base_calculo THEN 'E_base_distinto_req_y_aprob'
      ELSE 'Z_otro'
    END AS caso
  FROM p
)
SELECT *
FROM c
WHERE caso = 'H_base_null_con_aprobacion'
ORDER BY id;
*/
