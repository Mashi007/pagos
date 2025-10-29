-- ============================================
-- VERIFICACIÓN FINAL: Tabla de Amortización
-- ============================================

-- Ver cuántas cuotas tiene el préstamo #9
SELECT 
    COUNT(*) as total_cuotas,
    MIN(numero_cuota) as primera_cuota,
    MAX(numero_cuota) as ultima_cuota,
    SUM(monto_cuota) as total_pagado
FROM 
    cuotas 
WHERE 
    prestamo_id = 9;

-- Ver las primeras 3 y últimas 3 cuotas
SELECT 
    numero_cuota,
    fecha_vencimiento,
    monto_cuota,
    monto_capital,
    monto_interes,
    estado
FROM 
    cuotas 
WHERE 
    prestamo_id = 9
ORDER BY 
    numero_cuota;

-- Debe mostrar:
-- ✅ total_cuotas = 12
-- ✅ primera_cuota = 1
-- ✅ ultima_cuota = 12
-- ✅ monto_cuota = 38.85 (aproximado) para cada una

