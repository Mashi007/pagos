# ============================================================
# ESPERAR DEPLOYMENT Y PROBAR AUTOMATICAMENTE
# ============================================================

$baseUrl = "https://pagos-f2qf.onrender.com"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "ESPERANDO DEPLOYMENT Y PROBANDO AUTOMATICAMENTE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$maxIntentos = 20
$intento = 0

while ($intento -lt $maxIntentos) {
    $intento++
    Write-Host "Intento $intento/$maxIntentos - Verificando deployment..." -ForegroundColor Yellow
    
    try {
        # Verificar si el servidor responde con el nuevo timestamp
        $rootResponse = Invoke-RestMethod -Uri "$baseUrl/" -Method Get
        
        if ($rootResponse.deploy_timestamp -eq "2025-10-16T10:30:00Z") {
            Write-Host "  Deployment anterior aún activo, esperando..." -ForegroundColor Yellow
            Start-Sleep -Seconds 30
            continue
        }
        
        Write-Host "  Nuevo deployment detectado!" -ForegroundColor Green
        Write-Host "  Timestamp: $($rootResponse.deploy_timestamp)" -ForegroundColor White
        
        # Probar endpoint de debug
        try {
            $debugResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/debug/cliente-model" -Method Get
            Write-Host "  Endpoints de debug disponibles!" -ForegroundColor Green
            break
        } catch {
            Write-Host "  Endpoints de debug aún no disponibles, esperando..." -ForegroundColor Yellow
            Start-Sleep -Seconds 30
            continue
        }
        
    } catch {
        Write-Host "  Error verificando servidor: $($_.Exception.Message)" -ForegroundColor Red
        Start-Sleep -Seconds 30
        continue
    }
}

if ($intento -eq $maxIntentos) {
    Write-Host ""
    Write-Host "TIMEOUT: El deployment no se completó en el tiempo esperado" -ForegroundColor Red
    Write-Host "Procediendo a probar con el endpoint actual..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PROBANDO CREACION DE CLIENTE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Obtener token
Write-Host "Obteniendo token..." -ForegroundColor Yellow
$loginBody = '{"email":"itmaster@rapicreditca.com","password":"R@pi_2025**"}'
try {
    $loginResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/auth/login" -Method Post -Body $loginBody -ContentType "application/json"
    $token = $loginResponse.access_token
    Write-Host "Token obtenido" -ForegroundColor Green
} catch {
    Write-Host "ERROR: No se pudo obtener token" -ForegroundColor Red
    exit 1
}

$authHeaders = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# Datos del cliente
$clienteData = @{
    cedula = "001-1234567-8"
    nombres = "Roberto"
    apellidos = "Sanchez Garcia"
    telefono = "809-555-2001"
    email = "roberto.sanchez@email.com"
    direccion = "Calle Principal #123, Santo Domingo"
    fecha_nacimiento = "1985-06-15"
    ocupacion = "Ingeniero"
    modelo_vehiculo = "Toyota Corolla 2023"
    marca_vehiculo = "Toyota"
    anio_vehiculo = 2023
    color_vehiculo = "Blanco"
    chasis = "TC2023-001-ABC"
    motor = "1.8L-001"
    concesionario = "AutoMax Santo Domingo"
    vendedor_concesionario = "Pedro Martinez"
    total_financiamiento = 25000.00
    cuota_inicial = 5000.00
    fecha_entrega = "2024-01-15"
    numero_amortizaciones = 36
    modalidad_pago = "MENSUAL"
    asesor_config_id = 1
    notas = "Cliente nuevo - Primer financiamiento"
} | ConvertTo-Json

Write-Host "Intentando crear cliente..." -ForegroundColor Yellow
Write-Host ""

$intentoCliente = 0
$maxIntentosCliente = 5
$exito = $false

while ($intentoCliente -lt $maxIntentosCliente -and -not $exito) {
    $intentoCliente++
    Write-Host "Intento $intentoCliente/$maxIntentosCliente de crear cliente..." -ForegroundColor Cyan
    
    try {
        $cliente = Invoke-RestMethod -Uri "$baseUrl/api/v1/clientes" -Method Post -Headers $authHeaders -Body $clienteData -TimeoutSec 30
        
        Write-Host ""
        Write-Host "🎉 EXITO! CLIENTE CREADO CORRECTAMENTE" -ForegroundColor Green
        Write-Host ""
        Write-Host "Datos del cliente creado:" -ForegroundColor Cyan
        Write-Host "  ID: $($cliente.id)" -ForegroundColor White
        Write-Host "  Nombre: $($cliente.nombres) $($cliente.apellidos)" -ForegroundColor White
        Write-Host "  Cedula: $($cliente.cedula)" -ForegroundColor White
        Write-Host "  Email: $($cliente.email)" -ForegroundColor White
        Write-Host "  Vehiculo: $($cliente.modelo_vehiculo)" -ForegroundColor White
        Write-Host "  Monto Financiado: $($cliente.monto_financiado)" -ForegroundColor White
        Write-Host "  Asesor ID: $($cliente.asesor_config_id)" -ForegroundColor White
        Write-Host ""
        Write-Host "✅ PROBLEMA RESUELTO - EL SISTEMA ESTA FUNCIONANDO" -ForegroundColor Green
        Write-Host ""
        Write-Host "PROXIMO PASO: Crear prestamo para este cliente" -ForegroundColor Cyan
        Write-Host "Usa el ID del cliente: $($cliente.id)" -ForegroundColor Yellow
        
        $exito = $true
        
    } catch {
        $statusCode = if ($_.Exception.Response) { $_.Exception.Response.StatusCode.value__ } else { "N/A" }
        Write-Host "  FALLO: Status $statusCode" -ForegroundColor Red
        
        if ($statusCode -eq 503) {
            Write-Host "  Error 503: Base de datos temporalmente no disponible" -ForegroundColor Yellow
            Write-Host "  Esperando 45 segundos..." -ForegroundColor Yellow
            Start-Sleep -Seconds 45
        } elseif ($statusCode -eq 400) {
            Write-Host "  Error 400: Datos invalidos" -ForegroundColor Red
            Write-Host "  Detalle: $($_.Exception.Message)" -ForegroundColor Red
            break
        } else {
            Write-Host "  Error inesperado: $($_.Exception.Message)" -ForegroundColor Red
            Start-Sleep -Seconds 30
        }
    }
    
    Write-Host ""
}

if (-not $exito) {
    Write-Host "❌ FALLO: No se pudo crear el cliente después de $maxIntentosCliente intentos" -ForegroundColor Red
    Write-Host ""
    Write-Host "PROBLEMAS IDENTIFICADOS:" -ForegroundColor Yellow
    Write-Host "  1. El endpoint POST clientes sigue dando 503" -ForegroundColor Yellow
    Write-Host "  2. La base de datos puede estar temporalmente no disponible" -ForegroundColor Yellow
    Write-Host "  3. Puede haber un problema más profundo en la configuración" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "RECOMENDACIONES:" -ForegroundColor Cyan
    Write-Host "  1. Revisar logs del servidor en Render" -ForegroundColor Cyan
    Write-Host "  2. Verificar estado de la base de datos PostgreSQL" -ForegroundColor Cyan
    Write-Host "  3. Considerar reiniciar el servicio en Render" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan

