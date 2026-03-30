-- ============================================================================
-- FASE 2 PARTE 6: Índices Adicionales
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_pagos_estado_fecha 
ON pagos (estado, fecha_pago DESC) 
WHERE estado = 'PAGADO';

CREATE INDEX IF NOT EXISTS idx_cuotas_vencidas 
ON cuotas (prestamo_id, fecha_vencimiento) 
WHERE estado != 'CANCELADA';

CREATE INDEX IF NOT EXISTS idx_cliente_cedula_estado 
ON clientes (cedula) 
WHERE estado = 'ACTIVO';

-- Verificar
SELECT COUNT(*) as total_indices FROM pg_indexes
WHERE indexname LIKE 'idx_%' AND tablename IN ('pagos', 'cuotas', 'clientes');
