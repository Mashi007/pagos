-- ============================================================================
-- FASE 2 PARTE 5: Funciones y Triggers
-- ============================================================================

CREATE OR REPLACE FUNCTION actualizar_retraso_snapshot()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY clientes_retrasados_mv;
    
    DELETE FROM clientes_retraso_snapshot;
    INSERT INTO clientes_retraso_snapshot 
        (cliente_id, cedula, cuotas_retrasadas, monto_total_retrasado, 
         fecha_mas_antigua, fecha_mas_reciente, updated_at)
    SELECT 
        id, cedula, cuotas_retrasadas, monto_total_retrasado,
        fecha_mas_antigua, fecha_mas_reciente, NOW()
    FROM clientes_retrasados_mv;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_actualizar_retraso_snapshot ON cuotas;
CREATE TRIGGER trigger_actualizar_retraso_snapshot
AFTER INSERT OR UPDATE ON cuotas
FOR EACH ROW
EXECUTE FUNCTION actualizar_retraso_snapshot();

CREATE OR REPLACE FUNCTION limpiar_caches_expirados()
RETURNS void AS $$
BEGIN
    DELETE FROM email_config_cache WHERE expires_at < NOW();
    DELETE FROM adjuntos_fijos_cache WHERE updated_at < NOW() - INTERVAL '24 hours';
    RAISE NOTICE 'Cachés limpiados';
END;
$$ LANGUAGE plpgsql;

-- Verificar
SELECT COUNT(*) as triggers FROM information_schema.triggers 
WHERE trigger_name = 'trigger_actualizar_retraso_snapshot';
