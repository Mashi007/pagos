# ============================================================
# PASO 6: REGISTRAR PAGOS
# Los pagos se registran basados en los préstamos
# ============================================================

$baseUrl = "https://pagos-f2qf.onrender.com"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PASO 6: REGISTRAR PAGOS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Obtener token si no existe
if (-not $env:AUTH_TOKEN) {
    Write-Host "ERROR: Token no encontrado. Ejecuta primero: paso_0_obtener_token.ps1" -ForegroundColor Red
    exit 1
}

$authHeaders = @{
    "Authorization" = "Bearer $env:AUTH_TOKEN"
    "Content-Type" = "application/json"
}

# DATOS DE EJEMPLO - MODIFICA CON TUS DATOS REALES
# IMPORTANTE: Usa IDs reales de préstamos que creaste en paso_5
$pagos = @(
    # Pagos del préstamo 1
    @{
        prestamo_id = 1  # MODIFICA ESTO CON UN ID REAL
        monto = 650.00
        fecha_pago = "2024-02-15"
        metodo_pago = "TRANSFERENCIA"
        estado = "COMPLETADO"
        referencia = "REF-001-2024-02-15"
        notas = "Pago de cuota 1"
    },
    @{
        prestamo_id = 1
        monto = 650.00
        fecha_pago = "2024-03-15"
        metodo_pago = "TRANSFERENCIA"
        estado = "COMPLETADO"
        referencia = "REF-001-2024-03-15"
        notas = "Pago de cuota 2"
    },
    # Pagos del préstamo 2
    @{
        prestamo_id = 2  # MODIFICA ESTO CON UN ID REAL
        monto = 550.00
        fecha_pago = "2024-03-01"
        metodo_pago = "CHEQUE"
        estado = "COMPLETADO"
        referencia = "CHQ-002-2024-03-01"
        notas = "Pago de cuota 1"
    },
    @{
        prestamo_id = 2
        monto = 550.00
        fecha_pago = "2024-04-01"
        metodo_pago = "CHEQUE"
        estado = "COMPLETADO"
        referencia = "CHQ-002-2024-04-01"
        notas = "Pago de cuota 2"
    },
    # Pagos del préstamo 3
    @{
        prestamo_id = 3  # MODIFICA ESTO CON UN ID REAL
        monto = 580.00
        fecha_pago = "2024-02-20"
        metodo_pago = "EFECTIVO"
        estado = "COMPLETADO"
        referencia = "EFE-003-2024-02-20"
        notas = "Pago de cuota 1"
    },
    @{
        prestamo_id = 3
        monto = 580.00
        fecha_pago = "2024-03-20"
        metodo_pago = "TRANSFERENCIA"
        estado = "COMPLETADO"
        referencia = "TRA-003-2024-03-20"
        notas = "Pago de cuota 2"
    }
)

Write-Host "REGISTRANDO PAGOS..." -ForegroundColor Yellow
Write-Host ""
Write-Host "IMPORTANTE: Verifica que los IDs de préstamos sean correctos" -ForegroundColor Red
Write-Host ""

$pagosCreados = @()

foreach ($pago in $pagos) {
    Write-Host "Registrando pago para préstamo ID $($pago.prestamo_id)..." -ForegroundColor Cyan
    
    try {
        $pagoBody = $pago | ConvertTo-Json
        $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/pagos/" -Method Post -Headers $authHeaders -Body $pagoBody -TimeoutSec 15
        
        Write-Host "  EXITO: Pago registrado con ID: $($response.id)" -ForegroundColor Green
        $pagosCreados += $response
        
    } catch {
        Write-Host "  ERROR: No se pudo registrar el pago" -ForegroundColor Red
        Write-Host "  Detalles: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host ""
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "RESUMEN" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Total de pagos registrados: $($pagosCreados.Count)" -ForegroundColor Green
Write-Host ""

if ($pagosCreados.Count -gt 0) {
    Write-Host "IDs de pagos registrados:" -ForegroundColor Yellow
    foreach ($pag in $pagosCreados) {
        Write-Host "  ID: $($pag.id) - Monto: $($pag.monto) - Préstamo ID: $($pag.prestamo_id)" -ForegroundColor White
    }
    Write-Host ""
    Write-Host "PROXIMO PASO: Ejecutar paso_7_verificar_sistema.ps1" -ForegroundColor Cyan
}

