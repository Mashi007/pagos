-- =============================================================================
-- Verificar que las columnas están creadas (ejecutar en DBeaver / psql)
-- =============================================================================

-- 1) Listar todas las columnas de pagos_informes (debe incluir G, H, J: nombre_cliente, estado_conciliacion, telefono)
SELECT column_name, data_type, character_maximum_length, is_nullable
FROM information_schema.columns
WHERE table_name = 'pagos_informes'
ORDER BY ordinal_position;

-- 2) Comprobar solo las columnas añadidas para Google Sheets (G, H, J)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'pagos_informes'
  AND column_name IN ('nombre_cliente', 'estado_conciliacion', 'telefono')
ORDER BY column_name;
-- Si devuelve 3 filas, las columnas están creadas.

-- 3) Verificación explícita: qué falta (0 filas = todo OK)
SELECT 'FALTA: ' || col AS resultado
FROM (VALUES ('nombre_cliente'), ('estado_conciliacion'), ('telefono')) AS t(col)
WHERE NOT EXISTS (
  SELECT 1 FROM information_schema.columns c
  WHERE c.table_schema = current_schema()
    AND c.table_name = 'pagos_informes'
    AND c.column_name = t.col
);
-- Si no devuelve filas, ninguna columna falta.
