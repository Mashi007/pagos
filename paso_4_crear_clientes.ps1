# ============================================================
# PASO 4: CREAR CLIENTES
# ESTE ES EL PASO MAS IMPORTANTE
# Los clientes son la base del sistema de financiamiento
# ============================================================

$baseUrl = "https://pagos-f2qf.onrender.com"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PASO 4: CREAR CLIENTES" -ForegroundColor Cyan
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
# IMPORTANTE: Usa IDs reales de asesores que creaste en paso_1
$clientes = @(
    @{
        cedula = "001-1234567-8"
        nombres = "Roberto"
        apellidos = "Sánchez García"
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
        vendedor_concesionario = "Pedro Martínez"
        
        # Datos del financiamiento
        total_financiamiento = 25000.00
        cuota_inicial = 5000.00
        monto_financiado = 20000.00
        fecha_entrega = "2024-01-15"
        numero_amortizaciones = 36
        modalidad_pago = "MENSUAL"
        
        # Asignación (IMPORTANTE: Usa un ID real de asesor)
        asesor_config_id = 1  # MODIFICA ESTO CON UN ID REAL
        
        # Estado
        estado = "ACTIVO"
        activo = $true
        notas = "Cliente nuevo - Primer financiamiento"
    },
    @{
        cedula = "002-2345678-9"
        nombres = "Laura"
        apellidos = "Martínez Pérez"
        telefono = "809-555-2002"
        email = "laura.martinez@email.com"
        direccion = "Av. Independencia #456, Santo Domingo"
        fecha_nacimiento = "1990-03-22"
        ocupacion = "Contadora"
        
        modelo_vehiculo = "Honda Civic 2023"
        marca_vehiculo = "Honda"
        anio_vehiculo = 2023
        color_vehiculo = "Gris"
        chasis = "HC2023-002-XYZ"
        motor = "2.0L-002"
        
        concesionario = "Vehículos Premium"
        vendedor_concesionario = "Ana López"
        
        total_financiamiento = 28000.00
        cuota_inicial = 7000.00
        monto_financiado = 21000.00
        fecha_entrega = "2024-02-01"
        numero_amortizaciones = 48
        modalidad_pago = "MENSUAL"
        
        asesor_config_id = 2  # MODIFICA ESTO CON UN ID REAL
        
        estado = "ACTIVO"
        activo = $true
        notas = "Cliente con buen historial crediticio"
    },
    @{
        cedula = "003-3456789-0"
        nombres = "Miguel"
        apellidos = "Rodríguez Castro"
        telefono = "809-555-2003"
        email = "miguel.rodriguez@email.com"
        direccion = "Calle El Sol #789, Santiago"
        fecha_nacimiento = "1988-11-08"
        ocupacion = "Comerciante"
        
        modelo_vehiculo = "Nissan Sentra 2024"
        marca_vehiculo = "Nissan"
        anio_vehiculo = 2024
        color_vehiculo = "Negro"
        chasis = "NS2024-003-DEF"
        motor = "1.6L-003"
        
        concesionario = "Concesionario La Estrella"
        vendedor_concesionario = "Luis Fernández"
        
        total_financiamiento = 22000.00
        cuota_inicial = 4000.00
        monto_financiado = 18000.00
        fecha_entrega = "2024-01-20"
        numero_amortizaciones = 36
        modalidad_pago = "MENSUAL"
        
        asesor_config_id = 3  # MODIFICA ESTO CON UN ID REAL
        
        estado = "ACTIVO"
        activo = $true
        notas = "Cliente referido"
    }
)

Write-Host "INGRESANDO CLIENTES..." -ForegroundColor Yellow
Write-Host ""
Write-Host "IMPORTANTE: Verifica que los IDs de asesores sean correctos" -ForegroundColor Red
Write-Host ""

$clientesCreados = @()

foreach ($cliente in $clientes) {
    Write-Host "Creando cliente: $($cliente.nombres) $($cliente.apellidos)..." -ForegroundColor Cyan
    
    try {
        $clienteBody = $cliente | ConvertTo-Json
        $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/clientes/" -Method Post -Headers $authHeaders -Body $clienteBody -TimeoutSec 15
        
        Write-Host "  EXITO: Cliente creado con ID: $($response.id)" -ForegroundColor Green
        $clientesCreados += $response
        
    } catch {
        Write-Host "  ERROR: No se pudo crear el cliente" -ForegroundColor Red
        Write-Host "  Detalles: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host ""
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "RESUMEN" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Total de clientes creados: $($clientesCreados.Count)" -ForegroundColor Green
Write-Host ""

if ($clientesCreados.Count -gt 0) {
    Write-Host "IDs de clientes creados (guarda estos IDs):" -ForegroundColor Yellow
    foreach ($cli in $clientesCreados) {
        Write-Host "  ID: $($cli.id) - $($cli.nombres) $($cli.apellidos) - Cedula: $($cli.cedula)" -ForegroundColor White
    }
    Write-Host ""
    Write-Host "PROXIMO PASO: Ejecutar paso_5_crear_prestamos.ps1" -ForegroundColor Cyan
}

