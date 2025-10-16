# ============================================================
# VERIFICAR TABLAS VACIAS Y PREPARAR CARGA DE DATOS REALES
# ============================================================

$baseUrl = "https://pagos-f2qf.onrender.com"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "VERIFICACION DE TABLAS VACIAS - DATOS REALES" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Obtener token de autenticacion
Write-Host "Obteniendo token de autenticacion..." -ForegroundColor Yellow
try {
    $loginBody = @{
        email = "itmaster@rapicreditca.com"
        password = "R@pi_2025**"
    } | ConvertTo-Json
    
    $loginResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/auth/login" -Method Post -Body $loginBody -ContentType "application/json" -TimeoutSec 15
    $token = $loginResponse.access_token
    Write-Host "OK: Token obtenido" -ForegroundColor Green
    
    $authHeaders = @{
        "Authorization" = "Bearer $token"
    }
    
} catch {
    Write-Host "ERROR: No se pudo obtener token" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host ""

# Verificar estado de cada tabla
Write-Host "Verificando estado de tablas..." -ForegroundColor Yellow

$tablesToCheck = @(
    @{name="Usuarios"; endpoint="/api/v1/users/"; critical=$true},
    @{name="Asesores"; endpoint="/api/v1/asesores/"; critical=$true},
    @{name="Concesionarios"; endpoint="/api/v1/concesionarios/"; critical=$true},
    @{name="Modelos Vehiculos"; endpoint="/api/v1/modelos-vehiculos/"; critical=$true},
    @{name="Clientes"; endpoint="/api/v1/clientes/"; critical=$true},
    @{name="Prestamos"; endpoint="/api/v1/prestamos/"; critical=$true},
    @{name="Pagos"; endpoint="/api/v1/pagos/"; critical=$true},
    @{name="Reportes"; endpoint="/api/v1/reportes/cartera"; critical=$false}
)

$emptyTables = @()
$workingTables = @()
$errorTables = @()

foreach ($table in $tablesToCheck) {
    Write-Host "Verificando $($table.name)..." -ForegroundColor Cyan
    
    try {
        $response = Invoke-RestMethod -Uri "$baseUrl$($table.endpoint)" -Method Get -Headers $authHeaders -TimeoutSec 15
        
        if ($response.total -and $response.total -eq 0) {
            Write-Host "  VACIA: 0 registros" -ForegroundColor Red
            $emptyTables += $table
        } elseif ($response.items -and $response.items.Count -eq 0) {
            Write-Host "  VACIA: 0 registros" -ForegroundColor Red
            $emptyTables += $table
        } elseif ($response.total -and $response.total -gt 0) {
            Write-Host "  OK: $($response.total) registros" -ForegroundColor Green
            $workingTables += $table
        } elseif ($response.items -and $response.items.Count -gt 0) {
            Write-Host "  OK: $($response.items.Count) registros" -ForegroundColor Green
            $workingTables += $table
        } else {
            Write-Host "  OK: Endpoint funcionando" -ForegroundColor Green
            $workingTables += $table
        }
        
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Host "  ERROR: Status $statusCode" -ForegroundColor Red
        $errorTables += $table
    }
    
    Write-Host ""
}

# Resumen de estado
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "RESUMEN DE ESTADO DE TABLAS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "TABLAS VACIAS ($($emptyTables.Count)):" -ForegroundColor Red
foreach ($table in $emptyTables) {
    $priority = if ($table.critical) { "CRITICA" } else { "Normal" }
    Write-Host "  - $($table.name) ($priority)" -ForegroundColor Red
}

Write-Host ""
Write-Host "TABLAS CON DATOS ($($workingTables.Count)):" -ForegroundColor Green
foreach ($table in $workingTables) {
    Write-Host "  - $($table.name)" -ForegroundColor Green
}

Write-Host ""
Write-Host "TABLAS CON ERRORES ($($errorTables.Count)):" -ForegroundColor Yellow
foreach ($table in $errorTables) {
    Write-Host "  - $($table.name)" -ForegroundColor Yellow
}

Write-Host ""

# Recomendaciones
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "RECOMENDACIONES PARA CARGA DE DATOS REALES" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

if ($emptyTables.Count -gt 0) {
    Write-Host "PRIORIDAD ALTA - Cargar datos en:" -ForegroundColor Red
    foreach ($table in $emptyTables) {
        if ($table.critical) {
            Write-Host "  1. $($table.name) - CRITICA para funcionamiento" -ForegroundColor Red
        }
    }
    
    Write-Host ""
    Write-Host "ORDEN RECOMENDADO DE CARGA:" -ForegroundColor Yellow
    Write-Host "  1. Asesores (base para clientes)" -ForegroundColor White
    Write-Host "  2. Concesionarios (base para clientes)" -ForegroundColor White
    Write-Host "  3. Modelos de Vehiculos (base para clientes)" -ForegroundColor White
    Write-Host "  4. Clientes (depende de los anteriores)" -ForegroundColor White
    Write-Host "  5. Prestamos (depende de clientes)" -ForegroundColor White
    Write-Host "  6. Pagos (depende de prestamos)" -ForegroundColor White
    Write-Host ""
    
    Write-Host "METODOS DE CARGA DISPONIBLES:" -ForegroundColor Cyan
    Write-Host "  A) Formularios web (recomendado para pocos registros)" -ForegroundColor White
    Write-Host "  B) Carga masiva via Excel/CSV (recomendado para muchos registros)" -ForegroundColor White
    Write-Host "  C) API directa (recomendado para integraciones)" -ForegroundColor White
    Write-Host ""
    
    Write-Host "VENTAJAS DE DATOS REALES:" -ForegroundColor Green
    Write-Host "  ✅ Solucion definitiva a errores 503" -ForegroundColor Green
    Write-Host "  ✅ Sistema completamente funcional" -ForegroundColor Green
    Write-Host "  ✅ Datos consistentes del negocio" -ForegroundColor Green
    Write-Host "  ✅ Sin dependencias de scripts" -ForegroundColor Green
    Write-Host "  ✅ Base solida para crecimiento" -ForegroundColor Green
    
} else {
    Write-Host "EXCELENTE: Todas las tablas tienen datos!" -ForegroundColor Green
    Write-Host "El sistema deberia estar funcionando correctamente" -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "FIN DE VERIFICACION" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
