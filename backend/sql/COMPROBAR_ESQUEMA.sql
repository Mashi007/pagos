-- =============================================================================
-- SQL PARA COMPROBAR ESQUEMA (Render / PostgreSQL)
-- Ejecutar para verificar tablas y columnas después de las migraciones.
-- =============================================================================

-- 1) Columnas de pagos_whatsapp (debe incluir link_imagen)
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'pagos_whatsapp'
ORDER BY ordinal_position;

-- 2) Columnas de pagos_informes (incluye is_nullable; banco_entidad_financiera debe ser YES)
SELECT column_name, data_type, character_maximum_length, is_nullable
FROM information_schema.columns
WHERE table_name = 'pagos_informes'
ORDER BY ordinal_position;

-- 3) Columnas de conversacion_cobranza (debe incluir pagos_informe_id_pendiente)
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'conversacion_cobranza'
ORDER BY ordinal_position;

-- 4) Resumen: solo nombres de columnas clave (rápido)
SELECT 'pagos_whatsapp' AS tabla, string_agg(column_name, ', ' ORDER BY ordinal_position) AS columnas
FROM information_schema.columns WHERE table_name = 'pagos_whatsapp'
UNION ALL
SELECT 'pagos_informes', string_agg(column_name, ', ' ORDER BY ordinal_position)
FROM information_schema.columns WHERE table_name = 'pagos_informes'
UNION ALL
SELECT 'conversacion_cobranza', string_agg(column_name, ', ' ORDER BY ordinal_position)
FROM information_schema.columns WHERE table_name = 'conversacion_cobranza';

-- 5) Confirmar que banco_entidad_financiera acepta NULL (evita NotNullViolation)
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'pagos_informes'
  AND column_name IN ('banco_entidad_financiera', 'nombre_banco', 'numero_deposito', 'link_imagen', 'cantidad')
ORDER BY column_name;
