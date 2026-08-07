BEGIN;
DROP INDEX IF EXISTS ix_evidencias_notificacion_etiqueta_gmail;
DROP INDEX IF EXISTS ix_evidencias_notificacion_gmail_message_id;
DROP INDEX IF EXISTS ix_evidencias_notificacion_cedula;
DROP INDEX IF EXISTS ix_evidencias_notificacion_fecha_registro;
DROP INDEX IF EXISTS ix_evidencias_notificacion_email_cliente_norm;
COMMIT;
