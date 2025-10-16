# ============================================================
# DIAGNOSTICO PROFUNDO POST-DEPLOYMENT
# ============================================================

$baseUrl = "https://pagos-f2qf.onrender.com"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "DIAGNOSTICO PROFUNDO - IDENTIFICAR PROBLEMA RAIZ" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Esperar deployment
Write-Host "Esperando 60 segundos para deployment..." -ForegroundColor Yellow
Start-Sleep -Seconds 60

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

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PASO 1: VERIFICAR ESTRUCTURA DEL MODELO CLIENTE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

try {
    $modelInfo = Invoke-RestMethod -Uri "$baseUrl/api/v1/debug/cliente-model" -Method Get
    Write-Host "Status: $($modelInfo.status)" -ForegroundColor Green
    Write-Host "Tabla: $($modelInfo.table_name)" -ForegroundColor White
    Write-Host "Total columnas: $($modelInfo.total_columns)" -ForegroundColor White
    Write-Host ""
    Write-Host "Columnas del modelo:" -ForegroundColor Yellow
    foreach ($col in $modelInfo.columns) {
        $fkInfo = if ($col.foreign_keys.Count -gt 0) { " -> FK: $($col.foreign_keys -join ', ')" } else { "" }
        Write-Host "  - $($col.name) ($($col.type))$fkInfo" -ForegroundColor Gray
    }
} catch {
    Write-Host "ERROR: No se pudo obtener info del modelo" -ForegroundColor Red
    Write-Host "Detalle: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PASO 2: VERIFICAR ESTRUCTURA REAL DE LA BD" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

try {
    $dbInfo = Invoke-RestMethod -Uri "$baseUrl/api/v1/debug/cliente-db-structure" -Method Get
    Write-Host "Status: $($dbInfo.status)" -ForegroundColor Green
    Write-Host "Tabla: $($dbInfo.table)" -ForegroundColor White
    Write-Host "Total columnas: $($dbInfo.total_columns)" -ForegroundColor White
    Write-Host ""
    Write-Host "Columnas en la BD:" -ForegroundColor Yellow
    foreach ($col in $dbInfo.columns) {
        $nullableInfo = if ($col.nullable -eq "YES") { "NULL" } else { "NOT NULL" }
        Write-Host "  - $($col.name) ($($col.type)) $nullableInfo" -ForegroundColor Gray
    }
} catch {
    Write-Host "ERROR: No se pudo obtener info de la BD" -ForegroundColor Red
    Write-Host "Detalle: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PASO 3: PROBAR INSERCION CON DATOS MINIMOS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

try {
    $testInsert = Invoke-RestMethod -Uri "$baseUrl/api/v1/debug/test-insert" -Method Post -Headers $authHeaders
    Write-Host "Status: $($testInsert.status)" -ForegroundColor Green
    Write-Host "Mensaje: $($testInsert.message)" -ForegroundColor White
    if ($testInsert.test_id) {
        Write-Host "Test ID: $($testInsert.test_id)" -ForegroundColor White
    }
} catch {
    Write-Host "ERROR: La inserción de prueba falló" -ForegroundColor Red
    Write-Host "Detalle: $($_.Exception.Message)" -ForegroundColor Red
    
    if ($_.Exception.Response) {
        try {
            $errorStream = $_.Exception.Response.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($errorStream)
            $errorBody = $reader.ReadToEnd()
            Write-Host "Error Body:" -ForegroundColor Red
            Write-Host $errorBody -ForegroundColor Red
        } catch {
            Write-Host "No se pudo obtener detalles adicionales" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PASO 4: VALIDAR SCHEMA CLIENTECREATE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

try {
    $testSchema = Invoke-RestMethod -Uri "$baseUrl/api/v1/debug/test-create-schema" -Method Post -Headers $authHeaders
    Write-Host "Status: $($testSchema.status)" -ForegroundColor Green
    Write-Host "Mensaje: $($testSchema.message)" -ForegroundColor White
    Write-Host ""
    Write-Host "Campos originales: $($testSchema.original_keys.Count)" -ForegroundColor Yellow
    Write-Host "Campos filtrados: $($testSchema.filtered_keys.Count)" -ForegroundColor Green
    Write-Host "Campos removidos: $($testSchema.removed_keys.Count)" -ForegroundColor Red
    
    if ($testSchema.removed_keys.Count -gt 0) {
        Write-Host ""
        Write-Host "CAMPOS REMOVIDOS (NO EXISTEN EN MODELO):" -ForegroundColor Red
        foreach ($key in $testSchema.removed_keys) {
            Write-Host "  - $key" -ForegroundColor Red
        }
    }
    
    Write-Host ""
    Write-Host "Datos filtrados para inserción:" -ForegroundColor Cyan
    $testSchema.data | ConvertTo-Json -Depth 10 | Write-Host -ForegroundColor Gray
    
} catch {
    Write-Host "ERROR: La validación del schema falló" -ForegroundColor Red
    Write-Host "Detalle: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PASO 5: INTENTAR CREAR CLIENTE REAL" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$clienteData = @{
    cedula = "001-1234567-8"
    nombres = "Roberto"
    apellidos = "Sanchez Garcia"
    telefono = "809-555-2001"
    email = "roberto.sanchez@email.com"
    direccion = "Calle Principal #123"
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
try {
    $cliente = Invoke-RestMethod -Uri "$baseUrl/api/v1/clientes" -Method Post -Headers $authHeaders -Body $clienteData
    
    Write-Host "EXITO! Cliente creado" -ForegroundColor Green
    Write-Host ""
    Write-Host "ID: $($cliente.id)" -ForegroundColor White
    Write-Host "Nombre: $($cliente.nombres) $($cliente.apellidos)" -ForegroundColor White
    Write-Host "Cedula: $($cliente.cedula)" -ForegroundColor White
    Write-Host "Email: $($cliente.email)" -ForegroundColor White
    
} catch {
    Write-Host "ERROR: No se pudo crear el cliente" -ForegroundColor Red
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    Write-Host "Detalle: $($_.Exception.Message)" -ForegroundColor Red
    
    if ($_.Exception.Response) {
        try {
            $errorStream = $_.Exception.Response.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($errorStream)
            $errorBody = $reader.ReadToEnd()
            Write-Host ""
            Write-Host "ERROR COMPLETO:" -ForegroundColor Red
            Write-Host $errorBody -ForegroundColor Red
        } catch {
            Write-Host "No se pudo obtener detalles adicionales" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "FIN DEL DIAGNOSTICO PROFUNDO" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

