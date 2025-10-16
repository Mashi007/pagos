# ============================================================
# CREAR CLIENTE CON REINTENTOS AUTOMATICOS
# ============================================================

$baseUrl = "https://pagos-f2qf.onrender.com"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "CREAR CLIENTE CON REINTENTOS AUTOMATICOS" -ForegroundColor Cyan
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
    monto_financiado = 20000.00
    fecha_entrega = "2024-01-15"
    numero_amortizaciones = 36
    modalidad_pago = "MENSUAL"
    asesor_config_id = 1
    estado = "ACTIVO"
    activo = $true
    notas = "Cliente nuevo - Primer financiamiento"
} | ConvertTo-Json

Write-Host "Intentando crear cliente con reintentos..." -ForegroundColor Yellow
Write-Host ""

$maxIntentos = 10
$intento = 0
$exito = $false

while ($intento -lt $maxIntentos -and -not $exito) {
    $intento++
    Write-Host "Intento $intento/$maxIntentos..." -ForegroundColor Cyan
    
    try {
        $cliente = Invoke-RestMethod -Uri "$baseUrl/api/v1/clientes" -Method Post -Headers $authHeaders -Body $clienteData -TimeoutSec 30
        
        Write-Host "EXITO! Cliente creado" -ForegroundColor Green
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
        Write-Host "IMPORTANTE: Guarda este ID para crear prestamos: $($cliente.id)" -ForegroundColor Yellow
        Write-Host ""
        
        # Verificar que se creo
        Write-Host "Verificando que el cliente existe..." -ForegroundColor Yellow
        $clientes = Invoke-RestMethod -Uri "$baseUrl/api/v1/clientes/" -Method Get -Headers $authHeaders
        Write-Host "Total de clientes en el sistema: $($clientes.total)" -ForegroundColor Green
        Write-Host ""
        
        Write-Host "PROXIMO PASO: Crear prestamo para este cliente" -ForegroundColor Cyan
        Write-Host "Usa el ID del cliente: $($cliente.id)" -ForegroundColor Yellow
        
        $exito = $true
        
    } catch {
        $statusCode = if ($_.Exception.Response) { $_.Exception.Response.StatusCode.value__ } else { "N/A" }
        Write-Host "  FALLO: Status $statusCode" -ForegroundColor Red
        
        if ($statusCode -eq 503) {
            Write-Host "  Error 503: Base de datos temporalmente no disponible" -ForegroundColor Yellow
            Write-Host "  Esperando 30 segundos antes del siguiente intento..." -ForegroundColor Yellow
            Start-Sleep -Seconds 30
        } elseif ($statusCode -eq 400) {
            Write-Host "  Error 400: Datos invalidos" -ForegroundColor Red
            Write-Host "  Detalle: $($_.Exception.Message)" -ForegroundColor Red
            break
        } else {
            Write-Host "  Error inesperado: $($_.Exception.Message)" -ForegroundColor Red
            Start-Sleep -Seconds 10
        }
    }
    
    Write-Host ""
}

if (-not $exito) {
    Write-Host "FALLO: No se pudo crear el cliente después de $maxIntentos intentos" -ForegroundColor Red
    Write-Host "El problema puede ser:" -ForegroundColor Yellow
    Write-Host "  1. Base de datos temporalmente no disponible" -ForegroundColor Yellow
    Write-Host "  2. Problema de conectividad" -ForegroundColor Yellow
    Write-Host "  3. Error en el código del endpoint" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Recomendacion: Intentar mas tarde o revisar logs del servidor" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan

