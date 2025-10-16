# ============================================================
# VERIFICACION DE ESTADO DE TABLAS EN BASE DE DATOS
# ============================================================

$baseUrl = "https://pagos-f2qf.onrender.com"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "VERIFICACION DE ESTADO DE TABLAS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Obtener token
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
    exit 1
}

Write-Host ""

# Verificar estado de cada tabla/modulo
$tablas = @(
    @{name="Usuarios"; url="/api/v1/users/"; endpoint="users"},
    @{name="Clientes"; url="/api/v1/clientes/"; endpoint="clientes"},
    @{name="Prestamos"; url="/api/v1/prestamos/"; endpoint="prestamos"},
    @{name="Pagos"; url="/api/v1/pagos/"; endpoint="pagos"},
    @{name="Asesores"; url="/api/v1/asesores"; endpoint="asesores"},
    @{name="Concesionarios"; url="/api/v1/concesionarios"; endpoint="concesionarios"},
    @{name="Modelos Vehiculos"; url="/api/v1/modelos-vehiculos"; endpoint="modelos_vehiculos"}
)

Write-Host "Verificando estado de tablas/modulos..." -ForegroundColor Yellow
Write-Host ""

$tablasConDatos = 0
$tablasVacias = 0
$tablasConError = 0

foreach ($tabla in $tablas) {
    Write-Host "[$($tabla.name)]" -ForegroundColor Cyan
    Write-Host "    URL: $($tabla.url)" -ForegroundColor Gray
    
    try {
        $response = Invoke-RestMethod -Uri "$baseUrl$($tabla.url)" -Method Get -Headers $authHeaders -TimeoutSec 15
        
        # Verificar si tiene datos
        if ($response.total -and $response.total -gt 0) {
            Write-Host "    OK: $($response.total) registros" -ForegroundColor Green
            $tablasConDatos++
        } elseif ($response.items -and $response.items.Count -gt 0) {
            Write-Host "    OK: $($response.items.Count) registros" -ForegroundColor Green
            $tablasConDatos++
        } elseif ($response.Count -gt 0) {
            Write-Host "    OK: $($response.Count) registros" -ForegroundColor Green
            $tablasConDatos++
        } else {
            Write-Host "    VACIA: Sin registros" -ForegroundColor Yellow
            $tablasVacias++
        }
        
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Host "    ERROR: Status $statusCode" -ForegroundColor Red
        Write-Host "    Mensaje: $($_.Exception.Message)" -ForegroundColor Red
        $tablasConError++
    }
    
    Write-Host ""
}

# Resumen
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "RESUMEN DE ESTADO DE TABLAS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Tablas con datos: $tablasConDatos" -ForegroundColor Green
Write-Host "Tablas vacias: $tablasVacias" -ForegroundColor Yellow
Write-Host "Tablas con error: $tablasConError" -ForegroundColor Red
Write-Host ""

if ($tablasConError -gt 0) {
    Write-Host "PROBLEMA: $tablasConError tablas tienen errores 503" -ForegroundColor Red
    Write-Host "Causa probable: Tablas vacias o foreign keys incorrectos" -ForegroundColor Red
} elseif ($tablasVacias -gt 0) {
    Write-Host "ADVERTENCIA: $tablasVacias tablas estan vacias" -ForegroundColor Yellow
    Write-Host "Solucion: Generar mock data para testing" -ForegroundColor Yellow
} else {
    Write-Host "OK: Todas las tablas tienen datos" -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "FIN DE VERIFICACION" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

