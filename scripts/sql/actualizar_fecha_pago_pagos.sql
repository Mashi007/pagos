-- Actualizar fecha_pago en tabla pagos para pagos de ABONO_2026
-- Usa la fecha actual del sistema

UPDATE pagos
SET fecha_pago = CURRENT_TIMESTAMP,
    fecha_actualizacion = CURRENT_TIMESTAMP
WHERE numero_documento LIKE 'ABONO_2026_%'
  AND activo = TRUE;
