-- Migración 016: tabla secuencia_referencia_cobros (referencias RPC-YYYYMMDD-XXXXX)
-- Ejecutar en DBeaver contra la BD de producción/desarrollo.

CREATE TABLE IF NOT EXISTS secuencia_referencia_cobros (
    fecha DATE PRIMARY KEY,
    siguiente INTEGER NOT NULL DEFAULT 1
);

COMMENT ON TABLE secuencia_referencia_cobros IS
'Contador por día para referencia_interna de pagos_reportados (RPC-YYYYMMDD-XXXXX)';
