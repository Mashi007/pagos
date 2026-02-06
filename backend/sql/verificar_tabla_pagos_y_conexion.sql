-- =============================================================================
-- Verificación: tabla PAGOS y conexión con PRÉSTAMOS / CLIENTES
-- Ejecutar en la BD del proyecto (PostgreSQL). Confirma que la tabla existe,
-- tiene las columnas esperadas por el backend y las FKs están bien.
-- NO se procesa el resto hasta que el primer check devuelva: Tabla pagos existe | OK
-- =============================================================================

\set ON_ERROR_STOP on

-- 1) Confirmar que la tabla pagos existe (si no existe, el script se detiene después de este SELECT)
SELECT 'Tabla pagos existe' AS check_item,
       CASE WHEN EXISTS (
         SELECT 1 FROM information_schema.tables
         WHERE table_schema = 'public' AND table_name = 'pagos'
       ) THEN 'OK' ELSE 'FALTA TABLA' END AS resultado;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'pagos'
  ) THEN
    RAISE EXCEPTION 'FIN: La tabla pagos no existe. Crea la tabla y vuelve a ejecutar. No se procesa el resto del script hasta ver: check_item | resultado | Tabla pagos existe | OK';
  END IF;
END $$;

-- 2) Listar columnas de pagos (nombre y tipo)
SELECT 'Columnas de pagos' AS check_item, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'pagos'
ORDER BY ordinal_position;

-- 3) Confirmar foreign key pagos -> prestamos
SELECT 'FK pagos.prestamo_id -> prestamos.id' AS check_item,
       CASE WHEN EXISTS (
         SELECT 1 FROM information_schema.table_constraints tc
         JOIN information_schema.key_column_usage kcu
           ON tc.constraint_name = kcu.constraint_name
           AND tc.table_schema = kcu.table_schema
         WHERE tc.table_schema = 'public'
           AND tc.table_name = 'pagos'
           AND tc.constraint_type = 'FOREIGN KEY'
           AND kcu.column_name = 'prestamo_id'
       ) THEN 'OK' ELSE 'REVISAR FK' END AS resultado;

-- 4) Columnas mínimas requeridas por el backend (app/models/pago.py)
-- Tu tabla puede tener más columnas (numero_cuota, cliente_id, banco, etc.); con estas 18 el API funciona.
SELECT 'Columnas requeridas presentes' AS check_item,
       (SELECT count(*) FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'pagos'
          AND (column_name IN (
            'id', 'prestamo_id', 'cedula', 'cedula_cliente', 'fecha_pago', 'monto_pagado', 'estado',
            'numero_documento', 'institucion_bancaria', 'fecha_registro', 'fecha_conciliacion',
            'conciliado', 'verificado_concordancia', 'usuario_registro', 'notas',
            'documento_nombre', 'documento_tipo', 'documento_ruta', 'referencia_pago'
          ))
       ) AS columnas_encontradas,
       18 AS columnas_esperadas_minimo,
       CASE WHEN (SELECT count(*) FROM information_schema.columns
                  WHERE table_schema = 'public' AND table_name = 'pagos'
                    AND column_name IN (
                      'id', 'prestamo_id', 'cedula', 'cedula_cliente', 'fecha_pago', 'monto_pagado', 'estado',
                      'numero_documento', 'institucion_bancaria', 'fecha_registro', 'fecha_conciliacion',
                      'conciliado', 'verificado_concordancia', 'usuario_registro', 'notas',
                      'documento_nombre', 'documento_tipo', 'documento_ruta', 'referencia_pago'
                    )) >= 18
            THEN 'OK' ELSE 'FALTAN COLUMNAS' END AS resultado;

-- 5) Índices recomendados para listado/filtros (pagos conectado a API)
SELECT 'Índices en pagos' AS check_item, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public' AND tablename = 'pagos'
ORDER BY indexname;

-- 6) Integridad: pagos con prestamo_id que no existe en prestamos (deberían ser 0 o pocos)
SELECT 'Pagos con prestamo_id inexistente' AS check_item,
       count(*) AS cantidad
FROM pagos p
LEFT JOIN prestamos pr ON pr.id = p.prestamo_id
WHERE p.prestamo_id IS NOT NULL AND pr.id IS NULL;

-- 7) Resumen de conexión: total pagos y cuántos enlazan a préstamo/cliente
SELECT
  (SELECT count(*) FROM pagos) AS total_pagos,
  (SELECT count(*) FROM pagos WHERE prestamo_id IS NOT NULL) AS pagos_con_prestamo_id,
  (SELECT count(*) FROM pagos p
   INNER JOIN prestamos pr ON pr.id = p.prestamo_id) AS pagos_enlazados_prestamo,
  (SELECT count(*) FROM pagos p
   INNER JOIN prestamos pr ON pr.id = p.prestamo_id
   INNER JOIN clientes c ON c.id = pr.cliente_id) AS pagos_enlazados_cliente;

-- 8) Muestra de 3 registros (confirmar que datos se leen bien)
-- Backend mapea columna física "cedula" a cedula_cliente en la API. Si tu BD tiene "cedula_cliente", úsala en el SELECT.
SELECT id,
       prestamo_id,
       cedula,
       fecha_pago,
       monto_pagado,
       estado,
       numero_documento,
       verificado_concordancia,
       fecha_registro
FROM pagos
ORDER BY id DESC
LIMIT 3;
