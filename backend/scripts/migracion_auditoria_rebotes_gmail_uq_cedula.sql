-- Unicidad de cedula en auditoria_rebotes_gmail (una fila por cedula).
-- Ejecutar en la BD tras desplegar la regla de no repetir cedula.
-- Si ya hay duplicados, limpielos antes o el CREATE fallara.

BEGIN;

-- Opcional: ver duplicados actuales
-- SELECT upper(trim(cedula)) AS c, COUNT(*)
-- FROM public.auditoria_rebotes_gmail
-- WHERE cedula IS NOT NULL AND btrim(cedula) <> ''
-- GROUP BY 1 HAVING COUNT(*) > 1;

CREATE UNIQUE INDEX IF NOT EXISTS uq_auditoria_rebotes_gmail_cedula
    ON public.auditoria_rebotes_gmail (upper(trim(cedula)))
    WHERE cedula IS NOT NULL AND btrim(cedula) <> '';

COMMIT;
