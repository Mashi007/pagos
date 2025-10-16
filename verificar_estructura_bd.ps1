# ============================================================
# VERIFICAR ESTRUCTURA REAL DE LA BASE DE DATOS
# ============================================================

$baseUrl = "https://pagos-f2qf.onrender.com"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "VERIFICAR ESTRUCTURA REAL DE LA BASE DE DATOS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Obtener token
Write-Host "Obteniendo token..." -ForegroundColor Yellow
$loginBody = '{"email":"itmaster@rapicreditca.com","password":"R@pi_2025**"}'
$loginResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/auth/login" -Method Post -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token
$authHeaders = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

Write-Host "Token obtenido" -ForegroundColor Green
Write-Host ""

# Verificar endpoint test sin autenticación
Write-Host "1. Verificando endpoint test..." -ForegroundColor Yellow
try {
    $testResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/clientes/test" -Method Get
    Write-Host "   OK: Test endpoint funciona" -ForegroundColor Green
    Write-Host "   Total clientes: $($testResponse.total_clientes)" -ForegroundColor White
    Write-Host "   Sample: $($testResponse.sample | ConvertTo-Json -Compress)" -ForegroundColor Gray
} catch {
    Write-Host "   ERROR: Test endpoint falla" -ForegroundColor Red
    Write-Host "   Detalle: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Verificar endpoint GET con autenticación
Write-Host "2. Verificando endpoint GET con autenticación..." -ForegroundColor Yellow
try {
    $clientes = Invoke-RestMethod -Uri "$baseUrl/api/v1/clientes/" -Method Get -Headers $authHeaders
    Write-Host "   OK: GET funciona" -ForegroundColor Green
    Write-Host "   Total: $($clientes.total)" -ForegroundColor White
    Write-Host "   Página: $($clientes.page)" -ForegroundColor White
    Write-Host "   Límite: $($clientes.limit)" -ForegroundColor White
    
    if ($clientes.total -gt 0) {
        Write-Host "   Primer cliente:" -ForegroundColor Cyan
        $primerCliente = $clientes.clientes[0]
        Write-Host "     ID: $($primerCliente.id)" -ForegroundColor White
        Write-Host "     Nombre: $($primerCliente.nombres) $($primerCliente.apellidos)" -ForegroundColor White
        Write-Host "     Cedula: $($primerCliente.cedula)" -ForegroundColor White
        Write-Host "     Asesor ID: $($primerCliente.asesor_config_id)" -ForegroundColor White
    }
} catch {
    Write-Host "   ERROR: GET falla" -ForegroundColor Red
    Write-Host "   Detalle: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Verificar endpoint count
Write-Host "3. Verificando endpoint count..." -ForegroundColor Yellow
try {
    $count = Invoke-RestMethod -Uri "$baseUrl/api/v1/clientes/count" -Method Get -Headers $authHeaders
    Write-Host "   OK: Count funciona" -ForegroundColor Green
    Write-Host "   Total: $($count.total)" -ForegroundColor White
} catch {
    Write-Host "   ERROR: Count falla" -ForegroundColor Red
    Write-Host "   Detalle: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Verificar asesores disponibles
Write-Host "4. Verificando asesores disponibles..." -ForegroundColor Yellow
try {
    $asesores = Invoke-RestMethod -Uri "$baseUrl/api/v1/asesores/" -Method Get -Headers $authHeaders
    Write-Host "   OK: Asesores disponibles: $($asesores.total)" -ForegroundColor Green
    if ($asesores.total -gt 0) {
        Write-Host "   Primer asesor:" -ForegroundColor Cyan
        $primerAsesor = $asesores.items[0]
        Write-Host "     ID: $($primerAsesor.id)" -ForegroundColor White
        Write-Host "     Nombre: $($primerAsesor.nombre_completo)" -ForegroundColor White
        Write-Host "     Email: $($primerAsesor.email)" -ForegroundColor White
    }
} catch {
    Write-Host "   ERROR: No se pueden obtener asesores" -ForegroundColor Red
    Write-Host "   Detalle: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Verificar concesionarios disponibles
Write-Host "5. Verificando concesionarios disponibles..." -ForegroundColor Yellow
try {
    $concesionarios = Invoke-RestMethod -Uri "$baseUrl/api/v1/concesionarios/" -Method Get -Headers $authHeaders
    Write-Host "   OK: Concesionarios disponibles: $($concesionarios.total)" -ForegroundColor Green
    if ($concesionarios.total -gt 0) {
        Write-Host "   Primer concesionario:" -ForegroundColor Cyan
        $primerConcesionario = $concesionarios.items[0]
        Write-Host "     ID: $($primerConcesionario.id)" -ForegroundColor White
        Write-Host "     Nombre: $($primerConcesionario.nombre)" -ForegroundColor White
    }
} catch {
    Write-Host "   ERROR: No se pueden obtener concesionarios" -ForegroundColor Red
    Write-Host "   Detalle: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Verificar modelos de vehículos disponibles
Write-Host "6. Verificando modelos de vehículos disponibles..." -ForegroundColor Yellow
try {
    $modelos = Invoke-RestMethod -Uri "$baseUrl/api/v1/modelos-vehiculos/" -Method Get -Headers $authHeaders
    Write-Host "   OK: Modelos disponibles: $($modelos.total)" -ForegroundColor Green
    if ($modelos.total -gt 0) {
        Write-Host "   Primer modelo:" -ForegroundColor Cyan
        $primerModelo = $modelos.items[0]
        Write-Host "     ID: $($primerModelo.id)" -ForegroundColor White
        Write-Host "     Modelo: $($primerModelo.modelo)" -ForegroundColor White
    }
} catch {
    Write-Host "   ERROR: No se pueden obtener modelos" -ForegroundColor Red
    Write-Host "   Detalle: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "FIN DE VERIFICACION" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

