-- ============================================
-- GENERAR CUOTAS PARA PRÉSTAMO #9
-- ============================================
-- Este script inserta las 12 cuotas manualmente
-- Basado en los datos del préstamo

-- PRIMERO: Obtener datos del préstamo
SELECT 
    id,
    total_financiamiento,
    numero_cuotas,
    fecha_base_calculo,
    tasa_interes
FROM 
    prestamos 
WHERE 
    id = 9;

-- SEGUNDO: Calcular cuota
-- La cuota debe ser: total_financiamiento / 12 = 38.85 (aproximado)

-- TERCERO: Insertar las 12 cuotas
-- ADAPTAR LOS VALORES SEGÚN TU PRÉSTAMO
-- Fecha base: 2025-11-28
-- Cuota: 38.85 (verificar con tu préstamo)

INSERT INTO cuotas (prestamo_id, numero_cuota, fecha_vencimiento, monto_cuota, monto_capital, monto_interes, saldo_capital_inicial, saldo_capital_final, estado, created_at, updated_at)
VALUES
(9, 1, '2025-11-28', 38.85, 38.85, 0.00, 466.19, 427.34, 'PENDIENTE', NOW(), NOW()),
(9, 2, '2025-12-28', 38.85, 38.85, 0.00, 427.34, 388.49, 'PENDIENTE', NOW(), NOW()),
(9, 3, '2026-01-28', 38.85, 38.85, 0.00, 388.49, 349.64, 'PENDIENTE', NOW(), NOW()),
(9, 4, '2026-02-28', 38.85, 38.85, 0.00, 349.64, 310.79, 'PENDIENTE', NOW(), NOW()),
(9, 5, '2026-03-28', 38.85, 38.85, 0.00, 310.79, 271.94, 'PENDIENTE', NOW(), NOW()),
(9, 6, '2026-04-28', 38.85, 38.85, 0.00, 271.94, 233.09, 'PENDIENTE', NOW(), NOW()),
(9, 7, '2026-05-28', 38.85, 38.85, 0.00, 233.09, 194.24, 'PENDIENTE', NOW(), NOW()),
(9, 8, '2026-06-28', 38.85, 38.85, 0.00, 194.24, 155.39, 'PENDIENTE', NOW(), NOW()),
(9, 9, '2026-07-28', 38.85, 38.85, 0.00, 155.39, 116.54, 'PENDIENTE', NOW(), NOW()),
(9, 10, '2026-08-28', 38.85, 38.85, 0.00, 116.54, 77.69, 'PENDIENTE', NOW(), NOW()),
(9, 11, '2026-09-28', 38.85, 38.85, 0.00, 77.69, 38.84, 'PENDIENTE', NOW(), NOW()),
(9, 12, '2026-10-28', 38.84, 38.84, 0.00, 38.84, 0.00, 'PENDIENTE', NOW(), NOW());

-- NOTA: 
-- - Ajusta monto_cuota según tu préstamo (total_financiamiento / 12)
-- - Ajusta las fechas según la fecha_base_calculo del préstamo
-- - Ajusta los saldos capital según el monto total

-- Verificar que se insertaron:
SELECT COUNT(*) as total_cuotas FROM cuotas WHERE prestamo_id = 9;

