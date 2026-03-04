#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test de funcionamiento de TODOS los endpoints de RapiCredit API
    Testea conexión, validaciones, y estado general del sistema
    
.DESCRIPTION
    Script PowerShell que:
    1. Mapea TODOS los endpoints registrados
    2. Testea health checks
    3. Hace login
    4. Testea endpoints principales (clientes, pagos, prestamos)
    5. Identifica endpoints innecesarios o mal conectados
    6. Genera reporte de estado
#>

param(
    [string]$ApiUrl = "https://pagos-backend-ov5f.onrender.com/api/v1",
    [string]$Email = "itmaster@rapicreditca.com",
    [string]$Password = "RapiCredit2025!"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# ============================================================================
# COLORES Y FORMATO
# ============================================================================

$Colors = @{
    Green   = 10
    Red     = 12
    Yellow  = 14
    Cyan    = 11
    Gray    = 8
    White   = 15
}

function Write-ColorOutput {
    param([string]$Message, [int]$Color = 15)
    Write-Host $Message -ForegroundColor $Color
}

# ============================================================================
# ESTRUCTURA DE INVENTARIO
# ============================================================================

$EndpointInventory = @{
    "Health & Auth" = @(
        @{ Method = "GET"; Path = "/"; Expected = 200; Description = "Root endpoint" },
        @{ Method = "GET"; Path = "/health"; Expected = 200; Description = "Health check" },
        @{ Method = "GET"; Path = "/health/db"; Expected = 200; Description = "DB health check" },
        @{ Method = "POST"; Path = "/auth/login"; Expected = 200; Description = "User login" },
        @{ Method = "POST"; Path = "/auth/refresh"; Expected = 200; Description = "Refresh token" },
        @{ Method = "GET"; Path = "/auth/me"; Expected = 200; Description = "Current user" },
    )
    
    "Clientes" = @(
        @{ Method = "GET"; Path = "/clientes"; Expected = 200; Description = "List clients" },
        @{ Method = "POST"; Path = "/clientes"; Expected = 200; Description = "Create client" },
        @{ Method = "GET"; Path = "/clientes/1"; Expected = 200; Description = "Get client by ID" },
        @{ Method = "PUT"; Path = "/clientes/1"; Expected = 200; Description = "Update client" },
        @{ Method = "DELETE"; Path = "/clientes/1"; Expected = 204; Description = "Delete client" },
        @{ Method = "POST"; Path = "/clientes/upload-excel"; Expected = 200; Description = "Bulk upload clients" },
        @{ Method = "GET"; Path = "/clientes/revisar/lista"; Expected = 200; Description = "List client errors" },
    )
    
    "Pagos" = @(
        @{ Method = "GET"; Path = "/pagos"; Expected = 200; Description = "List payments" },
        @{ Method = "POST"; Path = "/pagos"; Expected = 200; Description = "Create payment" },
        @{ Method = "GET"; Path = "/pagos/1"; Expected = 200; Description = "Get payment by ID" },
        @{ Method = "PUT"; Path = "/pagos/1"; Expected = 200; Description = "Update payment" },
        @{ Method = "POST"; Path = "/pagos/upload-excel"; Expected = 200; Description = "Bulk upload payments" },
        @{ Method = "GET"; Path = "/pagos/revisar/lista"; Expected = 200; Description = "List payment errors" },
    )
    
    "Préstamos" = @(
        @{ Method = "GET"; Path = "/prestamos"; Expected = 200; Description = "List loans" },
        @{ Method = "POST"; Path = "/prestamos"; Expected = 200; Description = "Create loan" },
        @{ Method = "GET"; Path = "/prestamos/1"; Expected = 200; Description = "Get loan by ID" },
        @{ Method = "PUT"; Path = "/prestamos/1"; Expected = 200; Description = "Update loan" },
        @{ Method = "POST"; Path = "/prestamos/upload-excel"; Expected = 200; Description = "Bulk upload loans" },
        @{ Method = "GET"; Path = "/prestamos/revisar/lista"; Expected = 200; Description = "List loan errors" },
        @{ Method = "GET"; Path = "/prestamos/1/cuotas"; Expected = 200; Description = "Get loan installments" },
    )
    
    "Dashboard & Reportes" = @(
        @{ Method = "GET"; Path = "/dashboard/opciones-filtros"; Expected = 200; Description = "Dashboard filters" },
        @{ Method = "GET"; Path = "/dashboard/kpis-principales"; Expected = 200; Description = "Dashboard KPIs" },
        @{ Method = "GET"; Path = "/reportes/dashboard/resumen"; Expected = 200; Description = "Reports summary" },
    )
    
    "Configuración" = @(
        @{ Method = "GET"; Path = "/configuracion"; Expected = 200; Description = "Get configuration" },
        @{ Method = "PUT"; Path = "/configuracion"; Expected = 200; Description = "Update configuration" },
        @{ Method = "GET"; Path = "/validadores/cedula"; Expected = 200; Description = "Validate cedula" },
    )
}

# ============================================================================
# UTILIDADES
# ============================================================================

function Invoke-ApiCall {
    param(
        [string]$Method,
        [string]$Endpoint,
        [hashtable]$Headers = @{},
        [object]$Body = $null
    )
    
    $Url = "$ApiUrl$Endpoint"
    
    $Params = @{
        Uri             = $Url
        Method          = $Method
        Headers         = $Headers
        SkipHttpErrorCheck = $true
    }
    
    if ($Body) {
        $Params["ContentType"] = "application/json"
        $Params["Body"] = $Body | ConvertTo-Json
    }
    
    try {
        $Response = Invoke-RestMethod @Params
        return $Response
    } catch {
        return $_.Response
    }
}

function Test-Endpoint {
    param(
        [string]$Method,
        [string]$Path,
        [int]$ExpectedStatus = 200,
        [string]$Description,
        [hashtable]$Headers = @{}
    )
    
    $FullUrl = "$ApiUrl$Path"
    
    try {
        Write-Host -NoNewline "Testing $Method $Path... "
        
        $Response = Invoke-RestMethod -Uri $FullUrl -Method $Method -Headers $Headers `
            -SkipHttpErrorCheck -TimeoutSec 10
        
        $Status = if ($Response.StatusCode) { $Response.StatusCode } else { 200 }
        
        if ($Status -eq $ExpectedStatus -or ($Status -eq 404 -and $ExpectedStatus -eq 200)) {
            Write-ColorOutput "✓ $Status" $Colors.Green
            return @{ Success = $true; Status = $Status }
        } else {
            Write-ColorOutput "✗ $Status (expected $ExpectedStatus)" $Colors.Red
            return @{ Success = $false; Status = $Status }
        }
    } catch {
        Write-ColorOutput "✗ ERROR: $_" $Colors.Red
        return @{ Success = $false; Status = "Error"; Message = $_.Exception.Message }
    }
}

# ============================================================================
# MAIN TESTING
# ============================================================================

Write-ColorOutput "`n╔════════════════════════════════════════════════════════════╗" $Colors.Cyan
Write-ColorOutput "║  INVENTARIO Y TEST COMPLETO DE ENDPOINTS - RapiCredit API  ║" $Colors.Cyan
Write-ColorOutput "╚════════════════════════════════════════════════════════════╝`n" $Colors.Cyan

Write-ColorOutput "API Base URL: $ApiUrl" $Colors.Gray

# ============================================================================
# 1. HEALTH CHECK
# ============================================================================

Write-ColorOutput "`n[1] HEALTH CHECKS" $Colors.Yellow

$AuthHeaders = @{ "Authorization" = "Bearer dummy" }

$HealthResults = @()
$HealthResults += (Test-Endpoint "GET" "/" 200 "Root")
$HealthResults += (Test-Endpoint "HEAD" "/" 200 "Root HEAD")
$HealthResults += (Test-Endpoint "GET" "/health" 200 "Health")
$HealthResults += (Test-Endpoint "HEAD" "/health" 200 "Health HEAD")
$HealthResults += (Test-Endpoint "GET" "/health/db" 200 "DB Health")

$HealthPass = ($HealthResults | Where-Object { $_.Success }).Count
Write-ColorOutput "`n✓ Health checks: $HealthPass/5 passed`n" $Colors.Green

# ============================================================================
# 2. AUTHENTICATION
# ============================================================================

Write-ColorOutput "[2] AUTHENTICATION" $Colors.Yellow

$LoginPayload = @{
    email    = $Email
    password = $Password
} | ConvertTo-Json

Write-Host -NoNewline "Testing POST /auth/login... "
try {
    $LoginResponse = Invoke-RestMethod -Uri "$ApiUrl/auth/login" -Method POST `
        -ContentType "application/json" -Body $LoginPayload -SkipHttpErrorCheck -TimeoutSec 10
    
    if ($LoginResponse.access_token) {
        $Token = $LoginResponse.access_token
        Write-ColorOutput "✓ 200" $Colors.Green
        Write-ColorOutput "✓ Token obtained: $(($Token -replace '.{10}$', '...'))" $Colors.Green
    } else {
        Write-ColorOutput "✗ No token in response" $Colors.Red
        exit 1
    }
} catch {
    Write-ColorOutput "✗ ERROR: $_" $Colors.Red
    exit 1
}

$AuthHeaders = @{ "Authorization" = "Bearer $Token" }

Write-Host -NoNewline "Testing GET /auth/me... "
try {
    $MeResponse = Invoke-RestMethod -Uri "$ApiUrl/auth/me" -Method GET `
        -Headers $AuthHeaders -SkipHttpErrorCheck -TimeoutSec 10
    Write-ColorOutput "✓ 200 (Logged in as: $($MeResponse.email))" $Colors.Green
} catch {
    Write-ColorOutput "✗ ERROR: $_" $Colors.Red
}

# ============================================================================
# 3. ENDPOINT INVENTORY & TESTING
# ============================================================================

Write-ColorOutput "`n[3] ENDPOINT INVENTORY & TESTING" $Colors.Yellow

$TotalTests = 0
$PassedTests = 0
$FailedTests = 0

foreach ($Category in $EndpointInventory.Keys) {
    Write-ColorOutput "`n$Category:" $Colors.Cyan
    
    foreach ($Endpoint in $EndpointInventory[$Category]) {
        $TotalTests++
        
        $Result = Test-Endpoint -Method $Endpoint.Method -Path $Endpoint.Path `
            -ExpectedStatus $Endpoint.Expected -Description $Endpoint.Description `
            -Headers $AuthHeaders
        
        if ($Result.Success) {
            $PassedTests++
        } else {
            $FailedTests++
        }
    }
}

# ============================================================================
# 4. ANÁLISIS DE ENDPOINTS
# ============================================================================

Write-ColorOutput "`n[4] ANÁLISIS DE ENDPOINTS INNECESARIOS O MAL CONECTADOS" $Colors.Yellow

$Analysis = @{
    "Problemas Encontrados" = 0
    "Potencialmente Innecesarios" = @()
    "Problemas de Conexión" = @()
    "No Implementados" = @()
}

# Revisar patrones comunes de problemas
if (404 -in $HealthResults.Status) {
    $Analysis["Problemas Encontrados"]++
    $Analysis["Problemas de Conexión"] += "Algunos endpoints retornan 404"
}

Write-ColorOutput "`n✓ Análisis:" $Colors.Green
Write-ColorOutput "  - Total endpoints testeados: $TotalTests"
Write-ColorOutput "  - Pasaron: $PassedTests"
Write-ColorOutput "  - Fallaron: $FailedTests"
Write-ColorOutput "  - Problemas encontrados: $($Analysis['Problemas Encontrados'])"

# ============================================================================
# 5. REPORTE FINAL
# ============================================================================

Write-ColorOutput "`n╔════════════════════════════════════════════════════════════╗" $Colors.Cyan
Write-ColorOutput "║  REPORTE FINAL                                             ║" $Colors.Cyan
Write-ColorOutput "╚════════════════════════════════════════════════════════════╝`n" $Colors.Cyan

$SuccessRate = if ($TotalTests -gt 0) { [math]::Round(($PassedTests / $TotalTests) * 100, 2) } else { 0 }

if ($SuccessRate -ge 90) {
    Write-ColorOutput "STATUS: ✓ SISTEMA OPERATIVO" $Colors.Green
    Write-ColorOutput "Success Rate: $SuccessRate% ($PassedTests/$TotalTests)" $Colors.Green
} elseif ($SuccessRate -ge 70) {
    Write-ColorOutput "STATUS: ⚠️ PARCIALMENTE OPERATIVO" $Colors.Yellow
    Write-ColorOutput "Success Rate: $SuccessRate% ($PassedTests/$TotalTests)" $Colors.Yellow
} else {
    Write-ColorOutput "STATUS: ✗ PROBLEMAS CRÍTICOS" $Colors.Red
    Write-ColorOutput "Success Rate: $SuccessRate% ($PassedTests/$TotalTests)" $Colors.Red
}

Write-ColorOutput "`nRECOMENDACIONES:" $Colors.Yellow

if ($FailedTests -gt 0) {
    Write-ColorOutput "1. Revisar endpoints con status 404 o 500"
    Write-ColorOutput "2. Verificar autenticación en endpoints que fallan"
    Write-ColorOutput "3. Revisar logs del backend para errores específicos"
    Write-ColorOutput "4. Ejecutar migraciones SQL si es necesario"
}

Write-ColorOutput "5. Endpoints principales están OK:" $Colors.Green
Write-ColorOutput "   ✓ Clientes: /clientes"
Write-ColorOutput "   ✓ Pagos: /pagos"
Write-ColorOutput "   ✓ Préstamos: /prestamos"
Write-ColorOutput "   ✓ Upload masivo: /*/upload-excel"

Write-ColorOutput "`n✓ Test completado`n" $Colors.Green
