-- Tabla pagos_con_errores: pagos con errores de validación desde Carga Masiva.
-- No se mezclan con pagos que cumplen validadores (tabla pagos).
-- Revisar Pagos y el front muestran solo esta tabla.
--
-- Ejecutar: psql $DATABASE_URL -f backend/scripts/006_pagos_con_errores.sql

CREATE TABLE IF NOT EXISTS pagos_con_errores (
  id SERIAL PRIMARY KEY,
  cedula VARCHAR(20),
  prestamo_id INTEGER REFERENCES prestamos(id) ON DELETE SET NULL,
  fecha_pago TIMESTAMP NOT NULL,
  monto_pagado NUMERIC(14, 2) NOT NULL,
  numero_documento VARCHAR(100),
  institucion_bancaria VARCHAR(255),
  estado VARCHAR(30) DEFAULT 'PENDIENTE',
  fecha_registro TIMESTAMP NOT NULL DEFAULT NOW(),
  fecha_conciliacion TIMESTAMP,
  conciliado BOOLEAN DEFAULT FALSE,
  verificado_concordancia VARCHAR(10) DEFAULT '',
  usuario_registro VARCHAR(255),
  notas TEXT,
  documento_nombre VARCHAR(255),
  documento_tipo VARCHAR(50),
  documento_ruta VARCHAR(255),
  referencia_pago VARCHAR(100) NOT NULL DEFAULT '',
  errores_descripcion JSONB,
  fila_origen INTEGER,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pagos_con_errores_cedula ON pagos_con_errores(cedula);
CREATE INDEX IF NOT EXISTS idx_pagos_con_errores_fecha_pago ON pagos_con_errores(fecha_pago);
CREATE INDEX IF NOT EXISTS idx_pagos_con_errores_fecha_registro ON pagos_con_errores(fecha_registro DESC);

COMMENT ON TABLE pagos_con_errores IS 'Pagos con errores de validación desde Carga Masiva. Vista Revisar Pagos. Al descargar Excel se eliminan.';

-- Si existía la tabla exportados (versión anterior), eliminarla
DROP TABLE IF EXISTS pagos_con_errores_exportados;

-- Migración: mover pagos existentes que se identifican como "con errores".
-- Criterio: pagos con prestamo_id NULL que NO están en revisar_pagos.
-- NOTA: Sin un flag en pagos no podemos distinguir con certeza. Esta migración
-- mueve pagos sin crédito que podrían ser válidos. Ejecutar solo si aplica.
--
-- Para migración manual (descomentar y ajustar criterio si es necesario):
/*
INSERT INTO pagos_con_errores (
  cedula, prestamo_id, fecha_pago, monto_pagado, numero_documento,
  institucion_bancaria, estado, fecha_registro, fecha_conciliacion, conciliado,
  verificado_concordancia, usuario_registro, notas, documento_nombre, documento_tipo,
  documento_ruta, referencia_pago, errores_descripcion
)
SELECT
  p.cedula, p.prestamo_id, p.fecha_pago, p.monto_pagado, p.numero_documento,
  p.institucion_bancaria, COALESCE(p.estado, 'PENDIENTE'), p.fecha_registro,
  p.fecha_conciliacion, COALESCE(p.conciliado, FALSE),
  COALESCE(p.verificado_concordancia, ''), p.usuario_registro, p.notas,
  p.documento_nombre, p.documento_tipo, p.documento_ruta,
  COALESCE(p.referencia_pago, ''), '[]'::jsonb
FROM pagos p
WHERE p.prestamo_id IS NULL
  AND NOT EXISTS (SELECT 1 FROM revisar_pagos rp WHERE rp.pago_id = p.id);
-- Tras verificar, opcional: DELETE FROM pagos WHERE id IN (...migrados...);
*/
