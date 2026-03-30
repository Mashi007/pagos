-- ============================================================================
-- FASE 2 PARTE 2: Tabla Snapshot
-- ============================================================================

DROP TABLE IF EXISTS clientes_retraso_snapshot CASCADE;

CREATE TABLE clientes_retraso_snapshot (
    cliente_id INT PRIMARY KEY,
    cedula VARCHAR(50),
    cuotas_retrasadas INT,
    monto_total_retrasado DECIMAL(15, 2),
    fecha_mas_antigua DATE,
    fecha_mas_reciente DATE,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_clientes_retraso_snapshot_cedula 
ON clientes_retraso_snapshot (cedula);

CREATE INDEX idx_clientes_retraso_snapshot_updated 
ON clientes_retraso_snapshot (updated_at DESC);

-- Verificar
SELECT COUNT(*) as total FROM clientes_retraso_snapshot;
