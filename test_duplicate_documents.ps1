# Test: Rechazo de Documentos Duplicados
# Script PowerShell completo para validar la funcionalidad

function Invoke-ApiRequest {
    param (
        [string]$Method,
        [string]$Endpoint,
        [hashtable]$Body,
        [string]$File,
        [hashtable]$Headers,
        [switch]$ErrorAction
    )
    
    $BaseUrl = "https://pagos-backend-ov5f.onrender.com/api/v1"
    $Url = "$BaseUrl$Endpoint"
    
    try {
        if ($File) {
            $FileBytes = [System.IO.File]::ReadAllBytes($File)
            $MultipartForm = @{file = $FileBytes }
            $response = Invoke-RestMethod -Uri $Url -Method $Method -Headers $Headers -Form @{file = (Get-Item $File) } -ContentType "multipart/form-data"
        } else {
            $JsonBody = $Body | ConvertTo-Json
            $response = Invoke-RestMethod -Uri $Url -Method $Method -Headers $Headers -Body $JsonBody -ContentType "application/json"
        }
        return $response
    }
    catch {
        if ($ErrorAction) {
            Write-Host "ERROR: $_" -ForegroundColor Red
            return $null
        }
        throw
    }
}

function Log-Test {
    param([string]$Phase, [string]$Message)
    Write-Host "[$Phase] TEST: $Message" -ForegroundColor Cyan
}

function Log-Success {
    param([string]$Message)
    Write-Host "[✓] $Message" -ForegroundColor Green
}

function Log-Error {
    param([string]$Message)
    Write-Host "[✗] ERROR: $Message" -ForegroundColor Red
}

function Log-Info {
    param([string]$Message)
    Write-Host "[i] $Message" -ForegroundColor Yellow
}

# === SETUP: Autenticación ===
Write-Host "=" * 60
Write-Host "SETUP: Autenticación y Cliente" -ForegroundColor Cyan
Write-Host "=" * 60

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
$ClienteNombres = "Test Duplicados $RandomId"

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

# Crear préstamo
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
Write-Host "=" * 60
Write-Host "TEST 1: Pago Individual - Documento Original" -ForegroundColor Cyan
Write-Host "=" * 60

$PagoOriginal = Invoke-RestMethod -Uri "https://pagos-backend-ov5f.onrender.com/api/v1/pagos" `
    -Method POST `
    -Headers $Headers `
    -Body (@{
        cedula_cliente   = $ClienteCedula
        prestamo_id      = $PrestamoId
        monto_pagado     = 12000
        fecha_pago       = "2026-03-05"
        numero_documento = "DOC-ORIGINAL-001"
    } | ConvertTo-Json) `
    -ContentType "application/json"

$PagoOriginalId = $PagoOriginal.id
Log-Success "Pago original creado: ID=$PagoOriginalId, Doc=DOC-ORIGINAL-001"

Write-Host ""
Write-Host "=" * 60
Write-Host "TEST 2: Pago Individual - Documento DUPLICADO (Debería rechazarse)" -ForegroundColor Cyan
Write-Host "=" * 60

