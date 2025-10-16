# ============================================================
# PASO 5: CREAR PRESTAMOS
# Los préstamos se crean basados en los clientes
# ============================================================

$baseUrl = "https://pagos-f2qf.onrender.com"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PASO 5: CREAR PRESTAMOS" -ForegroundColor Cyan
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
# IMPORTANTE: Usa IDs reales de clientes que creaste en paso_4
$prestamos = @(
    @{
        cliente_id = 1  # MODIFICA ESTO CON UN ID REAL
        monto_prestamo = 20000.00
        tasa_interes = 12.5
        plazo_meses = 36
        tipo_prestamo = "VEHICULAR"
        estado = "APROBADO"
        fecha_aprobacion = "2024-01-15"
        notas = "Préstamo para vehículo Toyota Corolla 2023"
    },
    @{
        cliente_id = 2  # MODIFICA ESTO CON UN ID REAL
        monto_prestamo = 21000.00
        tasa_interes = 11.8
        plazo_meses = 48
        tipo_prestamo = "VEHICULAR"
        estado = "APROBADO"
        fecha_aprobacion = "2024-02-01"
        notas = "Préstamo para vehículo Honda Civic 2023"
    },
    @{
        cliente_id = 3  # MODIFICA ESTO CON UN ID REAL
        monto_prestamo = 18000.00
        tasa_interes = 13.0
        plazo_meses = 36
        tipo_prestamo = "VEHICULAR"
        estado = "APROBADO"
        fecha_aprobacion = "2024-01-20"
        notas = "Préstamo para vehículo Nissan Sentra 2024"
    }
)

Write-Host "INGRESANDO PRESTAMOS..." -ForegroundColor Yellow
Write-Host ""
Write-Host "IMPORTANTE: Verifica que los IDs de clientes sean correctos" -ForegroundColor Red
Write-Host ""

$prestamosCreados = @()

foreach ($prestamo in $prestamos) {
    Write-Host "Creando préstamo para cliente ID $($prestamo.cliente_id)..." -ForegroundColor Cyan
    
    try {
        $prestamoBody = $prestamo | ConvertTo-Json
        $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/prestamos/" -Method Post -Headers $authHeaders -Body $prestamoBody -TimeoutSec 15
        
        Write-Host "  EXITO: Préstamo creado con ID: $($response.id)" -ForegroundColor Green
        $prestamosCreados += $response
        
    } catch {
        Write-Host "  ERROR: No se pudo crear el préstamo" -ForegroundColor Red
        Write-Host "  Detalles: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host ""
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "RESUMEN" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Total de préstamos creados: $($prestamosCreados.Count)" -ForegroundColor Green
Write-Host ""

if ($prestamosCreados.Count -gt 0) {
    Write-Host "IDs de préstamos creados (guarda estos IDs):" -ForegroundColor Yellow
    foreach ($pres in $prestamosCreados) {
        Write-Host "  ID: $($pres.id) - Monto: $($pres.monto_prestamo) - Cliente ID: $($pres.cliente_id)" -ForegroundColor White
    }
    Write-Host ""
    Write-Host "PROXIMO PASO: Ejecutar paso_6_crear_pagos.ps1" -ForegroundColor Cyan
}

