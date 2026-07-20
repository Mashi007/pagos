-- Tabla ya creada en produccion (2026-07-20). Script de referencia / entornos nuevos.
-- Auditoría: rebotes de notificaciones detectados en Gmail (itmaster)

BEGIN;

CREATE TABLE IF NOT EXISTS public.auditoria_rebotes_gmail (
    id                BIGSERIAL PRIMARY KEY,
    gmail_message_id  VARCHAR(64)  NOT NULL,
    gmail_thread_id   VARCHAR(64)  NULL,
    cedula            VARCHAR(20)  NULL,
    correo            VARCHAR(255) NOT NULL,
    observaciones     VARCHAR(50)  NOT NULL,
    asunto_gmail      VARCHAR(500) NULL,
    remitente_detectado VARCHAR(255) NULL,
    etiqueta_gmail    VARCHAR(100) NULL,
    fecha_mensaje     TIMESTAMP WITHOUT TIME ZONE NULL,
    fecha_registro    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    procesado_por     VARCHAR(150) NULL,
    fragmento_cuerpo  TEXT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_auditoria_rebotes_gmail_message
    ON public.auditoria_rebotes_gmail (gmail_message_id);

CREATE INDEX IF NOT EXISTS idx_auditoria_rebotes_gmail_correo
    ON public.auditoria_rebotes_gmail (correo);

CREATE INDEX IF NOT EXISTS idx_auditoria_rebotes_gmail_cedula
    ON public.auditoria_rebotes_gmail (cedula);

CREATE INDEX IF NOT EXISTS idx_auditoria_rebotes_gmail_obs
    ON public.auditoria_rebotes_gmail (observaciones);

CREATE INDEX IF NOT EXISTS idx_auditoria_rebotes_gmail_fecha
    ON public.auditoria_rebotes_gmail (fecha_registro);

COMMIT;
