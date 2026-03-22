-- Opcional: vaciar por completo la cola temporal de descargas (legacy).
-- Útil si quedaron filas huérfanas tras migrar al flujo único
-- GET /pagos-reportados/exportar-aprobados-excel
--
-- Revisar antes:
-- SELECT COUNT(*) FROM pagos_pendiente_descargar;
--
-- TRUNCATE reinicia identidades según motor; en PostgreSQL:
-- TRUNCATE TABLE pagos_pendiente_descargar RESTART IDENTITY;

DELETE FROM pagos_pendiente_descargar;