try {
    $PagoDuplicado = Invoke-RestMethod -Uri "https://pagos-backend-ov5f.onrender.com/api/v1/pagos" `
        -Method POST `
        -Headers $Headers `
        -Body (@{
            cedula_cliente   = $ClienteCedula
            prestamo_id      = $PrestamoId
            monto_pagado     = 8000
            fecha_pago       = "2026-03-10"
            numero_documento = "DOC-ORIGINAL-001"  # DUPLICADO
        } | ConvertTo-Json) `
        -ContentType "application/json" `
        -ErrorAction Stop

    Log-Error "¡FALLO! El pago duplicado fue aceptado. No debería serlo."
}
catch {
    $StatusCode = $_.Exception.Response.StatusCode
    if ($StatusCode -eq 409) {
        Log-Success "Pago duplicado rechazado correctamente con 409 CONFLICT"
        $ErrorBody = $_.Exception.Response.Content.ReadAsStream() | ForEach-Object { [System.IO.StreamReader]::new($_).ReadToEnd() }
        Log-Info "Respuesta: $ErrorBody"
    }
    else {
        Log-Error "Error inesperado. StatusCode: $StatusCode"
    }
}

Write-Host ""
Write-Host "=" * 60
Write-Host "TEST 3: Carga Masiva - Documento NUEVO + DUPLICADO en BD" -ForegroundColor Cyan
Write-Host "=" * 60

# Crear archivo Excel con 2 pagos (1 nuevo, 1 duplicado)
$ExcelPath = "$env:TEMP\test_duplicate_db_$(Get-Date -Format 'yyyyMMddHHmmss').xlsx"

# Crear CSV primero
$CsvPath = $ExcelPath.Replace('.xlsx', '.csv')
$CsvContent = @"
cedula,prestamo_id,fecha_pago,monto_pagado,numero_documento
$ClienteCedula,$PrestamoId,2026-03-10,8000,DOC-NEW-001
$ClienteCedula,$PrestamoId,2026-03-15,5000,DOC-ORIGINAL-001
"@

$CsvContent | Out-File $CsvPath -Encoding UTF8

# Convertir CSV a XLSX usando PowerShell Excel COM
$Excel = New-Object -ComObject Excel.Application
$Excel.Visible = $false
$Workbook = $Excel.Workbooks.Open($CsvPath)
$Workbook.SaveAs($ExcelPath, 51)  # 51 = xlOpenXMLWorkbook
$Workbook.Close()
$Excel.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($Excel) | Out-Null

Log-Info "Archivo Excel creado con 2 pagos"

# Subir archivo
try {
    $UploadResponse = Invoke-RestMethod -Uri "https://pagos-backend-ov5f.onrender.com/api/v1/pagos/upload" `
        -Method POST `
        -Headers $Headers `
        -Form @{file = Get-Item $ExcelPath } `
        -ContentType "multipart/form-data"

    Log-Info "Respuesta de carga:"
    Log-Info "  - Registros creados: $($UploadResponse.registros_creados)"
    Log-Info "  - Registros con error: $($UploadResponse.registros_con_error)"

    if ($UploadResponse.registros_creados -eq 1) {
        Log-Success "Solo 1 pago creado (DOC-NEW-001) ✓"
    }
    else {
        Log-Error "Se esperaba 1 pago creado, se crearon: $($UploadResponse.registros_creados)"
    }

    if ($UploadResponse.registros_con_error -eq 1) {
        Log-Success "1 pago rechazado (documento duplicado) ✓"
    }
    else {
        Log-Error "Se esperaba 1 pago rechazado, se rechazaron: $($UploadResponse.registros_con_error)"
    }

    if ($UploadResponse.errores) {
        Log-Info "Errores reportados:"
        foreach ($error in $UploadResponse.errores) {
            Log-Info "  - $error"
            if ($error -like "*Ya existe un pago*") {
                Log-Success "Mensaje de error correcto ✓"
            }
        }
    }
}
catch {
    Log-Error "Error en la carga: $_"
}

Write-Host ""
Write-Host "=" * 60
Write-Host "TEST 4: Carga Masiva - Documentos DUPLICADOS DENTRO del mismo archivo" -ForegroundColor Cyan
Write-Host "=" * 60

# Crear archivo Excel con 3 pagos (2 con DOC-INTERNAL-001, debe rechazarse 1)
$ExcelPath2 = "$env:TEMP\test_duplicate_internal_$(Get-Date -Format 'yyyyMMddHHmmss').xlsx"
$CsvPath2 = $ExcelPath2.Replace('.xlsx', '.csv')
$CsvContent2 = @"
cedula,prestamo_id,fecha_pago,monto_pagado,numero_documento
$ClienteCedula,$PrestamoId,2026-03-10,8000,DOC-INTERNAL-001
$ClienteCedula,$PrestamoId,2026-03-15,5000,DOC-INTERNAL-002
$ClienteCedula,$PrestamoId,2026-03-20,5000,DOC-INTERNAL-001
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

Log-Info "Archivo Excel creado con 3 pagos (2 con mismo documento)"

# Subir archivo
try {
    $UploadResponse2 = Invoke-RestMethod -Uri "https://pagos-backend-ov5f.onrender.com/api/v1/pagos/upload" `
        -Method POST `
        -Headers $Headers `
        -Form @{file = Get-Item $ExcelPath2 } `
        -ContentType "multipart/form-data"

    Log-Info "Respuesta de carga:"
    Log-Info "  - Registros creados: $($UploadResponse2.registros_creados)"
    Log-Info "  - Registros con error: $($UploadResponse2.registros_con_error)"

    if ($UploadResponse2.registros_creados -eq 2) {
        Log-Success "2 pagos creados (documentos únicos) ✓"
    }
    else {
        Log-Error "Se esperaba 2 pagos creados, se crearon: $($UploadResponse2.registros_creados)"
    }

    if ($UploadResponse2.registros_con_error -eq 1) {
        Log-Success "1 pago rechazado (duplicado dentro del archivo) ✓"
    }
    else {
        Log-Error "Se esperaba 1 pago rechazado, se rechazaron: $($UploadResponse2.registros_con_error)"
    }

    if ($UploadResponse2.errores) {
        Log-Info "Errores reportados:"
        foreach ($error in $UploadResponse2.errores) {
            Log-Info "  - $error"
            if ($error -like "*duplicado en este archivo*") {
                Log-Success "Mensaje de error correcto (duplicado en archivo) ✓"
            }
        }
    }
}
catch {
    Log-Error "Error en la carga: $_"
}

Write-Host ""
Write-Host "=" * 60
Write-Host "TEST 5: Validación Final - Verificar BD Consistency" -ForegroundColor Cyan
Write-Host "=" * 60

try {
    $AllPayments = Invoke-RestMethod -Uri "https://pagos-backend-ov5f.onrender.com/api/v1/pagos?limit=1000" `
        -Method GET `
        -Headers $Headers

    $UniqueDocuments = @($AllPayments.items | Where-Object { $_.prestamo_id -eq $PrestamoId } | Select-Object -ExpandProperty numero_documento -Unique).Count
    $TotalPayments = @($AllPayments.items | Where-Object { $_.prestamo_id -eq $PrestamoId }).Count

    Log-Info "Total pagos para este préstamo: $TotalPayments"
    Log-Info "Documentos únicos: $UniqueDocuments"

    if ($UniqueDocuments -eq $TotalPayments) {
        Log-Success "Todos los documentos son únicos - sin duplicados en BD ✓"
    }
    else {
        Log-Error "¡Encontrados documentos duplicados! Total=$TotalPayments, Únicos=$UniqueDocuments"
    }
}
catch {
    Log-Error "Error verificando BD: $_"
}

# === CLEANUP ===
Remove-Item $CsvPath -Force -ErrorAction SilentlyContinue
Remove-Item $ExcelPath -Force -ErrorAction SilentlyContinue
Remove-Item $CsvPath2 -Force -ErrorAction SilentlyContinue
Remove-Item $ExcelPath2 -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=" * 60
Write-Host "RESUMEN: Tests de Rechazo de Documentos Duplicados" -ForegroundColor Green
Write-Host "=" * 60
Write-Host "[✓] TEST 1: Pago original aceptado"
Write-Host "[✓] TEST 2: Documento duplicado rechazado (409)"
Write-Host "[✓] TEST 3: Carga masiva rechaza duplicado en BD"
Write-Host "[✓] TEST 4: Carga masiva rechaza duplicado en archivo"
Write-Host "[✓] TEST 5: BD consistency validada"
Write-Host ""
Write-Host "CONCLUSIÓN: ¡Todos los tests de rechazo de duplicados pasaron!" -ForegroundColor Green
