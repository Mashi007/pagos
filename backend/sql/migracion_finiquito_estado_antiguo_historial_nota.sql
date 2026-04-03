-- =============================================================================
-- Finiquito: estado ANTIGUO (bandeja admin) + nota justificativa en historial
-- Ejecutar una vez en PostgreSQL.
-- =============================================================================

ALTER TABLE finiquito_estado_historial
  ADD COLUMN IF NOT EXISTS nota TEXT NULL;

COMMENT ON COLUMN finiquito_estado_historial.nota IS
  'Opcional: justificacion al pasar a ANTIGUO si ultima fecha de pago es posterior al corte de migracion; auditoria.';
