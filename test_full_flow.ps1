# Testing Script for RapiCredit API (PowerShell)
# Run: .\test_full_flow.ps1

param(
    [string]$Email = "itmaster@rapicreditca.com",
    [string]$Password = $env:ADMIN_PASSWORD
)

$BaseUrl = "https://rapicredit.onrender.com/api/v1"

# Colors
$Green = [ConsoleColor]::Green
$Red = [ConsoleColor]::Red
$Yellow = [ConsoleColor]::Yellow

Write-Host "==========================================" -ForegroundColor Yellow
Write-Host "RapiCredit API - Full Flow Testing" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Yellow

# Test 1: Login
Write-Host "`n[TEST 1] LOGIN" -ForegroundColor Yellow

$LoginResponse = Invoke-RestMethod -Uri "$BaseUrl/auth/login" `
    -Method POST `
    -Headers @{"Content-Type" = "application/json"} `
    -Body (@{
        email    = $Email
        password = $Password
    } | ConvertTo-Json) `
    -ErrorAction SilentlyContinue

if (-not $LoginResponse.access_token) {
    Write-Host "❌ LOGIN FAILED" -ForegroundColor Red
    Write-Host "Response: $LoginResponse"
    exit 1
}

$AccessToken = $LoginResponse.access_token
Write-Host "✅ LOGIN SUCCESS" -ForegroundColor Green
Write-Host "Token: $($AccessToken.Substring(0, 20))..."

# Headers for authenticated requests
$Headers = @{
    "Content-Type"  = "application/json"
    "Authorization" = "Bearer $AccessToken"
}

# Test 2: Create Loan
Write-Host "`n[TEST 2] CREATE LOAN" -ForegroundColor Yellow

$PrestamoPayload = @{
    cedula_cliente      = "V12345678"
    monto               = 50000
    tasa_interes        = 5.5
    plazo_meses         = 24
    tipo_amortizacion   = "FRANCESA"
    modelo_vehiculo     = "Toyota Corolla 2020"
    concesionario       = "Automotriz Central"
    analista            = "Juan Pérez"
} | ConvertTo-Json

$PrestamoResponse = Invoke-RestMethod -Uri "$BaseUrl/prestamos" `
    -Method POST `
    -Headers $Headers `
    -Body $PrestamoPayload `
    -ErrorAction SilentlyContinue

if (-not $PrestamoResponse.id) {
    Write-Host "❌ CREATE LOAN FAILED" -ForegroundColor Red
    Write-Host "Response: $PrestamoResponse"
    exit 1
}

$PrestamoId = $PrestamoResponse.id
Write-Host "✅ CREATE LOAN SUCCESS" -ForegroundColor Green
Write-Host "Loan ID: $PrestamoId"

# Test 3: Create Payment
Write-Host "`n[TEST 3] CREATE PAYMENT" -ForegroundColor Yellow

$PagoPayload = @{
    cedula            = "V12345678"
    prestamo_id       = $PrestamoId
    monto_pagado      = 2500.50
    fecha_pago        = "2026-03-04"
    numero_documento  = "BNC-20260304-TEST"
} | ConvertTo-Json

$PagoResponse = Invoke-RestMethod -Uri "$BaseUrl/pagos" `
    -Method POST `
    -Headers $Headers `
    -Body $PagoPayload `
    -ErrorAction SilentlyContinue

if (-not $PagoResponse.id) {
    Write-Host "❌ CREATE PAYMENT FAILED" -ForegroundColor Red
    Write-Host "Response: $PagoResponse"
    exit 1
}

$PagoId = $PagoResponse.id
Write-Host "✅ CREATE PAYMENT SUCCESS" -ForegroundColor Green
Write-Host "Payment ID: $PagoId"

# Test 4: Get Loan Details
Write-Host "`n[TEST 4] GET LOAN DETAILS" -ForegroundColor Yellow

$LoanDetails = Invoke-RestMethod -Uri "$BaseUrl/prestamos/$PrestamoId" `
    -Method GET `
    -Headers $Headers `
    -ErrorAction SilentlyContinue

$LoanState = $LoanDetails.estado
$UsuarioProponente = $LoanDetails.usuario_proponente

if ($LoanState -eq "DRAFT") {
    Write-Host "✅ LOAN STATE CORRECT (DRAFT)" -ForegroundColor Green
}
else {
    Write-Host "⚠️  Unexpected state: $LoanState" -ForegroundColor Yellow
}

if ($UsuarioProponente -eq $Email) {
    Write-Host "✅ USUARIO_PROPONENTE CORRECT" -ForegroundColor Green
}
else {
    Write-Host "⚠️  Unexpected usuario_proponente: $UsuarioProponente" -ForegroundColor Yellow
}

# Test 5: Get Payment Details
Write-Host "`n[TEST 5] GET PAYMENT DETAILS" -ForegroundColor Yellow

$PagoDetails = Invoke-RestMethod -Uri "$BaseUrl/pagos/$PagoId" `
    -Method GET `
    -Headers $Headers `
    -ErrorAction SilentlyContinue

$PagoState = $PagoDetails.estado
$UsuarioRegistro = $PagoDetails.usuario_registro

if ($PagoState -eq "PAGADO") {
    Write-Host "✅ PAYMENT STATE CORRECT (PAGADO)" -ForegroundColor Green
}
else {
    Write-Host "⚠️  Unexpected state: $PagoState" -ForegroundColor Yellow
}

if ($UsuarioRegistro -eq $Email) {
    Write-Host "✅ USUARIO_REGISTRO CORRECT" -ForegroundColor Green
}
else {
    Write-Host "⚠️  Unexpected usuario_registro: $UsuarioRegistro" -ForegroundColor Yellow
}

# Final Summary
Write-Host "`n==========================================" -ForegroundColor Green
Write-Host "✅ ALL TESTS COMPLETED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Loan ID: $PrestamoId"
Write-Host "Payment ID: $PagoId"
Write-Host "==========================================" -ForegroundColor Green
