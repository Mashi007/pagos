-- =============================================================================
-- Verificación: "Guardar y aprobar" almacena en BD
-- Ejecutar en DBeaver contra la BD del proyecto (PostgreSQL).
-- Confirma que las tablas prestamos, cuotas y auditoria tienen las columnas
-- que usa el backend y que, tras aprobar un préstamo, los datos quedan
-- persistidos e integrados.
--
-- Para verificar otro préstamo: busca y reemplaza 20842 por el id deseado
-- en las secciones 5 y 6.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1) Existencia de tablas
-- -----------------------------------------------------------------------------
SELECT '1. Tablas requeridas' AS seccion;
SELECT table_name AS tabla,
       CASE WHEN table_schema = 'public' THEN 'OK' ELSE 'Revisar schema' END AS resultado
  FROM information_schema.tables
 WHERE table_schema = 'public'
   AND table_name IN ('prestamos', 'cuotas', 'auditoria', 'usuarios', 'clientes')
 ORDER BY table_name;

-- -----------------------------------------------------------------------------
-- 2) Columnas en PRESTAMOS (actualizadas por aprobar-manual)
-- El endpoint escribe: estado, fecha_aprobacion, fecha_base_calculo,
-- usuario_aprobador, total_financiamiento, numero_cuotas, modalidad_pago,
-- cuota_periodo, tasa_interes, observaciones.
-- -----------------------------------------------------------------------------
SELECT '2. Columnas en prestamos (aprobación manual)' AS seccion;
SELECT column_name, data_type, is_nullable
  FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'prestamos'
   AND column_name IN (
     'id', 'cliente_id', 'estado', 'fecha_aprobacion', 'fecha_base_calculo',
     'usuario_aprobador', 'total_financiamiento', 'numero_cuotas', 'modalidad_pago',
     'cuota_periodo', 'tasa_interes', 'observaciones', 'fecha_actualizacion'
   )
 ORDER BY ordinal_position;

-- Comprobar que existen las 13 columnas mínimas
SELECT '2b. Conteo columnas prestamos (mínimo 13)' AS check_item,
       count(*) AS encontradas,
       13 AS esperadas,
       CASE WHEN count(*) >= 13 THEN 'OK' ELSE 'FALTAN COLUMNAS' END AS resultado
  FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'prestamos'
   AND column_name IN (
     'id', 'cliente_id', 'estado', 'fecha_aprobacion', 'fecha_base_calculo',
     'usuario_aprobador', 'total_financiamiento', 'numero_cuotas', 'modalidad_pago',
     'cuota_periodo', 'tasa_interes', 'observaciones', 'fecha_actualizacion'
   );

-- -----------------------------------------------------------------------------
-- 3) Columnas en CUOTAS (generadas al aprobar)
-- Backend escribe: prestamo_id, cliente_id, numero_cuota, fecha_vencimiento,
-- monto_cuota, saldo_capital_inicial, saldo_capital_final, estado.
-- -----------------------------------------------------------------------------
SELECT '3. Columnas en cuotas (tabla amortización)' AS seccion;
SELECT column_name, data_type, is_nullable
  FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'cuotas'
   AND column_name IN (
     'id', 'prestamo_id', 'cliente_id', 'numero_cuota', 'fecha_vencimiento',
     'monto_cuota', 'saldo_capital_inicial', 'saldo_capital_final', 'estado'
   )
 ORDER BY ordinal_position;

SELECT '3b. Conteo columnas cuotas (mínimo 9)' AS check_item,
       count(*) AS encontradas,
       9 AS esperadas,
       CASE WHEN count(*) >= 9 THEN 'OK' ELSE 'FALTAN COLUMNAS' END AS resultado
  FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'cuotas'
   AND column_name IN (
     'id', 'prestamo_id', 'cliente_id', 'numero_cuota', 'fecha_vencimiento',
     'monto_cuota', 'saldo_capital_inicial', 'saldo_capital_final', 'estado'
   );

-- -----------------------------------------------------------------------------
-- 4) Columnas en AUDITORIA (registro de aprobación)
-- Backend escribe: usuario_id, accion='APROBACION_MANUAL', entidad='prestamos',
-- entidad_id=prestamo_id, detalles, exito, fecha (server_default).
-- -----------------------------------------------------------------------------
SELECT '4. Columnas en auditoria' AS seccion;
SELECT column_name, data_type, is_nullable
  FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'auditoria'
   AND column_name IN ('id', 'usuario_id', 'accion', 'entidad', 'entidad_id', 'detalles', 'exito', 'fecha')
 ORDER BY ordinal_position;

