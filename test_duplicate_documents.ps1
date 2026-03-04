# Test: Rechazo de Documentos Duplicados
# Script PowerShell completo para validar la funcionalidad

function Log-Test {
    param([string]$Phase, [string]$Message)
    Write-Host "[$Phase] TEST: $Message" -ForegroundColor Cyan
}

function Log-Success {
    param([string]$Message)
    Write-Host "[+] $Message" -ForegroundColor Green
}

function Log-Error {
    param([string]$Message)
    Write-Host "[-] ERROR: $Message" -ForegroundColor Red
}

function Log-Info {
    param([string]$Message)
    Write-Host "[*] $Message" -ForegroundColor Yellow
}

# === SETUP: Autenticacion ===
Write-Host ""
Write-Host "====== SETUP: Autenticacion ======" -ForegroundColor Cyan

$LoginResponse = Invoke-RestMethod -Uri "https://pagos-backend-ov5f.onrender.com/api/v1/auth/login" `
    -Method POST `
    -Body (@{
        email    = "itmaster@rapicreditca.com"
        password = "Itmaster@2024"
    } | ConvertTo-Json) `
    -ContentType "application/json"

$Token = $LoginResponse.access_token
$Headers = @{ "Authorization" = "Bearer $Token" }

Log-Success "Autenticado"

# === CREAR CLIENTE Y PRESTAMO ===
Log-Test "SETUP" "Crear cliente para pruebas"

$Timestamp = Get-Date -Format "yyyyMMddHHmmss"
$RandomId = Get-Random -Minimum 1000 -Maximum 9999
$ClienteCedula = "V" + $Timestamp.Substring(8)
$ClienteNombres = "Test_Dup_$RandomId"

$ClienteResponse = Invoke-RestMethod -Uri "https://pagos-backend-ov5f.onrender.com/api/v1/clientes" `
    -Method POST `
    -Headers $Headers `
    -Body (@{
        cedula           = $ClienteCedula
        nombres          = $ClienteNombres
        apellidos        = "Test"
        direccion        = "Calle Test"
        fecha_nacimiento = "1990-01-01"
        ocupacion        = "Test"
        usuario_registro = "itmaster@rapicreditca.com"
        notas            = "Cliente para test duplicados"
    } | ConvertTo-Json) `
    -ContentType "application/json"

$ClienteId = $ClienteResponse.id
Log-Success "Cliente creado: $ClienteCedula"

# Crear prestamo
$PrestamoResponse = Invoke-RestMethod -Uri "https://pagos-backend-ov5f.onrender.com/api/v1/prestamos" `
    -Method POST `
    -Headers $Headers `
    -Body (@{
        cliente_id              = $ClienteId
        total_financiamiento    = 36000
        numero_cuotas           = 3
        usuario_proponente      = "itmaster@rapicreditca.com"
        usuario_aprobacion      = "itmaster@rapicreditca.com"
    } | ConvertTo-Json) `
    -ContentType "application/json"

$PrestamoId = $PrestamoResponse.id
Log-Success "Prestamo creado: $PrestamoId"

Write-Host ""
Write-Host "====== TEST 1: Pago Individual - Documento Original ======" -ForegroundColor Cyan

$PagoOriginal = Invoke-RestMethod -Uri "https://pagos-backend-ov5f.onrender.com/api/v1/pagos" `
    -Method POST `
    -Headers $Headers `
    -Body (@{
        cedula_cliente   = $ClienteCedula
        prestamo_id      = $PrestamoId
        monto_pagado     = 12000
        fecha_pago       = "2026-03-05"
        numero_documento = "DOC_ORIGINAL_001"
    } | ConvertTo-Json) `
    -ContentType "application/json"

$PagoOriginalId = $PagoOriginal.id
Log-Success "Pago original creado: ID=$PagoOriginalId, Doc=DOC_ORIGINAL_001"

Write-Host ""
Write-Host "====== TEST 2: Pago Individual - Documento DUPLICADO ======" -ForegroundColor Cyan

try {
    $PagoDuplicado = Invoke-RestMethod -Uri "https://pagos-backend-ov5f.onrender.com/api/v1/pagos" `
        -Method POST `
        -Headers $Headers `
        -Body (@{
            cedula_cliente   = $ClienteCedula
            prestamo_id      = $PrestamoId
            monto_pagado     = 8000
            fecha_pago       = "2026-03-10"
            numero_documento = "DOC_ORIGINAL_001"
        } | ConvertTo-Json) `
        -ContentType "application/json" `
        -ErrorAction Stop

    Log-Error "FALLO - El pago duplicado fue aceptado. No deberia serlo."
    $Success2 = $false
}
catch {
    $StatusCode = $_.Exception.Response.StatusCode
    if ($StatusCode -eq 409) {
        Log-Success "Pago duplicado rechazado con 409 CONFLICT"
        $Success2 = $true
    }
    else {
        Log-Error "Error inesperado. StatusCode: $StatusCode"
        $Success2 = $false
    }
}

Write-Host ""
Write-Host "====== TEST 3: Carga Masiva - Doc NUEVO + DUPLICADO en BD ======" -ForegroundColor Cyan

$ExcelPath = "$env:TEMP\test_dup_db_$Timestamp.xlsx"
$CsvPath = "$env:TEMP\test_dup_db_$Timestamp.csv"

