-- Flujo: tras OCR se envían datos al chat para que el cliente confirme o edite.
-- conversacion_cobranza: estado 'esperando_confirmacion_datos' y informe pendiente a confirmar.
ALTER TABLE conversacion_cobranza ADD COLUMN IF NOT EXISTS pagos_informe_id_pendiente INTEGER REFERENCES pagos_informes(id) ON DELETE SET NULL;
