-- =============================================================================
-- Control 5 (pagos_mismo_dia_monto): autorizacion "Visto" por administrador
-- - Excluye el pago del conteo de duplicados fecha+monto (columna en pagos).
-- - Bitacora append-only en auditoria_pago_control5_visto.
-- Ejecutar una vez en PostgreSQL (Render / local).
-- =============================================================================

ALTER TABLE pagos
  ADD COLUMN IF NOT EXISTS excluir_control_pagos_mismo_dia_monto BOOLEAN NOT NULL DEFAULT false;

COMMENT ON COLUMN pagos.excluir_control_pagos_mismo_dia_monto IS
  'True: este pago no cuenta en control auditoria pagos_mismo_dia_monto (duplicado fecha+monto autorizado; p. ej. Banco Mercantil sin serie de documento).';

CREATE TABLE IF NOT EXISTS auditoria_pago_control5_visto (
  id SERIAL PRIMARY KEY,
  pago_id INTEGER NOT NULL REFERENCES pagos (id) ON DELETE CASCADE,
  prestamo_id INTEGER REFERENCES prestamos (id) ON DELETE SET NULL,
  usuario_id INTEGER NOT NULL REFERENCES usuarios (id),
  creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  numero_documento_anterior VARCHAR(100),
  numero_documento_nuevo VARCHAR(100) NOT NULL,
  sufijo_cuatro_digitos CHAR(4) NOT NULL,
  codigo_control VARCHAR(80) NOT NULL DEFAULT 'pagos_mismo_dia_monto'
);

CREATE INDEX IF NOT EXISTS ix_aud_p5v_pago ON auditoria_pago_control5_visto (pago_id);
CREATE INDEX IF NOT EXISTS ix_aud_p5v_prestamo ON auditoria_pago_control5_visto (prestamo_id);
CREATE INDEX IF NOT EXISTS ix_aud_p5v_creado ON auditoria_pago_control5_visto (creado_en DESC);

COMMENT ON TABLE auditoria_pago_control5_visto IS
  'Auditoria: admin aplico Visto control 5 (sufijo aleatorio 4 digitos al numero_documento; excluye de duplicado fecha+monto).';