$CsvContent = @"
cedula,prestamo_id,fecha_pago,monto_pagado,numero_documento
$ClienteCedula,$PrestamoId,2026-03-10,8000,DOC_NEW_001
$ClienteCedula,$PrestamoId,2026-03-15,5000,DOC_ORIGINAL_001
"@

$CsvContent | Out-File $CsvPath -Encoding UTF8

# Convertir CSV a XLSX
$Excel = New-Object -ComObject Excel.Application
$Excel.Visible = $false
$Workbook = $Excel.Workbooks.Open($CsvPath)
$Workbook.SaveAs($ExcelPath, 51)
$Workbook.Close()
$Excel.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($Excel) | Out-Null

Log-Info "Archivo Excel creado"

try {
    $UploadResponse = Invoke-RestMethod -Uri "https://pagos-backend-ov5f.onrender.com/api/v1/pagos/upload" `
        -Method POST `
        -Headers $Headers `
        -Form @{file = Get-Item $ExcelPath } `
        -ContentType "multipart/form-data"

    Log-Info "Registros creados: $($UploadResponse.registros_creados)"
    Log-Info "Registros con error: $($UploadResponse.registros_con_error)"

    if ($UploadResponse.registros_creados -eq 1) {
        Log-Success "Solo 1 pago creado (DOC_NEW_001)"
        $Success3a = $true
    }
    else {
        Log-Error "Se esperaba 1, se crearon: $($UploadResponse.registros_creados)"
        $Success3a = $false
    }

    if ($UploadResponse.registros_con_error -eq 1) {
        Log-Success "1 pago rechazado (duplicado)"
        $Success3b = $true
    }
    else {
        Log-Error "Se esperaba 1 rechazado, se rechazaron: $($UploadResponse.registros_con_error)"
        $Success3b = $false
    }
}
catch {
    Log-Error "Error en la carga: $_"
    $Success3a = $false
    $Success3b = $false
}

Write-Host ""
Write-Host "====== TEST 4: Carga Masiva - Documentos DUPLICADOS en ARCHIVO ======" -ForegroundColor Cyan

$ExcelPath2 = "$env:TEMP\test_dup_internal_$Timestamp.xlsx"
$CsvPath2 = "$env:TEMP\test_dup_internal_$Timestamp.csv"

$CsvContent2 = @"
cedula,prestamo_id,fecha_pago,monto_pagado,numero_documento
$ClienteCedula,$PrestamoId,2026-03-10,8000,DOC_INT_001
$ClienteCedula,$PrestamoId,2026-03-15,5000,DOC_INT_002
$ClienteCedula,$PrestamoId,2026-03-20,5000,DOC_INT_001
"@

$CsvContent2 | Out-File $CsvPath2 -Encoding UTF8

# Convertir a XLSX
$Excel2 = New-Object -ComObject Excel.Application
$Excel2.Visible = $false
$Workbook2 = $Excel2.Workbooks.Open($CsvPath2)
$Workbook2.SaveAs($ExcelPath2, 51)
$Workbook2.Close()
$Excel2.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($Excel2) | Out-Null

Log-Info "Archivo Excel creado"

try {
    $UploadResponse2 = Invoke-RestMethod -Uri "https://pagos-backend-ov5f.onrender.com/api/v1/pagos/upload" `
        -Method POST `
        -Headers $Headers `
        -Form @{file = Get-Item $ExcelPath2 } `
        -ContentType "multipart/form-data"

    Log-Info "Registros creados: $($UploadResponse2.registros_creados)"
    Log-Info "Registros con error: $($UploadResponse2.registros_con_error)"

    if ($UploadResponse2.registros_creados -eq 2) {
        Log-Success "2 pagos creados (documentos unicos)"
        $Success4a = $true
    }
    else {
        Log-Error "Se esperaba 2, se crearon: $($UploadResponse2.registros_creados)"
        $Success4a = $false
    }

    if ($UploadResponse2.registros_con_error -eq 1) {
        Log-Success "1 pago rechazado (duplicado en archivo)"
        $Success4b = $true
    }
    else {
        Log-Error "Se esperaba 1 rechazado, se rechazaron: $($UploadResponse2.registros_con_error)"
        $Success4b = $false
    }
}
catch {
    Log-Error "Error en la carga: $_"
    $Success4a = $false
    $Success4b = $false
}

# === CLEANUP ===
Remove-Item $CsvPath -Force -ErrorAction SilentlyContinue
Remove-Item $ExcelPath -Force -ErrorAction SilentlyContinue
Remove-Item $CsvPath2 -Force -ErrorAction SilentlyContinue
Remove-Item $ExcelPath2 -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "====== RESUMEN DE RESULTADOS ======" -ForegroundColor Cyan
Log-Success "TEST 1: Pago original aceptado"
if ($Success2) { Log-Success "TEST 2: Documento duplicado rechazado con 409" } else { Log-Error "TEST 2: FALLO" }
if ($Success3a -and $Success3b) { Log-Success "TEST 3: Carga masiva rechaza duplicado en BD" } else { Log-Error "TEST 3: FALLO" }
if ($Success4a -and $Success4b) { Log-Success "TEST 4: Carga masiva rechaza duplicado en archivo" } else { Log-Error "TEST 4: FALLO" }

Write-Host ""
if ($Success2 -and $Success3a -and $Success3b -and $Success4a -and $Success4b) {
    Write-Host "CONCLUSIÓN: Todos los tests pasaron!" -ForegroundColor Green
}
else {
    Write-Host "CONCLUSIÓN: Algunos tests fallaron" -ForegroundColor Red
}
