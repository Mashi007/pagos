-- Permite estado REVISION_CONTABLE en finiquito_casos (boton Revision contable).
-- Ejecutar en produccion si PATCH /finiquito/admin/casos/{id}/estado devuelve 500 al pasar a REVISION_CONTABLE.

ALTER TABLE finiquito_casos DROP CONSTRAINT IF EXISTS ck_finiquito_casos_estado;

ALTER TABLE finiquito_casos
ADD CONSTRAINT ck_finiquito_casos_estado
CHECK (
    estado IN (
        'REVISION',
        'ACEPTADO',
        'REVISION_CONTABLE',
        'RECHAZADO',
        'EN_PROCESO',
        'TERMINADO'
    )
);
