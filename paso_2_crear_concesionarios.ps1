# ============================================================
# PASO 2: CREAR CONCESIONARIOS
# Los concesionarios son necesarios para registrar clientes
# ============================================================

$baseUrl = "https://pagos-f2qf.onrender.com"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PASO 2: CREAR CONCESIONARIOS" -ForegroundColor Cyan
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
$concesionarios = @(
    @{
        nombre = "AutoMax Santo Domingo"
        direccion = "Av. 27 de Febrero, Santo Domingo"
        telefono = "809-555-1001"
        email = "contacto@automax.com"
        responsable = "Pedro Martínez"
        activo = $true
    },
    @{
        nombre = "Vehículos Premium"
        direccion = "Av. Winston Churchill, Santo Domingo"
        telefono = "809-555-1002"
        email = "ventas@vehiculospremium.com"
        responsable = "Ana López"
        activo = $true
    },
    @{
        nombre = "Concesionario La Estrella"
        direccion = "Calle El Sol, Santiago"
        telefono = "809-555-1003"
        email = "info@laestrella.com"
        responsable = "Luis Fernández"
        activo = $true
    }
)

Write-Host "INGRESANDO CONCESIONARIOS..." -ForegroundColor Yellow
Write-Host ""

$concesionariosCreados = @()

foreach ($concesionario in $concesionarios) {
    Write-Host "Creando concesionario: $($concesionario.nombre)..." -ForegroundColor Cyan
    
    try {
        $concesionarioBody = $concesionario | ConvertTo-Json
        $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/concesionarios/" -Method Post -Headers $authHeaders -Body $concesionarioBody -TimeoutSec 15
        
        Write-Host "  EXITO: Concesionario creado con ID: $($response.id)" -ForegroundColor Green
        $concesionariosCreados += $response
        
    } catch {
        Write-Host "  ERROR: No se pudo crear el concesionario" -ForegroundColor Red
        Write-Host "  Detalles: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host ""
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "RESUMEN" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Total de concesionarios creados: $($concesionariosCreados.Count)" -ForegroundColor Green
Write-Host ""

if ($concesionariosCreados.Count -gt 0) {
    Write-Host "IDs de concesionarios creados (guarda estos IDs):" -ForegroundColor Yellow
    foreach ($conc in $concesionariosCreados) {
        Write-Host "  ID: $($conc.id) - $($conc.nombre)" -ForegroundColor White
    }
    Write-Host ""
    Write-Host "PROXIMO PASO: Ejecutar paso_3_crear_modelos_vehiculos.ps1" -ForegroundColor Cyan
}

