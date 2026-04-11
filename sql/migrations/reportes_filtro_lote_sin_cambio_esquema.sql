-- =============================================================================
-- Informes por LOTE (Clientes hoja, Préstamos Drive): NOTAS Y COMPRUEBOS
-- =============================================================================
-- NO se requiere migración de esquema para filtrar por lote.
-- El backend lee la columna LOTE desde el JSON en conciliacion_sheet_rows.cells
-- (clave = texto de cabecera en la hoja, p. ej. "LOTE"), igual que MES u otras.
--
-- Requisito: snapshot actualizado (POST sync Drive / cron) para que existan
-- filas y que conciliacion_sheet_meta.headers incluya la cabecera LOTE.
--
-- Si aún no existen las tablas del snapshot CONCILIACIÓN, ejecute antes:
--   sql/migrations/informes_auxiliares_consolidado.sql
-- =============================================================================

-- Comprobaciones de solo lectura (opcional):

SELECT id,
       row_count,
       col_count,
       synced_at,
       CASE
         WHEN headers::text ILIKE '%lote%' THEN 'headers: parece incluir LOTE'
         ELSE 'headers: revise si la cabecera LOTE está en la hoja y re-sync'
       END AS nota_lote
FROM conciliacion_sheet_meta
WHERE id = 1;

SELECT COUNT(*) AS filas_en_snapshot
FROM conciliacion_sheet_rows;

-- Ejemplo: ver si alguna fila trae clave "LOTE" en cells (ajuste el literal si su hoja usa otro texto exacto):
SELECT COUNT(*) AS filas_con_clave_LOTE
FROM conciliacion_sheet_rows
WHERE cells ? 'LOTE';
