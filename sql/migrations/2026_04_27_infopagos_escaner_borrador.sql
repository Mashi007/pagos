-- Borrador persistente del escáner Infopagos (comprobante + metadatos).
-- Aplicar en PostgreSQL antes de usar el escáner con persistencia de borrador.

CREATE TABLE IF NOT EXISTS infopagos_escaner_borrador (
    id VARCHAR(32) PRIMARY KEY,
    cliente_id INTEGER REFERENCES clientes (id) ON DELETE SET NULL,
    usuario_id INTEGER REFERENCES usuarios (id) ON DELETE SET NULL,
    tipo_cedula VARCHAR(2) NOT NULL,
    numero_cedula VARCHAR(13) NOT NULL,
    cedula_normalizada VARCHAR(20) NOT NULL,
    fuente_tasa_cambio VARCHAR(16),
    comprobante_imagen_id VARCHAR(32) NOT NULL REFERENCES pago_comprobante_imagen (id) ON DELETE RESTRICT,
    comprobante_nombre VARCHAR(255) NOT NULL,
    payload_json TEXT,
    estado VARCHAR(24) NOT NULL DEFAULT 'borrador',
    pago_reportado_id INTEGER REFERENCES pagos_reportados (id) ON DELETE SET NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_infopagos_escaner_borrador_cedula_estado
    ON infopagos_escaner_borrador (cedula_normalizada, estado);

CREATE INDEX IF NOT EXISTS idx_infopagos_escaner_borrador_created
    ON infopagos_escaner_borrador (created_at);

COMMENT ON TABLE infopagos_escaner_borrador IS
    'Escáner Infopagos: solo escaneos que no cumplen validadores o marcan duplicado en cartera. Al guardar el reporte se marca confirmado (flujo normal); se puede eliminar o reabrir para editar.';

-- Backfill histórico (opcional): solo registros con señales claras de validación pendiente.
-- No migra "todo"; respeta la regla del producto: únicamente casos que NO cumplen validadores.
-- Criterio aplicado:
--   1) estado en cola manual (pendiente / en_revision), o
--   2) Gemini no exacto (false/error), o
--   3) observación/motivo con texto de validación/duplicado/regla.
-- Requisitos:
--   - Debe existir comprobante_imagen_id (la tabla temporal lo requiere NOT NULL).
--   - Evita duplicar backfills ya ejecutados (NOT EXISTS por pago_reportado_id).
INSERT INTO infopagos_escaner_borrador (
    id,
    cliente_id,
    usuario_id,
    tipo_cedula,
    numero_cedula,
    cedula_normalizada,
    fuente_tasa_cambio,
    comprobante_imagen_id,
    comprobante_nombre,
    payload_json,
    estado,
    pago_reportado_id
)
SELECT
    SUBSTRING(md5('legacy_pr_' || pr.id::text) FROM 1 FOR 32) AS id,
    c.id AS cliente_id,
    pr.usuario_gestion_id AS usuario_id,
    COALESCE(NULLIF(TRIM(pr.tipo_cedula), ''), 'V')::VARCHAR(2) AS tipo_cedula,
    COALESCE(TRIM(pr.numero_cedula), '')::VARCHAR(13) AS numero_cedula,
    UPPER(
        regexp_replace(
            COALESCE(TRIM(pr.tipo_cedula), '') || COALESCE(TRIM(pr.numero_cedula), ''),
            '[^A-Za-z0-9]',
            '',
            'g'
        )
    )::VARCHAR(20) AS cedula_normalizada,
    COALESCE(NULLIF(TRIM(pr.fuente_tasa_cambio), ''), 'euro')::VARCHAR(16) AS fuente_tasa_cambio,
    pr.comprobante_imagen_id,
    COALESCE(NULLIF(TRIM(pr.comprobante_nombre), ''), 'comprobante')::VARCHAR(255) AS comprobante_nombre,
    json_build_object(
        'source', 'backfill_pagos_reportados',
        'pago_reportado_id', pr.id,
        'estado_original', pr.estado,
        'validacion_campos', CASE
            WHEN COALESCE(pr.observacion, '') ~* '(campo|formato|obligatorio|institucion|numero|operacion|monto|cedula)'
                THEN pr.observacion
            ELSE NULL
        END,
        'validacion_reglas', CASE
            WHEN COALESCE(pr.observacion, '') ~* '(regla|tasa|fecha|bs|bolivar|validaci[oó]n)'
                THEN pr.observacion
            ELSE NULL
        END,
        'duplicado_en_pagos', (
            COALESCE(pr.observacion, '') ~* 'duplicad'
            OR COALESCE(pr.motivo_rechazo, '') ~* 'duplicad'
        ),
        'gemini_coincide_exacto', pr.gemini_coincide_exacto
    )::TEXT AS payload_json,
    'borrador'::VARCHAR(24) AS estado,
    pr.id AS pago_reportado_id
FROM pagos_reportados pr
LEFT JOIN clientes c
    ON UPPER(regexp_replace(COALESCE(c.cedula, ''), '[^A-Za-z0-9]', '', 'g')) =
       UPPER(regexp_replace(COALESCE(pr.tipo_cedula, '') || COALESCE(pr.numero_cedula, ''), '[^A-Za-z0-9]', '', 'g'))
WHERE
    pr.comprobante_imagen_id IS NOT NULL
    AND (
        LOWER(COALESCE(pr.estado, '')) IN ('pendiente', 'en_revision')
        OR LOWER(COALESCE(pr.gemini_coincide_exacto, '')) IN ('false', 'error')
        OR COALESCE(pr.observacion, '') ~* '(validaci[oó]n|regla|duplicad|tasa|monto|fecha|cedula|operaci[oó]n|instituci[oó]n)'
        OR COALESCE(pr.motivo_rechazo, '') ~* '(validaci[oó]n|regla|duplicad|tasa|monto|fecha|cedula|operaci[oó]n|instituci[oó]n)'
    )
    AND NOT EXISTS (
        SELECT 1
        FROM infopagos_escaner_borrador b
        WHERE b.pago_reportado_id = pr.id
    );
