# ============================================================
# PASO 3: CREAR MODELOS DE VEHICULOS
# Los modelos son necesarios para registrar clientes
# ============================================================

$baseUrl = "https://pagos-f2qf.onrender.com"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PASO 3: CREAR MODELOS DE VEHICULOS" -ForegroundColor Cyan
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
$modelos = @(
    @{
        modelo = "Toyota Corolla 2023"
        activo = $true
    },
    @{
        modelo = "Honda Civic 2023"
        activo = $true
    },
    @{
        modelo = "Nissan Sentra 2024"
        activo = $true
    },
    @{
        modelo = "Hyundai Elantra 2023"
        activo = $true
    },
    @{
        modelo = "Mazda 3 2024"
        activo = $true
    },
    @{
        modelo = "Kia Forte 2023"
        activo = $true
    }
)

Write-Host "INGRESANDO MODELOS DE VEHICULOS..." -ForegroundColor Yellow
Write-Host ""

$modelosCreados = @()

foreach ($modelo in $modelos) {
    Write-Host "Creando modelo: $($modelo.modelo)..." -ForegroundColor Cyan
    
    try {
        $modeloBody = $modelo | ConvertTo-Json
        $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/modelos-vehiculos/" -Method Post -Headers $authHeaders -Body $modeloBody -TimeoutSec 15
        
        Write-Host "  EXITO: Modelo creado con ID: $($response.id)" -ForegroundColor Green
        $modelosCreados += $response
        
    } catch {
        Write-Host "  ERROR: No se pudo crear el modelo" -ForegroundColor Red
        Write-Host "  Detalles: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host ""
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "RESUMEN" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Total de modelos creados: $($modelosCreados.Count)" -ForegroundColor Green
Write-Host ""

if ($modelosCreados.Count -gt 0) {
    Write-Host "IDs de modelos creados (guarda estos IDs):" -ForegroundColor Yellow
    foreach ($mod in $modelosCreados) {
        Write-Host "  ID: $($mod.id) - $($mod.modelo)" -ForegroundColor White
    }
    Write-Host ""
    Write-Host "PROXIMO PASO: Ejecutar paso_4_crear_clientes.ps1" -ForegroundColor Cyan
}

