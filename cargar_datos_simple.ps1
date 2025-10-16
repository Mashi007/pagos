$baseUrl = "https://pagos-f2qf.onrender.com"

Write-Host "Iniciando carga de datos..." -ForegroundColor Cyan

# Obtener token
$loginBody = '{"email":"itmaster@rapicreditca.com","password":"R@pi_2025**"}'
$loginResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/auth/login" -Method Post -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token
$authHeaders = @{ "Authorization" = "Bearer $token"; "Content-Type" = "application/json" }

Write-Host "Token obtenido" -ForegroundColor Green
Write-Host ""

# Crear asesor 1
Write-Host "Creando asesor 1..." -ForegroundColor Yellow
$ase1Body = '{"nombre":"Juan","apellido":"Perez","email":"juan.perez@rapicreditca.com","telefono":"809-555-0001","especialidad":"Ventas","activo":true}'
$ase1 = Invoke-RestMethod -Uri "$baseUrl/api/v1/asesores" -Method Post -Headers $authHeaders -Body $ase1Body
Write-Host "Asesor 1 creado: ID $($ase1.id)" -ForegroundColor Green

# Crear asesor 2
Write-Host "Creando asesor 2..." -ForegroundColor Yellow
$ase2Body = '{"nombre":"Maria","apellido":"Gonzalez","email":"maria.gonzalez@rapicreditca.com","telefono":"809-555-0002","especialidad":"Creditos","activo":true}'
$ase2 = Invoke-RestMethod -Uri "$baseUrl/api/v1/asesores" -Method Post -Headers $authHeaders -Body $ase2Body
Write-Host "Asesor 2 creado: ID $($ase2.id)" -ForegroundColor Green

Write-Host ""

# Crear cliente 1
Write-Host "Creando cliente 1..." -ForegroundColor Yellow
$cli1Body = "{`"cedula`":`"001-1234567-8`",`"nombres`":`"Roberto`",`"apellidos`":`"Sanchez Garcia`",`"telefono`":`"809-555-2001`",`"email`":`"roberto.sanchez@email.com`",`"direccion`":`"Calle Principal`",`"modelo_vehiculo`":`"Toyota Corolla 2023`",`"marca_vehiculo`":`"Toyota`",`"anio_vehiculo`":2023,`"color_vehiculo`":`"Blanco`",`"chasis`":`"TC2023-001-ABC`",`"motor`":`"1.8L-001`",`"concesionario`":`"AutoMax`",`"total_financiamiento`":25000.00,`"cuota_inicial`":5000.00,`"monto_financiado`":20000.00,`"fecha_entrega`":`"2024-01-15`",`"numero_amortizaciones`":36,`"modalidad_pago`":`"MENSUAL`",`"asesor_config_id`":$($ase1.id),`"estado`":`"ACTIVO`",`"activo`":true}"
$cli1 = Invoke-RestMethod -Uri "$baseUrl/api/v1/clientes" -Method Post -Headers $authHeaders -Body $cli1Body
Write-Host "Cliente 1 creado: ID $($cli1.id)" -ForegroundColor Green

Write-Host ""

# Crear prestamo 1
Write-Host "Creando prestamo 1..." -ForegroundColor Yellow
$pres1Body = "{`"cliente_id`":$($cli1.id),`"monto_prestamo`":20000.00,`"tasa_interes`":12.5,`"plazo_meses`":36,`"tipo_prestamo`":`"VEHICULAR`",`"estado`":`"APROBADO`",`"fecha_aprobacion`":`"2024-01-15`"}"
$pres1 = Invoke-RestMethod -Uri "$baseUrl/api/v1/prestamos/" -Method Post -Headers $authHeaders -Body $pres1Body
Write-Host "Prestamo 1 creado: ID $($pres1.id)" -ForegroundColor Green

Write-Host ""

# Crear pago 1
Write-Host "Registrando pago 1..." -ForegroundColor Yellow
$pago1Body = "{`"prestamo_id`":$($pres1.id),`"monto`":650.00,`"fecha_pago`":`"2024-02-15`",`"metodo_pago`":`"TRANSFERENCIA`",`"estado`":`"COMPLETADO`",`"referencia`":`"REF-001`"}"
$pago1 = Invoke-RestMethod -Uri "$baseUrl/api/v1/pagos/" -Method Post -Headers $authHeaders -Body $pago1Body
Write-Host "Pago 1 registrado: ID $($pago1.id)" -ForegroundColor Green

Write-Host ""
Write-Host "DATOS CARGADOS EXITOSAMENTE!" -ForegroundColor Green
Write-Host "Asesores: 2" -ForegroundColor White
Write-Host "Clientes: 1" -ForegroundColor White
Write-Host "Prestamos: 1" -ForegroundColor White
Write-Host "Pagos: 1" -ForegroundColor White

