-- =============================================================================
-- Alinear cuotas.cliente_id con el titular del préstamo (prestamos.cliente_id)
-- =============================================================================
-- Contexto: cuotas.cliente_id es denormalizado. Si diverge del titular, listados
-- y notificaciones pueden mostrar contacto de una persona y montos de otro crédito.
-- El backend ya corrige en envío (alinear_items_contacto_titular_prestamo) y
-- prejudicial usa prestamos.cliente_id; este SQL sanea la BD para el resto de vistas.
--
-- Motor: PostgreSQL (IS DISTINCT FROM, UPDATE ... FROM).
-- Para MySQL 8+, ver bloque comentado al final.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1) Diagnóstico: filas desalineadas o cliente_id nulo en cuota
-- -----------------------------------------------------------------------------
SELECT
    c.id AS cuota_id,
    c.prestamo_id,
    c.cliente_id AS cliente_id_cuota,
    p.cliente_id AS cliente_id_titular_prestamo,
    p.estado AS prestamo_estado
FROM cuotas c
INNER JOIN prestamos p ON p.id = c.prestamo_id
WHERE c.cliente_id IS DISTINCT FROM p.cliente_id
ORDER BY c.prestamo_id, c.id;

-- Conteo rápido
-- SELECT COUNT(*) FROM cuotas c
-- INNER JOIN prestamos p ON p.id = c.prestamo_id
-- WHERE c.cliente_id IS DISTINCT FROM p.cliente_id;


-- -----------------------------------------------------------------------------
-- 2) Corrección (ejecutar tras revisar el SELECT). Usar transacción en producción.
-- -----------------------------------------------------------------------------
BEGIN;

UPDATE cuotas c
SET cliente_id = p.cliente_id
FROM prestamos p
WHERE c.prestamo_id = p.id
  AND c.cliente_id IS DISTINCT FROM p.cliente_id;

-- Opcional: tocar actualizado_en si existe y queréis trazabilidad en filas tocadas
-- UPDATE cuotas c
-- SET
--   cliente_id = p.cliente_id,
--   actualizado_en = NOW()
-- FROM prestamos p
-- WHERE c.prestamo_id = p.id
--   AND c.cliente_id IS DISTINCT FROM p.cliente_id;

COMMIT;


-- =============================================================================
-- MySQL 8+ (equivalente; no ejecutar si ya corriste el bloque PostgreSQL)
-- =============================================================================
-- START TRANSACTION;
--
-- UPDATE cuotas c
-- INNER JOIN prestamos p ON p.id = c.prestamo_id
-- SET c.cliente_id = p.cliente_id
-- WHERE c.cliente_id IS NULL OR c.cliente_id <> p.cliente_id;
--
-- COMMIT;
