-- Normalizar cedulas existentes a MAYUSCULAS (Postgres). Ejecutar una vez tras desplegar normalizacion en codigo.
-- Evita desalineacion con nuevos pagos/clientes que ya guardan en mayusculas.

UPDATE clientes SET cedula = UPPER(TRIM(cedula)) WHERE cedula IS NOT NULL AND cedula <> UPPER(TRIM(cedula));
UPDATE prestamos SET cedula = UPPER(TRIM(cedula)) WHERE cedula IS NOT NULL AND cedula <> UPPER(TRIM(cedula));
UPDATE pagos SET cedula = UPPER(TRIM(cedula)) WHERE cedula IS NOT NULL AND cedula <> UPPER(TRIM(cedula));
