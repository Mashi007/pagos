-- Secuencia atómica por día para referencias de reportes de pago (RPC-YYYYMMDD-XXXXX).
-- Evita colisiones cuando varias peticiones generan referencia a la vez.
CREATE TABLE IF NOT EXISTS secuencia_referencia_cobros (
    fecha DATE PRIMARY KEY,
    siguiente INTEGER NOT NULL DEFAULT 1
);

COMMENT ON TABLE secuencia_referencia_cobros IS 'Contador por día para referencia_interna de pagos_reportados (RPC-YYYYMMDD-XXXXX)';
