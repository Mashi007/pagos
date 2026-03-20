-- ============================================================================
-- ALERTAS AUTOMATICAS: Pagos sin asignar y problemas de conciliacion
-- ============================================================================

-- 1. TABLA DE AUDITORIA DE ALERTAS
-- ============================================================================
CREATE TABLE IF NOT EXISTS alerta_conciliacion (
  id SERIAL PRIMARY KEY,
  tipo_alerta VARCHAR(50) NOT NULL,
  descripcion TEXT,
  cantidad_afectados INTEGER,
  monto_afectado NUMERIC(14,2),
  fecha_deteccion TIMESTAMP DEFAULT NOW(),
  estado VARCHAR(20) DEFAULT 'ACTIVA',
  resuelto_en TIMESTAMP NULL
);


-- 2. TABLA DE PAGOS SIN ASIGNAR (Cache)
-- ============================================================================
CREATE TABLE IF NOT EXISTS pagos_sin_asignar_cache (
  pago_id INTEGER PRIMARY KEY,
  fecha_pago DATE,
  monto_pagado NUMERIC(14,2),
  referencia_pago VARCHAR(100),
  prestamo_id INTEGER,
  dias_sin_asignar INTEGER,
  ultima_actualizacion TIMESTAMP DEFAULT NOW()
);


-- 3. FUNCION: Detectar pagos sin asignar
-- ============================================================================
CREATE OR REPLACE FUNCTION detectar_pagos_sin_asignar()
RETURNS TABLE (
  cantidad_pagos INTEGER,
  monto_total NUMERIC,
  pagos_antiguos_30dias INTEGER,
  pagos_antiguos_60dias INTEGER
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    COUNT(*)::INTEGER,
    SUM(pg.monto_pagado)::NUMERIC,
    COUNT(*) FILTER (WHERE pg.fecha_pago <= NOW() - INTERVAL '30 days')::INTEGER,
    COUNT(*) FILTER (WHERE pg.fecha_pago <= NOW() - INTERVAL '60 days')::INTEGER
  FROM pagos pg
  WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = pg.id);
END;
$$ LANGUAGE plpgsql;


-- 4. FUNCION: Actualizar cache de pagos sin asignar
-- ============================================================================
CREATE OR REPLACE FUNCTION actualizar_cache_pagos_sin_asignar()
RETURNS void AS $$
BEGIN
  DELETE FROM pagos_sin_asignar_cache;
  
  INSERT INTO pagos_sin_asignar_cache (pago_id, fecha_pago, monto_pagado, referencia_pago, prestamo_id, dias_sin_asignar)
  SELECT 
    pg.id,
    pg.fecha_pago::DATE,
    pg.monto_pagado,
    pg.referencia_pago,
    pg.prestamo_id,
    EXTRACT(DAY FROM (NOW() - pg.fecha_pago))::INTEGER
  FROM pagos pg
  WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = pg.id)
  ORDER BY pg.fecha_pago DESC;
  
  -- Registrar alerta si hay muchos pagos sin asignar
  IF (SELECT COUNT(*) FROM pagos_sin_asignar_cache) > 100 THEN
    INSERT INTO alerta_conciliacion (tipo_alerta, descripcion, cantidad_afectados, monto_afectado)
    SELECT 
      'MUCHOS_PAGOS_SIN_ASIGNAR',
      'Se detectaron ' || COUNT(*) || ' pagos sin asignar a cuotas',
      COUNT(*),
      SUM(monto_pagado)
    FROM pagos_sin_asignar_cache;
  END IF;
END;
$$ LANGUAGE plpgsql;


