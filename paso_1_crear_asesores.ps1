# ============================================================
# PASO 1: CREAR ASESORES
# Los asesores son necesarios para asignar clientes
# ============================================================

$baseUrl = "https://pagos-f2qf.onrender.com"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PASO 1: CREAR ASESORES" -ForegroundColor Cyan
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
$asesores = @(
    @{
        nombre = "Juan"
        apellido = "Pérez"
        email = "juan.perez@rapicreditca.com"
        telefono = "809-555-0001"
        especialidad = "Ventas de Vehículos"
        activo = $true
    },
    @{
        nombre = "María"
        apellido = "González"
        email = "maria.gonzalez@rapicreditca.com"
        telefono = "809-555-0002"
        especialidad = "Créditos Personales"
        activo = $true
    },
    @{
        nombre = "Carlos"
        apellido = "Rodríguez"
        email = "carlos.rodriguez@rapicreditca.com"
        telefono = "809-555-0003"
        especialidad = "Cobranza"
        activo = $true
    }
)

Write-Host "INGRESANDO ASESORES..." -ForegroundColor Yellow
Write-Host ""

$asesoresCreados = @()

foreach ($asesor in $asesores) {
    Write-Host "Creando asesor: $($asesor.nombre) $($asesor.apellido)..." -ForegroundColor Cyan
    
    try {
        $asesorBody = $asesor | ConvertTo-Json
        $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/asesores/" -Method Post -Headers $authHeaders -Body $asesorBody -TimeoutSec 15
        
        Write-Host "  EXITO: Asesor creado con ID: $($response.id)" -ForegroundColor Green
        $asesoresCreados += $response
        
    } catch {
        Write-Host "  ERROR: No se pudo crear el asesor" -ForegroundColor Red
        Write-Host "  Detalles: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host ""
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "RESUMEN" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Total de asesores creados: $($asesoresCreados.Count)" -ForegroundColor Green
Write-Host ""

if ($asesoresCreados.Count -gt 0) {
    Write-Host "IDs de asesores creados (guarda estos IDs):" -ForegroundColor Yellow
    foreach ($asesor in $asesoresCreados) {
        Write-Host "  ID: $($asesor.id) - $($asesor.nombre) $($asesor.apellido)" -ForegroundColor White
    }
    Write-Host ""
    Write-Host "PROXIMO PASO: Ejecutar paso_2_crear_concesionarios.ps1" -ForegroundColor Cyan
}