SELECT '4b. Conteo columnas auditoria (mínimo 8)' AS check_item,
       count(*) AS encontradas,
       8 AS esperadas,
       CASE WHEN count(*) >= 8 THEN 'OK' ELSE 'FALTAN COLUMNAS' END AS resultado
  FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'auditoria'
   AND column_name IN ('id', 'usuario_id', 'accion', 'entidad', 'entidad_id', 'detalles', 'exito', 'fecha');

-- -----------------------------------------------------------------------------
-- 5) Verificar un préstamo concreto tras "Guardar y aprobar"
-- Reemplaza 20842 por el id del préstamo que aprobaste en las consultas siguientes.
-- -----------------------------------------------------------------------------
SELECT '5. Préstamo tras aprobación (prestamos)' AS seccion;
SELECT id, cliente_id, estado, fecha_aprobacion, fecha_base_calculo, usuario_aprobador,
       total_financiamiento, numero_cuotas, modalidad_pago, cuota_periodo, tasa_interes,
       left(observaciones, 80) AS observaciones_corta
  FROM prestamos
 WHERE id = 20842;

-- Si estado = 'APROBADO', fecha_aprobacion y usuario_aprobador no nulos → guardado OK.

SELECT '5b. Cuotas generadas para el préstamo' AS seccion;
SELECT count(*) AS total_cuotas,
       min(numero_cuota) AS min_cuota,
       max(numero_cuota) AS max_cuota,
       sum(monto_cuota) AS suma_montos
  FROM cuotas
 WHERE prestamo_id = 20842;

SELECT '5c. Detalle primeras 5 cuotas' AS seccion;
SELECT id, prestamo_id, numero_cuota, fecha_vencimiento, monto_cuota,
       saldo_capital_inicial, saldo_capital_final, estado
  FROM cuotas
 WHERE prestamo_id = 20842
 ORDER BY numero_cuota
 LIMIT 5;

SELECT '5d. Registro de auditoría APROBACION_MANUAL' AS seccion;
SELECT id, usuario_id, accion, entidad, entidad_id, left(detalles, 120) AS detalles_corto, exito, fecha
  FROM auditoria
 WHERE entidad = 'prestamos' AND entidad_id = 20842 AND accion = 'APROBACION_MANUAL'
 ORDER BY fecha DESC
 LIMIT 3;

-- -----------------------------------------------------------------------------
-- 6) Integración: prestamo → cuotas → auditoria
-- -----------------------------------------------------------------------------
SELECT '6. Integración guardar-y-aprobar' AS seccion;
SELECT p.id AS prestamo_id,
       p.estado,
       p.fecha_aprobacion IS NOT NULL AS tiene_fecha_aprobacion,
       p.usuario_aprobador IS NOT NULL AS tiene_usuario_aprobador,
       (SELECT count(*) FROM cuotas c WHERE c.prestamo_id = p.id) AS num_cuotas,
       (SELECT count(*) FROM auditoria a WHERE a.entidad = 'prestamos' AND a.entidad_id = p.id AND a.accion = 'APROBACION_MANUAL') AS registros_auditoria
  FROM prestamos p
 WHERE p.id = 20842;

-- Resultado esperado para un préstamo recién aprobado:
-- estado = APROBADO, tiene_fecha_aprobacion = true, tiene_usuario_aprobador = true,
-- num_cuotas = numero_cuotas del préstamo (ej. 12), registros_auditoria >= 1.

-- -----------------------------------------------------------------------------
-- 7) Últimas aprobaciones manuales (lista reciente)
-- -----------------------------------------------------------------------------
SELECT '7. Últimas 10 aprobaciones manuales' AS seccion;
SELECT a.id, a.entidad_id AS prestamo_id, a.usuario_id, a.detalles, a.exito, a.fecha
  FROM auditoria a
 WHERE a.entidad = 'prestamos' AND a.accion = 'APROBACION_MANUAL'
 ORDER BY a.fecha DESC
 LIMIT 10;

-- -----------------------------------------------------------------------------
-- 8) Resumen: préstamos APROBADOS con cuotas y auditoría
-- -----------------------------------------------------------------------------
SELECT '8. Resumen integridad aprobados' AS seccion;
SELECT count(*) AS total_aprobados,
       count(*) FILTER (WHERE (SELECT count(*) FROM cuotas c WHERE c.prestamo_id = p.id) > 0) AS con_cuotas,
       count(*) FILTER (WHERE (SELECT count(*) FROM auditoria a WHERE a.entidad = 'prestamos' AND a.entidad_id = p.id AND a.accion = 'APROBACION_MANUAL') > 0) AS con_auditoria
  FROM prestamos p
 WHERE p.estado = 'APROBADO';

-- Si total_aprobados = con_cuotas = con_auditoria → integración correcta.
