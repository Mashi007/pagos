-- Estandariza modelo de vehículo en préstamos APROBADO y LIQUIDADO respecto al catálogo modelos_vehiculos.
-- 1) Si hay modelo_vehiculo_id válido: texto del préstamo = modelo canónico del catálogo.
-- 2) Si id es NULL pero el texto (trim, sin distinguir mayúsculas) coincide con una fila del catálogo:
--    asigna ese id y el nombre canónico.
-- No renombra por "parecido" (evita errores); solo coincidencia exacta tras lower(trim).
-- PostgreSQL / DBeaver

-- --- Previa: cuántos tocaría (ejecutar aparte) ---
-- SELECT p.id, p.estado, p.modelo_vehiculo, p.modelo_vehiculo_id, m.modelo AS catalogo
-- FROM prestamos p
-- LEFT JOIN modelos_vehiculos m ON m.id = p.modelo_vehiculo_id
-- WHERE p.estado IN ('APROBADO', 'LIQUIDADO')
--   AND (
--     (p.modelo_vehiculo_id IS NOT NULL AND (p.modelo_vehiculo IS DISTINCT FROM m.modelo OR m.id IS NULL))
--     OR (p.modelo_vehiculo_id IS NULL AND trim(p.modelo_vehiculo) <> '' AND EXISTS (
--       SELECT 1 FROM modelos_vehiculos mv
--       WHERE lower(trim(mv.modelo)) = lower(trim(p.modelo_vehiculo))
--     ))
--   );

BEGIN;

-- A) Texto alineado al catálogo cuando ya hay id válido
UPDATE prestamos p
SET modelo_vehiculo = m.modelo
FROM modelos_vehiculos m
WHERE p.estado IN ('APROBADO', 'LIQUIDADO')
  AND p.modelo_vehiculo_id = m.id
  AND p.modelo_vehiculo IS DISTINCT FROM m.modelo;

-- B) Id inválido (apunta a modelo borrado): quitar id para poder enlazar por texto en C)
UPDATE prestamos p
SET modelo_vehiculo_id = NULL
WHERE p.estado IN ('APROBADO', 'LIQUIDADO')
  AND p.modelo_vehiculo_id IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM modelos_vehiculos m WHERE m.id = p.modelo_vehiculo_id
  );

-- C) Sin id (o recién anulado) pero texto coincide exactamente con catálogo (lower+trim): id + nombre canónico
UPDATE prestamos p
SET
  modelo_vehiculo_id = mv.id,
  modelo_vehiculo = mv.modelo
FROM (
  SELECT DISTINCT ON (lower(trim(modelo)))
    id,
    modelo
  FROM modelos_vehiculos
  ORDER BY lower(trim(modelo)), id
) mv
WHERE p.estado IN ('APROBADO', 'LIQUIDADO')
  AND p.modelo_vehiculo_id IS NULL
  AND p.modelo_vehiculo IS NOT NULL
  AND trim(p.modelo_vehiculo) <> ''
  AND lower(trim(p.modelo_vehiculo)) = lower(trim(mv.modelo));

COMMIT;

-- --- Post: préstamos APROBADO/LIQUIDADO con texto que no existe en catálogo (revisión manual) ---
-- SELECT p.id, p.estado, p.modelo_vehiculo, p.modelo_vehiculo_id
-- FROM prestamos p
-- WHERE p.estado IN ('APROBADO', 'LIQUIDADO')
--   AND trim(COALESCE(p.modelo_vehiculo, '')) <> ''
--   AND NOT EXISTS (
--     SELECT 1 FROM modelos_vehiculos m
--     WHERE lower(trim(m.modelo)) = lower(trim(p.modelo_vehiculo))
--   );
