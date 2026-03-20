-- Crear tabla de auditoría para conciliación manual
-- Registra cada asignación de pago a cuota
CREATE TABLE IF NOT EXISTS auditoria_conciliacion_manual (
  id SERIAL PRIMARY KEY,
  pago_id INTEGER NOT NULL REFERENCES pagos(id) ON DELETE CASCADE,
  cuota_id INTEGER NOT NULL REFERENCES cuotas(id) ON DELETE CASCADE,
  usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
  monto_asignado NUMERIC(14, 2) NOT NULL,
  tipo_asignacion VARCHAR(20) DEFAULT 'MANUAL',  -- MANUAL o AUTOMATICA
  motivo TEXT,
  resultado VARCHAR(20) DEFAULT 'EXITOSA',  -- EXITOSA, FALLIDA
  fecha_asignacion TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  creado_en TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  actualizado_en TIMESTAMP WITH TIME ZONE,
  INDEX idx_pago_id (pago_id),
  INDEX idx_cuota_id (cuota_id),
  INDEX idx_usuario_id (usuario_id),
  INDEX idx_tipo_asignacion (tipo_asignacion),
  INDEX idx_fecha_asignacion (fecha_asignacion)
);

-- Vista: Resumen de auditoría de conciliación
CREATE OR REPLACE VIEW v_auditoria_conciliacion AS
SELECT 
  DATE(acm.fecha_asignacion) as fecha,
  acm.tipo_asignacion,
  COUNT(*) as cantidad_asignaciones,
  SUM(acm.monto_asignado) as monto_total,
  COUNT(*) FILTER (WHERE acm.resultado = 'EXITOSA') as exitosas,
  COUNT(*) FILTER (WHERE acm.resultado = 'FALLIDA') as fallidas
FROM auditoria_conciliacion_manual acm
GROUP BY DATE(acm.fecha_asignacion), acm.tipo_asignacion
ORDER BY fecha DESC;

-- Vista: Detalles de pagos sin asignar
CREATE OR REPLACE VIEW v_pagos_sin_asignar_detalle AS
SELECT 
  p.id as pago_id,
  p.cedula,
  p.fecha_pago,
  p.monto_pagado,
  p.referencia_pago,
  p.estado,
  EXTRACT(DAY FROM NOW() - p.fecha_pago::TIMESTAMP) as dias_sin_asignar,
  CASE 
    WHEN EXTRACT(DAY FROM NOW() - p.fecha_pago::TIMESTAMP) > 60 THEN 'MUY_ANTIGUO'
    WHEN EXTRACT(DAY FROM NOW() - p.fecha_pago::TIMESTAMP) > 30 THEN 'ANTIGUO'
    WHEN EXTRACT(DAY FROM NOW() - p.fecha_pago::TIMESTAMP) > 7 THEN 'RECIENTE'
    ELSE 'NUEVO'
  END as categoria_antigüedad
FROM pagos p
WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)
AND p.estado != 'CANCELADO'
ORDER BY p.fecha_pago DESC;

-- Vista: Validación de sobre-aplicación
CREATE OR REPLACE VIEW v_cuotas_sobre_aplicadas AS
SELECT 
  c.id as cuota_id,
  c.prestamo_id,
  c.numero_cuota,
  c.monto,
  COALESCE(SUM(cp.monto_aplicado), 0) as total_aplicado,
  COALESCE(SUM(cp.monto_aplicado), 0) - c.monto as exceso,
  c.estado,
  p.cedula
FROM cuotas c
LEFT JOIN cuota_pagos cp ON c.id = cp.cuota_id
LEFT JOIN prestamos p ON c.prestamo_id = p.id
GROUP BY c.id, c.prestamo_id, c.numero_cuota, c.monto, c.estado, p.cedula
HAVING COALESCE(SUM(cp.monto_aplicado), 0) > c.monto + 0.01
ORDER BY exceso DESC;

-- Vista: Estadísticas de estado de cuotas
CREATE OR REPLACE VIEW v_estadisticas_estados_cuota AS
SELECT 
  c.estado,
  COUNT(*) as cantidad,
  SUM(c.monto) as monto_total,
  AVG(c.monto) as monto_promedio,
  MIN(c.monto) as monto_minimo,
  MAX(c.monto) as monto_maximo,
  COUNT(*) FILTER (WHERE c.dias_mora > 0) as en_mora
FROM cuotas c
GROUP BY c.estado
ORDER BY cantidad DESC;
