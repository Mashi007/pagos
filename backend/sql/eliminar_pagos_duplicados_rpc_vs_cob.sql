-- =============================================================================
-- Eliminar pago duplicado: referencia sola (RPC-…) cuando ya existe COB-RPC-…
-- =============================================================================
-- Conserva: numero_documento = 'COB-' || referencia_interna (flujo Aprobar Cobros).
-- Borra:    numero_documento = referencia_interna (mismo texto sin prefijo COB-).
-- Caso típico: borra pago_id 57844, conserva 57519 (mismo reporte BS).
--
-- Efecto: elimina filas en cuota_pagos de ese pago (FK ON DELETE CASCADE).
-- Después: re-articular prestamo_id afectado (ej. 3200 en ese ejemplo).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- PASO 1 — Vista previa (ejecutar solo esto primero)
-- -----------------------------------------------------------------------------
SELECT
    p.id AS pago_id_a_borrar,
    p.prestamo_id,
    p.numero_documento,
    p.monto_pagado,
    p.estado,
    pr.referencia_interna,
    pr.id AS reportado_id
FROM pagos p
JOIN pagos_reportados pr
  ON TRIM(BOTH FROM p.numero_documento) = TRIM(BOTH FROM pr.referencia_interna)
 AND TRIM(BOTH FROM p.numero_documento) NOT LIKE 'COB-%'
WHERE UPPER(TRIM(pr.moneda)) = 'BS'
  AND pr.estado IN ('aprobado', 'importado')
  AND EXISTS (
        SELECT 1
        FROM pagos pcob
        WHERE TRIM(BOTH FROM pcob.numero_documento) = TRIM(BOTH FROM ('COB-' || pr.referencia_interna))
      );

-- -----------------------------------------------------------------------------
-- PASO 2 — Borrado en transacción (tras validar el PASO 1)
-- Ejecutar el bloque completo; si RETURNING es correcto, COMMIT. Si no, ROLLBACK.
-- -----------------------------------------------------------------------------
BEGIN;

DELETE FROM pagos p
USING pagos_reportados pr
WHERE TRIM(BOTH FROM p.numero_documento) = TRIM(BOTH FROM pr.referencia_interna)
  AND TRIM(BOTH FROM p.numero_documento) NOT LIKE 'COB-%'
  AND UPPER(TRIM(pr.moneda)) = 'BS'
  AND pr.estado IN ('aprobado', 'importado')
  AND EXISTS (
        SELECT 1
        FROM pagos pcob
        WHERE TRIM(BOTH FROM pcob.numero_documento) = TRIM(BOTH FROM ('COB-' || pr.referencia_interna))
      )
RETURNING p.id AS pago_id_borrado, p.prestamo_id, p.numero_documento;

-- Si la fila devuelta es la esperada (ej. id 57844):
-- COMMIT;
-- Si algo salió mal:
-- ROLLBACK;
