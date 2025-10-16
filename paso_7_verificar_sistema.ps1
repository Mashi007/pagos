# ============================================================
# PASO 7: VERIFICAR SISTEMA COMPLETO CON DATOS REALES
# Verifica que todos los endpoints funcionen correctamente
# ============================================================

# ============================================================
# CONFIGURACION - Cambiar estas variables según tu entorno
# ============================================================
$baseUrl = $env:API_BASE_URL
if (-not $baseUrl) {
    $baseUrl = "https://pagos-f2qf.onrender.com"
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PASO 7: VERIFICACION FINAL DEL SISTEMA" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Obtener token si no existe
if (-not $env:AUTH_TOKEN) {
    Write-Host "ERROR: Token no encontrado. Ejecuta primero: paso_0_obtener_token.ps1" -ForegroundColor Red
    exit 1
}

$authHeaders = @{
    "Authorization" = "Bearer $env:AUTH_TOKEN"
}

Write-Host "VERIFICANDO TODOS LOS ENDPOINTS CON DATOS REALES..." -ForegroundColor Yellow
Write-Host ""

$endpoints = @(
    @{name="Asesores"; url="/api/v1/asesores/"; tipo="Catálogo"},
    @{name="Concesionarios"; url="/api/v1/concesionarios/"; tipo="Catálogo"},
    @{name="Modelos Vehículos"; url="/api/v1/modelos-vehiculos/"; tipo="Catálogo"},
    @{name="Clientes"; url="/api/v1/clientes/"; tipo="Principal"; critical=$true},
    @{name="Préstamos"; url="/api/v1/prestamos/"; tipo="Principal"; critical=$true},
    @{name="Pagos"; url="/api/v1/pagos/"; tipo="Principal"; critical=$true},
    @{name="Reportes Cartera"; url="/api/v1/reportes/cartera"; tipo="Reportes"; critical=$true}
)

$resultados = @()

foreach ($endpoint in $endpoints) {
    $priority = if ($endpoint.critical) { "[CRITICO]" } else { "[Normal]" }
    Write-Host "$priority Verificando $($endpoint.name) ($($endpoint.tipo))..." -ForegroundColor Cyan
    
    try {
        $response = Invoke-RestMethod -Uri "$baseUrl$($endpoint.url)" -Method Get -Headers $authHeaders -TimeoutSec 15
        
        $count = 0
        $status = "OK"
        $message = ""
        
        if ($response.total -ne $null) {
            $count = $response.total
            $message = "$count registros"
        } elseif ($response.items -ne $null) {
            $count = $response.items.Count
            $message = "$count registros"
        } elseif ($response.data -ne $null) {
            $count = 1
            $message = "Data disponible"
        } else {
            $count = 0
            $message = "Funcionando"
        }
        
        Write-Host "  EXITO: $message" -ForegroundColor Green
        
        $resultados += @{
            nombre = $endpoint.name
            tipo = $endpoint.tipo
            estado = "OK"
            count = $count
            critical = $endpoint.critical
        }
        
    } catch {
        $statusCode = if ($_.Exception.Response) { $_.Exception.Response.StatusCode.value__ } else { "N/A" }
        Write-Host "  FALLO: Status $statusCode" -ForegroundColor Red
        
        $resultados += @{
            nombre = $endpoint.name
            tipo = $endpoint.tipo
            estado = "ERROR"
            count = 0
            statusCode = $statusCode
            critical = $endpoint.critical
        }
    }
    
    Write-Host ""
}

# Resumen por tipo
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "RESUMEN POR TIPO" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$catalogos = $resultados | Where-Object { $_.tipo -eq "Catálogo" }
$principales = $resultados | Where-Object { $_.tipo -eq "Principal" }
$reportes = $resultados | Where-Object { $_.tipo -eq "Reportes" }

Write-Host "CATALOGOS (Base de datos):" -ForegroundColor Yellow
foreach ($cat in $catalogos) {
    $color = if ($cat.estado -eq "OK") { "Green" } else { "Red" }
    $icon = if ($cat.estado -eq "OK") { "✓" } else { "✗" }
    Write-Host "  $icon $($cat.nombre): $($cat.count) registros" -ForegroundColor $color
}
Write-Host ""

Write-Host "PRINCIPALES (Operación):" -ForegroundColor Yellow
foreach ($prin in $principales) {
    $color = if ($prin.estado -eq "OK") { "Green" } else { "Red" }
    $icon = if ($prin.estado -eq "OK") { "✓" } else { "✗" }
    Write-Host "  $icon $($prin.nombre): $($prin.count) registros" -ForegroundColor $color
}
Write-Host ""

Write-Host "REPORTES:" -ForegroundColor Yellow
foreach ($rep in $reportes) {
    $color = if ($rep.estado -eq "OK") { "Green" } else { "Red" }
    $icon = if ($rep.estado -eq "OK") { "✓" } else { "✗" }
    Write-Host "  $icon $($rep.nombre): $(if ($rep.count -gt 0) { "$($rep.count) registros" } else { "Funcionando" })" -ForegroundColor $color
}
Write-Host ""

# Estadísticas finales
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "ESTADISTICAS FINALES" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$totalEndpoints = $resultados.Count
$endpointsOk = ($resultados | Where-Object { $_.estado -eq "OK" }).Count
$endpointsError = $totalEndpoints - $endpointsOk
$tasaExito = [math]::Round(($endpointsOk / $totalEndpoints) * 100, 2)

$criticalEndpoints = ($resultados | Where-Object { $_.critical }).Count
$criticalOk = ($resultados | Where-Object { $_.critical -and $_.estado -eq "OK" }).Count
$criticalRate = if ($criticalEndpoints -gt 0) { [math]::Round(($criticalOk / $criticalEndpoints) * 100, 2) } else { 100 }

Write-Host "Total de endpoints: $totalEndpoints" -ForegroundColor White
Write-Host "Funcionando: $endpointsOk" -ForegroundColor Green
Write-Host "Con errores: $endpointsError" -ForegroundColor Red
Write-Host "Tasa de éxito: $tasaExito%" -ForegroundColor $(if ($tasaExito -eq 100) { "Green" } elseif ($tasaExito -ge 80) { "Yellow" } else { "Red" })
Write-Host ""

Write-Host "Endpoints críticos: $criticalEndpoints" -ForegroundColor White
Write-Host "Críticos OK: $criticalOk" -ForegroundColor $(if ($criticalOk -eq $criticalEndpoints) { "Green" } else { "Red" })
Write-Host "Tasa crítica: $criticalRate%" -ForegroundColor $(if ($criticalRate -eq 100) { "Green" } else { "Red" })
Write-Host ""

# Veredicto final
if ($criticalOk -eq $criticalEndpoints -and $endpointsOk -eq $totalEndpoints) {
    Write-Host "🎉 EXCELENTE! SISTEMA 100% FUNCIONAL 🎉" -ForegroundColor Green
    Write-Host "Todos los endpoints funcionan correctamente con datos reales" -ForegroundColor Green
    Write-Host "El sistema está listo para producción" -ForegroundColor Green
} elseif ($criticalOk -eq $criticalEndpoints) {
    Write-Host "✓ EXITO! SISTEMA FUNCIONAL" -ForegroundColor Green
    Write-Host "Todos los endpoints críticos funcionan" -ForegroundColor Green
    Write-Host "Algunos endpoints secundarios pueden necesitar atención" -ForegroundColor Yellow
} else {
    Write-Host "⚠ ATENCION REQUERIDA" -ForegroundColor Yellow
    Write-Host "Algunos endpoints críticos tienen problemas" -ForegroundColor Red
    Write-Host "Se requiere revisión adicional" -ForegroundColor Red
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "FIN DE VERIFICACION" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

