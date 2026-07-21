-- KPIs permanentes del escaneo de rebotes Gmail (singleton, no se borra con DELETE del detalle).
BEGIN;

CREATE TABLE IF NOT EXISTS public.auditoria_rebotes_gmail_kpis (
    id                      SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    total_escaneados        BIGINT NOT NULL DEFAULT 0,
    total_guardados         BIGINT NOT NULL DEFAULT 0,
    total_omitidos          BIGINT NOT NULL DEFAULT 0,
    total_sin_correo        BIGINT NOT NULL DEFAULT 0,
    total_sin_cedula        BIGINT NOT NULL DEFAULT 0,
    total_cedula_duplicada  BIGINT NOT NULL DEFAULT 0,
    total_ya_existentes     BIGINT NOT NULL DEFAULT 0,
    total_mal               BIGINT NOT NULL DEFAULT 0,
    total_lleno             BIGINT NOT NULL DEFAULT 0,
    total_temporal          BIGINT NOT NULL DEFAULT 0,
    total_otro              BIGINT NOT NULL DEFAULT 0,
    total_corridas          BIGINT NOT NULL DEFAULT 0,
    ultima_corrida_at       TIMESTAMP WITHOUT TIME ZONE NULL,
    actualizado_en          TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO public.auditoria_rebotes_gmail_kpis (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;

COMMIT;
