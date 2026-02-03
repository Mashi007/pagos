-- La app usa nombre_banco; banco_entidad_financiera (esquema antiguo) no se rellena en INSERT.
-- Soluciona: null value in column "banco_entidad_financiera" violates not-null constraint
ALTER TABLE pagos_informes ALTER COLUMN banco_entidad_financiera DROP NOT NULL;
