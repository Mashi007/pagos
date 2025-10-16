# ============================================================
# PASO MANUAL 1: CREAR UN ASESOR
# ============================================================

# ============================================================
# CONFIGURACION - Cambiar estas variables según tu entorno
# ============================================================
$baseUrl = $env:API_BASE_URL
if (-not $baseUrl) {
    $baseUrl = "https://pagos-f2qf.onrender.com"
}

$adminEmail = $env:ADMIN_EMAIL
if (-not $adminEmail) {
    $adminEmail = "itmaster@rapicreditca.com"
}

$adminPassword = $env:ADMIN_PASSWORD
if (-not $adminPassword) {
    Write-Host "ERROR: Variable ADMIN_PASSWORD no configurada" -ForegroundColor Red
    Write-Host "Configura la variable de entorno o ingresa la contraseña:" -ForegroundColor Yellow
    $adminPassword = Read-Host "Contraseña del administrador" -AsSecureString
    $adminPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($adminPassword))
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PASO 1: CREAR UN ASESOR" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Obtener token
Write-Host "Obteniendo token..." -ForegroundColor Yellow
$loginBody = @{
    email = $adminEmail
    password = $adminPassword
} | ConvertTo-Json
try {
    $loginResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/auth/login" -Method Post -Body $loginBody -ContentType "application/json"
    $token = $loginResponse.access_token
    Write-Host "OK: Token obtenido" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "ERROR: No se pudo obtener token" -ForegroundColor Red
    exit 1
}

$authHeaders = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# Crear asesor
Write-Host "Creando asesor..." -ForegroundColor Yellow
Write-Host "Nombre: Juan Perez" -ForegroundColor White
Write-Host "Email: juan.perez@rapicreditca.com" -ForegroundColor White
Write-Host ""

$asesorBody = @{
    nombre = "JUAN PEREZ"
} | ConvertTo-Json

Write-Host "Enviando request a: $baseUrl/api/v1/asesores" -ForegroundColor Gray
Write-Host ""

try {
    $asesor = Invoke-RestMethod -Uri "$baseUrl/api/v1/asesores" -Method Post -Headers $authHeaders -Body $asesorBody
    
    Write-Host "EXITO! Asesor creado" -ForegroundColor Green
    Write-Host ""
    Write-Host "Datos del asesor creado:" -ForegroundColor Cyan
    Write-Host "  ID: $($asesor.id)" -ForegroundColor White
    Write-Host "  Nombre: $($asesor.nombre)" -ForegroundColor White
    Write-Host ""
    Write-Host "IMPORTANTE: Guarda este ID para crear clientes: $($asesor.id)" -ForegroundColor Yellow
    Write-Host ""
    
    # Verificar que se creo
    Write-Host "Verificando que el asesor existe..." -ForegroundColor Yellow
    $asesores = Invoke-RestMethod -Uri "$baseUrl/api/v1/asesores/" -Method Get -Headers $authHeaders
    Write-Host "Total de asesores en el sistema: $($asesores.total)" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "PROXIMO PASO: Ejecutar paso_manual_2_crear_cliente.ps1" -ForegroundColor Cyan
    Write-Host "Usa el ID del asesor: $($asesor.id)" -ForegroundColor Yellow
    
} catch {
    Write-Host "ERROR: No se pudo crear el asesor" -ForegroundColor Red
    Write-Host ""
    Write-Host "Detalles del error:" -ForegroundColor Yellow
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    
    if ($_.Exception.Response) {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Host "Codigo de estado HTTP: $statusCode" -ForegroundColor Red
        
        if ($statusCode -eq 405) {
            Write-Host "Error 405: Metodo no permitido" -ForegroundColor Red
            Write-Host "La ruta o el metodo POST pueden estar incorrectos" -ForegroundColor Yellow
        } elseif ($statusCode -eq 422) {
            Write-Host "Error 422: Datos invalidos" -ForegroundColor Red
            Write-Host "Revisa que los datos cumplan con el formato requerido" -ForegroundColor Yellow
        } elseif ($statusCode -eq 401) {
            Write-Host "Error 401: No autorizado" -ForegroundColor Red
            Write-Host "El token puede haber expirado" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan

