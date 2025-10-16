# ============================================================
# PASO MANUAL 2: CREAR UN CLIENTE
# ============================================================

$baseUrl = "https://pagos-f2qf.onrender.com"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PASO 2: CREAR UN CLIENTE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Obtener token
Write-Host "Obteniendo token..." -ForegroundColor Yellow
$loginBody = '{"email":"itmaster@rapicreditca.com","password":"R@pi_2025**"}'
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

# Crear cliente
Write-Host "Creando cliente..." -ForegroundColor Yellow
Write-Host "Nombre: Roberto Sanchez Garcia" -ForegroundColor White
Write-Host "Cedula: 001-1234567-8" -ForegroundColor White
Write-Host "Vehiculo: Toyota Corolla 2023" -ForegroundColor White
Write-Host "Asesor ID: 1" -ForegroundColor White
Write-Host ""

$clienteBody = @{
    cedula = "001-1234567-8"
    nombres = "Roberto"
    apellidos = "Sanchez Garcia"
    telefono = "809-555-2001"
    email = "roberto.sanchez@email.com"
    direccion = "Calle Principal #123, Santo Domingo"
    fecha_nacimiento = "1985-06-15"
    ocupacion = "Ingeniero"
    
    # Datos del vehículo
    modelo_vehiculo = "Toyota Corolla 2023"
    marca_vehiculo = "Toyota"
    anio_vehiculo = 2023
    color_vehiculo = "Blanco"
    chasis = "TC2023-001-ABC"
    motor = "1.8L-001"
    
    # Datos del concesionario
    concesionario = "AutoMax Santo Domingo"
    vendedor_concesionario = "Pedro Martinez"
    
    # Datos del financiamiento
    total_financiamiento = 25000.00
    cuota_inicial = 5000.00
    monto_financiado = 20000.00
    fecha_entrega = "2024-01-15"
    numero_amortizaciones = 36
    modalidad_pago = "MENSUAL"
    
    # Asignación (usando el ID del asesor creado)
    asesor_config_id = 1
    
    # Estado
    estado = "ACTIVO"
    activo = $true
    notas = "Cliente nuevo - Primer financiamiento"
} | ConvertTo-Json

Write-Host "Enviando request a: $baseUrl/api/v1/clientes" -ForegroundColor Gray
Write-Host ""

try {
    $cliente = Invoke-RestMethod -Uri "$baseUrl/api/v1/clientes" -Method Post -Headers $authHeaders -Body $clienteBody
    
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
    
    Write-Host "PROXIMO PASO: Ejecutar paso_manual_3_crear_prestamo.ps1" -ForegroundColor Cyan
    Write-Host "Usa el ID del cliente: $($cliente.id)" -ForegroundColor Yellow
    
} catch {
    Write-Host "ERROR: No se pudo crear el cliente" -ForegroundColor Red
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

