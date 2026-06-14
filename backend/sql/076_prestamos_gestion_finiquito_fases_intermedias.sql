-- Backfill prestamos.estado_gestion_finiquito para casos en ACEPTADO / REVISION_CONTABLE.
-- Ejecutar tras desplegar codigo que sincroniza esas fases (alembic 076 o manual).

UPDATE prestamos p
SET estado_gestion_finiquito = UPPER(TRIM(c.estado))
FROM finiquito_casos c
WHERE c.prestamo_id = p.id
  AND UPPER(TRIM(c.estado)) IN (
    'REVISION',
    'ACEPTADO',
    'REVISION_CONTABLE',
    'EN_PROCESO',
    'TERMINADO'
  );

UPDATE prestamos
SET estado_gestion_finiquito = 'REVISION'
WHERE UPPER(TRIM(COALESCE(estado_gestion_finiquito, ''))) = 'ANTIGUO';
