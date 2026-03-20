-- =============================================================================
-- PASO 1: Crear tabla de auditoria y funcion para actualizar a LIQUIDADO
-- =============================================================================

-- 1. Tabla de auditoria
CREATE TABLE IF NOT EXISTS auditoria_cambios_estado_prestamo (
    id SERIAL PRIMARY KEY,
    prestamo_id INTEGER NOT NULL REFERENCES prestamos(id),
    estado_anterior VARCHAR(50),
    estado_nuevo VARCHAR(50),
    motivo VARCHAR(255),
    fecha_cambio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ejecutado_por VARCHAR(100) DEFAULT 'sistema_automatico',
    total_financiamiento NUMERIC(14,2),
    suma_pagado NUMERIC(14,2)
);

CREATE INDEX IF NOT EXISTS idx_auditoria_prestamo_id 
    ON auditoria_cambios_estado_prestamo(prestamo_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_fecha_cambio 
    ON auditoria_cambios_estado_prestamo(fecha_cambio DESC);

-- 2. Funcion para actualizar prestamos a LIQUIDADO
CREATE OR REPLACE FUNCTION actualizar_prestamos_a_liquidado_automatico()
RETURNS void AS 'BEGIN
  -- Actualizar prestamos APROBADO que tienen 100% pagado
  WITH prestamos_a_liquidar AS (
    SELECT
      p.id,
      p.total_financiamiento::numeric(14,2) AS capital,
      COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = ''PAGADO''), 0)::numeric(14,2) AS suma_pagado
    FROM prestamos p
    LEFT JOIN cuotas c ON c.prestamo_id = p.id
    WHERE p.estado = ''APROBADO''
    GROUP BY p.id, p.total_financiamiento
    HAVING COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = ''PAGADO''), 0) >= p.total_financiamiento - 0.01
  )
  UPDATE prestamos p
  SET estado = ''LIQUIDADO''
  FROM prestamos_a_liquidar pal
  WHERE p.id = pal.id
    AND p.estado = ''APROBADO''
    AND ABS(p.total_financiamiento - pal.suma_pagado) <= 0.01;

  -- Registrar en auditoria
  INSERT INTO auditoria_cambios_estado_prestamo
    (prestamo_id, estado_anterior, estado_nuevo, motivo, total_financiamiento, suma_pagado)
  SELECT
    p.id,
    ''APROBADO'',
    ''LIQUIDADO'',
    ''Actualizacion automatica: 100% pagado'',
    p.total_financiamiento::numeric(14,2),
    COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = ''PAGADO''), 0)::numeric(14,2)
  FROM prestamos p
  LEFT JOIN cuotas c ON c.prestamo_id = p.id
  WHERE p.estado = ''LIQUIDADO''
    AND p.id IN (
      SELECT p2.id
      FROM prestamos p2
      LEFT JOIN cuotas c2 ON c2.prestamo_id = p2.id
      WHERE p2.estado = ''LIQUIDADO''
      GROUP BY p2.id, p2.total_financiamiento
      HAVING COALESCE(SUM(c2.monto_cuota) FILTER (WHERE c2.estado = ''PAGADO''), 0) >= p2.total_financiamiento - 0.01
    )
  GROUP BY p.id, p.total_financiamiento;
END;' LANGUAGE plpgsql;
