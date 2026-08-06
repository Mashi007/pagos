-- Evidencias de notificaciones (PDF unico: correo + anexo si aplica).
-- Origen: buzon itmaster@, etiquetas Gmail: DIA SIGUIENTE / 1 CUOTA / 2 O MAS CUOTAS.
-- Ejecutar en DBeaver sobre la misma BD de la app (despues de backup si aplica).

BEGIN;

CREATE TABLE IF NOT EXISTS public.evidencias_notificacion (
    id                  BIGSERIAL PRIMARY KEY,
    gmail_message_id    VARCHAR(64)  NOT NULL,
    gmail_thread_id     VARCHAR(64)  NULL,
    etiqueta_gmail      VARCHAR(40)  NOT NULL,
    email_cliente       VARCHAR(255) NOT NULL,
    email_cliente_norm  VARCHAR(255) NOT NULL,
    cedula              VARCHAR(50)  NULL,
    asunto              VARCHAR(500) NULL,
    fecha_mensaje       TIMESTAMP WITHOUT TIME ZONE NULL,
    pdf_contenido       BYTEA        NOT NULL,
    pdf_tamano_bytes    INTEGER      NOT NULL DEFAULT 0,
    tiene_anexo         BOOLEAN      NOT NULL DEFAULT FALSE,
    fuente_anexo        VARCHAR(20)  NULL,
    procesado_por       VARCHAR(150) NULL,
    fecha_registro      TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE public.evidencias_notificacion IS
  'PDF unico (correo + anexo dia siguiente) archivado desde etiquetas Gmail en itmaster.';
COMMENT ON COLUMN public.evidencias_notificacion.gmail_message_id IS
  'Id de mensaje Gmail; unico para idempotencia del escaneo.';
COMMENT ON COLUMN public.evidencias_notificacion.etiqueta_gmail IS
  'DIA SIGUIENTE | 1 CUOTA | 2 O MAS CUOTAS';
COMMENT ON COLUMN public.evidencias_notificacion.email_cliente_norm IS
  'Email del cliente en minusculas trim; busqueda rapida.';
COMMENT ON COLUMN public.evidencias_notificacion.pdf_contenido IS
  'PDF unico (cuerpo del correo + anexos PDF fusionados).';
COMMENT ON COLUMN public.evidencias_notificacion.fuente_anexo IS
  'Origen del anexo fusionado: gmail, sistema (adjuntos fijos dias_1_retraso) o ninguno.';

CREATE UNIQUE INDEX IF NOT EXISTS uq_evidencias_notificacion_gmail_message
    ON public.evidencias_notificacion (gmail_message_id);

CREATE INDEX IF NOT EXISTS idx_evidencias_notificacion_email_norm
    ON public.evidencias_notificacion (email_cliente_norm);

CREATE INDEX IF NOT EXISTS idx_evidencias_notificacion_cedula
    ON public.evidencias_notificacion (cedula);

CREATE INDEX IF NOT EXISTS idx_evidencias_notificacion_etiqueta
    ON public.evidencias_notificacion (etiqueta_gmail);

CREATE INDEX IF NOT EXISTS idx_evidencias_notificacion_fecha_mensaje
    ON public.evidencias_notificacion (fecha_mensaje DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_evidencias_notificacion_fecha_registro
    ON public.evidencias_notificacion (fecha_registro DESC);

DO $$
BEGIN
  CREATE EXTENSION IF NOT EXISTS pg_trgm;
EXCEPTION
  WHEN insufficient_privilege THEN
    RAISE NOTICE 'Sin privilegio para CREATE EXTENSION pg_trgm; se omiten indices GIN.';
  WHEN OTHERS THEN
    RAISE NOTICE 'pg_trgm no disponible (%); se omiten indices GIN.', SQLERRM;
END $$;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm') THEN
    CREATE INDEX IF NOT EXISTS idx_evidencias_notificacion_email_trgm
      ON public.evidencias_notificacion USING gin (email_cliente_norm gin_trgm_ops);
    CREATE INDEX IF NOT EXISTS idx_evidencias_notificacion_cedula_trgm
      ON public.evidencias_notificacion USING gin (cedula gin_trgm_ops);
  END IF;
END $$;

COMMIT;
