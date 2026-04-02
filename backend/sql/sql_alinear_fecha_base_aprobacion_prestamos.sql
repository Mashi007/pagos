-- Alinear fecha_base_calculo con el DIA de fecha_aprobacion (misma regla que en la app:
-- alinear_fecha_aprobacion_y_base_calculo en fechas_prestamo_coherencia.py).
--
-- NO usa fecha_actualizacion: esa columna es solo "ultimo guardado en BD" (onupdate ORM),
-- no define negocio ni amortizacion. Este script solo mira fecha_aprobacion y fecha_base_calculo.
--
-- Si las cuotas se generaron con una base antigua, actualizar solo fecha_base_calculo NO mueve
-- vencimientos: hace falta recalcular amortizacion en la app o endpoint de recalculo de fechas.
-- Antes: ejecutar prestamos_diagnostico_casos_fecha_aprob_base_req.sql para volumenes por caso.
-- Probar en copia de BD / entorno de pruebas antes de produccion.

-- Vista previa (opcional): cuantas filas tocara el UPDATE
-- SELECT COUNT(*) FROM prestamos
-- WHERE fecha_aprobacion IS NOT NULL
--   AND (fecha_base_calculo IS NULL
--        OR fecha_base_calculo IS DISTINCT FROM CAST(fecha_aprobacion AS date));

BEGIN;

UPDATE prestamos
SET fecha_base_calculo = CAST(fecha_aprobacion AS date)
WHERE fecha_aprobacion IS NOT NULL
  AND (
    fecha_base_calculo IS NULL
    OR fecha_base_calculo IS DISTINCT FROM CAST(fecha_aprobacion AS date)
  );

-- NO rellenar fecha_aprobacion desde fecha_base_calculo aqui: en politica vigente la aprobacion
-- es explicita (formularios/API). Si hay NULL en fecha_aprobacion con base poblada, revisar caso
-- a caso o asignar fecha de aprobacion por flujo de negocio, no por SQL automatico desde base.

COMMIT;
