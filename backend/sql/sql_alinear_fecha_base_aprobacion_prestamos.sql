-- Mantenimiento: alinear fecha_base_calculo con la parte fecha de fecha_aprobacion (canonica en formularios).
-- Si las cuotas se generaron con la base antigua, cambiar solo esta columna NO mueve vencimientos:
-- hace falta recalcular amortizacion en la app (o script) donde corresponda.
-- Antes, ejecutar prestamos_diagnostico_casos_fecha_aprob_base_req.sql para ver volumenes por caso.
-- Ejecutar en DBeaver/psql tras revisar en entorno de pruebas.

BEGIN;

UPDATE prestamos
SET fecha_base_calculo = CAST(fecha_aprobacion AS date)
WHERE fecha_aprobacion IS NOT NULL
  AND (
    fecha_base_calculo IS NULL
    OR fecha_base_calculo IS DISTINCT FROM CAST(fecha_aprobacion AS date)
  );

-- Legacy: solo existe base de calculo
UPDATE prestamos
SET fecha_aprobacion = CAST(fecha_base_calculo AS timestamp)
WHERE fecha_aprobacion IS NULL
  AND fecha_base_calculo IS NOT NULL;

COMMIT;