-- 5. FUNCION: Detectar pagos antiguos sin asignar
-- ============================================================================
CREATE OR REPLACE FUNCTION alerta_pagos_antiguos_sin_asignar(dias_minimos INTEGER DEFAULT 30)
RETURNS TABLE (
  cantidad INTEGER,
  monto NUMERIC,
  fecha_pago_mas_antigua DATE
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    COUNT(*)::INTEGER,
    SUM(monto_pagado)::NUMERIC,
    MIN(fecha_pago)::DATE
  FROM pagos_sin_asignar_cache
  WHERE dias_sin_asignar >= dias_minimos;
END;
$$ LANGUAGE plpgsql;


-- 6. FUNCION: Detectar cuotas sobre-aplicadas
-- ============================================================================
CREATE OR REPLACE FUNCTION detectar_cuotas_sobre_aplicadas()
RETURNS TABLE (
  cuota_id INTEGER,
  prestamo_id INTEGER,
  monto_cuota NUMERIC,
  monto_aplicado NUMERIC,
  exceso NUMERIC
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    c.id,
    c.prestamo_id,
    c.monto_cuota,
    SUM(cp.monto_aplicado),
    SUM(cp.monto_aplicado) - c.monto_cuota
  FROM cuotas c
  INNER JOIN cuota_pagos cp ON c.id = cp.cuota_id
  GROUP BY c.id, c.prestamo_id, c.monto_cuota
  HAVING SUM(cp.monto_aplicado) > c.monto_cuota;
END;
$$ LANGUAGE plpgsql;


-- 7. TRIGGER: Alertar cuando se registra pago sin prestamo
-- ============================================================================
CREATE OR REPLACE FUNCTION trigger_alerta_pago_sin_cuota()
RETURNS TRIGGER AS $$
DECLARE
  v_count INTEGER;
BEGIN
  -- Verificar si este pago tiene cuota asignada
  SELECT COUNT(*) INTO v_count FROM cuota_pagos WHERE pago_id = NEW.id;
  
  IF v_count = 0 THEN
    -- Registrar en tabla de cache para monitoreo
    INSERT INTO pagos_sin_asignar_cache (pago_id, fecha_pago, monto_pagado, referencia_pago, prestamo_id, dias_sin_asignar)
    VALUES (NEW.id, NEW.fecha_pago::DATE, NEW.monto_pagado, NEW.referencia_pago, NEW.prestamo_id, 0)
    ON CONFLICT (pago_id) DO NOTHING;
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear trigger
DROP TRIGGER IF EXISTS trigger_alerta_pago_sin_cuota ON pagos;
CREATE TRIGGER trigger_alerta_pago_sin_cuota
AFTER INSERT ON pagos
FOR EACH ROW
EXECUTE FUNCTION trigger_alerta_pago_sin_cuota();


-- 8. VISTA: Resumen de Alertas
-- ============================================================================
CREATE OR REPLACE VIEW v_alertas_conciliacion AS
SELECT 
  tipo_alerta,
  COUNT(*) AS cantidad_alertas,
  COUNT(*) FILTER (WHERE estado = 'ACTIVA') AS alertas_activas,
  MAX(fecha_deteccion) AS ultima_alerta,
  SUM(cantidad_afectados) AS total_afectados,
  SUM(monto_afectado) AS monto_total_afectado
FROM alerta_conciliacion
GROUP BY tipo_alerta
ORDER BY alertas_activas DESC;


-- 9. VISTA: Pagos Sin Asignar por Antiguedad
-- ============================================================================
CREATE OR REPLACE VIEW v_pagos_sin_asignar_antiguedad AS
SELECT 
  CASE 
    WHEN dias_sin_asignar < 7 THEN 'Reciente (< 7 dias)'
    WHEN dias_sin_asignar < 30 THEN 'Reciente (7-30 dias)'
    WHEN dias_sin_asignar < 60 THEN 'Antiguo (30-60 dias)'
    ELSE 'Muy Antiguo (> 60 dias)'
  END AS categoria,
  COUNT(*) AS cantidad,
  SUM(monto_pagado) AS monto_total,
  MIN(dias_sin_asignar) AS dias_minimos,
  MAX(dias_sin_asignar) AS dias_maximos
FROM pagos_sin_asignar_cache
GROUP BY categoria
ORDER BY dias_minimos DESC;


-- ============================================================================
-- USO Y MANTENIMIENTO
-- ============================================================================

-- Ejecutar cada hora:
-- SELECT actualizar_cache_pagos_sin_asignar();

-- Verificar alertas activas:
-- SELECT * FROM v_alertas_conciliacion;

-- Detectar pagos sin asignar > 30 dias:
-- SELECT * FROM alerta_pagos_antiguos_sin_asignar(30);

-- Detectar cuotas sobre-aplicadas:
-- SELECT * FROM detectar_cuotas_sobre_aplicadas();
