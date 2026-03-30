# ============================================================================
# Script para aplicar migración de índices a BD de producción (Windows)
# Uso: .\aplicar_migracion.ps1
# ============================================================================

param(
    [string]$DatabaseUrl = $env:DATABASE_URL,
    [switch]$SkipAnalyze = $false,
    [switch]$DryRun = $false
)

# Colores
$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor $Yellow
Write-Host "MIGRACIÓN: Crear índices para optimizar APIs públicas" -ForegroundColor $Yellow
Write-Host "Fecha: 2026-03-30" -ForegroundColor $Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor $Yellow
Write-Host ""

# Verificar DATABASE_URL
if (-not $DatabaseUrl) {
    Write-Host "ERROR: DATABASE_URL no está configurada" -ForegroundColor $Red
    Write-Host "Configura: `$env:DATABASE_URL = 'postgresql://user:pass@host/db'" -ForegroundColor $Red
    exit 1
}

Write-Host "✓ DATABASE_URL detectada" -ForegroundColor $Green
Write-Host ""

if ($DryRun) {
    Write-Host "⚠ DRY RUN: Mostrando SQL sin ejecutar" -ForegroundColor $Yellow
    Write-Host ""
}

# SQL para crear índices
$sql = @"
-- 1. Índice: Búsqueda rápida de clientes por cédula
CREATE INDEX IF NOT EXISTS idx_cliente_cedula ON clientes (cedula)
WHERE cedula IS NOT NULL;

-- 2. Índice: Códigos de estado de cuenta activos
CREATE INDEX IF NOT EXISTS idx_estado_cuenta_codigo_cedula_activo 
ON estado_cuenta_codigos (cedula_normalizada, usado, expira_en)
WHERE usado = FALSE;

-- 3. Índice: Préstamos por cliente y estado APROBADO
CREATE INDEX IF NOT EXISTS idx_prestamo_cliente_estado 
ON prestamos (cliente_id, estado)
WHERE estado = 'APROBADO';

-- 4. Índice: Pagos reportados por cédula y estado
CREATE INDEX IF NOT EXISTS idx_pago_reportado_cedula_estado 
ON pagos_reportados (tipo_cedula, numero_cedula, estado);

-- 5. Índice: Cuotas por préstamo
CREATE INDEX IF NOT EXISTS idx_cuota_prestamo 
ON cuotas (prestamo_id, numero_cuota)
WHERE estado != 'CANCELADA';

-- Verificación
SELECT 
    COUNT(*) as total_indices,
    NOW() as timestamp
FROM pg_indexes
WHERE indexname IN (
    'idx_cliente_cedula',
    'idx_estado_cuenta_codigo_cedula_activo',
    'idx_prestamo_cliente_estado',
    'idx_pago_reportado_cedula_estado',
    'idx_cuota_prestamo'
);
"@

if ($DryRun) {
    Write-Host "SQL a ejecutar:" -ForegroundColor $Yellow
    Write-Host $sql
    Write-Host ""
    exit 0
}

# Ejecutar SQL
try {
    Write-Host "Ejecutando migración de índices..." -ForegroundColor $Yellow
    Write-Host ""
    
    # Usar psql si está disponible, si no usar conexión alternativa
    if (Get-Command psql -ErrorAction SilentlyContinue) {
        $sql | psql $DatabaseUrl
    } else {
        Write-Host "WARNING: psql no encontrado en PATH" -ForegroundColor $Yellow
        Write-Host "Instala PostgreSQL client tools o ejecuta SQL manualmente:" -ForegroundColor $Yellow
        Write-Host ""
        Write-Host "Contenido del archivo SQL:" -ForegroundColor $Yellow
        Write-Host $sql
        exit 1
    }
    
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor $Green
    Write-Host "✓ MIGRACIÓN COMPLETADA EXITOSAMENTE" -ForegroundColor $Green
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor $Green
    Write-Host ""
    Write-Host "Índices creados:" -ForegroundColor $Green
    Write-Host "  1. idx_cliente_cedula (clientes)"
    Write-Host "  2. idx_estado_cuenta_codigo_cedula_activo (estado_cuenta_codigos)"
    Write-Host "  3. idx_prestamo_cliente_estado (prestamos)"
    Write-Host "  4. idx_pago_reportado_cedula_estado (pagos_reportados)"
    Write-Host "  5. idx_cuota_prestamo (cuotas)"
    Write-Host ""
    Write-Host "Próximos pasos:" -ForegroundColor $Yellow
    Write-Host "  1. Ejecutar VACUUM ANALYZE:"
    Write-Host "     psql `$env:DATABASE_URL -c 'VACUUM ANALYZE;'"
    Write-Host ""
    Write-Host "  2. Monitorear en próximas 24h:"
    Write-Host "     - Latencia en /validar-cedula"
    Write-Host "     - Latencia en /recibo-cuota"
    Write-Host "     - Latencia en pagos-reportados/listado-y-kpis"
    Write-Host ""
    
} catch {
    Write-Host "ERROR: Falló la migración" -ForegroundColor $Red
    Write-Host $_.Exception.Message -ForegroundColor $Red
    exit 1
}
