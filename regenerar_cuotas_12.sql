-- ============================================
-- PASO 4: Verificar y regenerar cuotas
-- ============================================

-- Después de ejecutar la corrección, verifica que quedó correcto:
SELECT 
    id,
    nombres,
    numero_cuotas,
    cuota_periodo,
    total_financiamiento
FROM 
    prestamos 
WHERE 
    id = 9;

-- Debe mostrar: numero_cuotas = 12, cuota_periodo = total_financiamiento / 12

-- Para regenerar las 12 cuotas, usa el endpoint de la API:
-- POST /api/v1/prestamos/9/generar-amortizacion
-- 
-- O desde el frontend, abre el préstamo y usa el botón de generar tabla de amortización

-- Verificar que se generaron correctamente:
SELECT 
    COUNT(*) as total_cuotas,
    MIN(numero_cuota) as primera,
    MAX(numero_cuota) as ultima
FROM 
    cuotas 
WHERE 
    prestamo_id = 9;

-- Debe mostrar: total_cuotas = 12

