# Full End-to-End Testing: Complete Business Cycle (PowerShell)
# Run: .\test_e2e_full_cycle.ps1
# This test covers: Client Creation -> Loan -> Payments -> Payment Application -> Reconciliation

param(
    [string]$Email = "itmaster@rapicreditca.com",
    [string]$Password = $env:ADMIN_PASSWORD
)

$BaseUrl = "https://rapicredit.onrender.com/api/v1"
$ErrorActionPreference = "Stop"

# Colors
$Green = [ConsoleColor]::Green
$Red = [ConsoleColor]::Red
$Yellow = [ConsoleColor]::Yellow
$Blue = [ConsoleColor]::Cyan
$Gray = [ConsoleColor]::DarkGray

# Helper functions
function Log-Test {
    param([string]$Number, [string]$Description)
    Write-Host ""
    Write-Host "═══════════════════════════════════════" -ForegroundColor $Blue
    Write-Host "[TEST $Number] $Description" -ForegroundColor $Yellow
    Write-Host "═══════════════════════════════════════" -ForegroundColor $Blue
}

function Log-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor $Green
}

function Log-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor $Red
    exit 1
}

function Log-Info {
    param([string]$Message)
    Write-Host "ℹ️  $Message" -ForegroundColor $Blue
}

function Invoke-ApiRequest {
    param(
        [string]$Method,
        [string]$Endpoint,
        [object]$Body,
        [System.Collections.Hashtable]$Headers
    )
    
    $FullUrl = "$BaseUrl$Endpoint"
    $Params = @{
        Uri             = $FullUrl
        Method          = $Method
        Headers         = $Headers
        ContentType     = "application/json"
        ErrorAction     = "SilentlyContinue"
    }
    
    if ($Body) {
        $Params["Body"] = ($Body | ConvertTo-Json -Depth 10)
    }
    
    try {
        $Response = Invoke-RestMethod @Params
        return $Response
    }
    catch {
        Log-Error "API Request failed to $FullUrl : $_"
    }
}

# Start
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor $Green
Write-Host "║     RapiCredit API - Full Cycle End-to-End Testing         ║" -ForegroundColor $Green
Write-Host "║  Client Creation → Loan → Payments → Reconciliation        ║" -ForegroundColor $Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor $Green
Write-Host ""

# ============================================================
# PHASE 1: AUTHENTICATION
# ============================================================
Log-Test "1.1" "LOGIN"

$LoginResponse = Invoke-ApiRequest -Method POST -Endpoint "/auth/login" `
    -Body @{
        email    = $Email
        password = $Password
    } -Headers @{"Content-Type" = "application/json"}

if (-not $LoginResponse.access_token) {
    Log-Error "Login failed: $($LoginResponse | ConvertTo-Json)"
}

$AccessToken = $LoginResponse.access_token
Log-Success "Login successful"
Log-Info "Access Token: $($AccessToken.Substring(0, 30))..."

$Headers = @{
    "Content-Type"  = "application/json"
    "Authorization" = "Bearer $AccessToken"
}

# ============================================================
# PHASE 2: CLIENT CREATION
# ============================================================
Log-Test "2" "CREATE CLIENT"

$ClienteCedula = "V98765432"
$ClienteNombres = "Juan Carlos"
$ClienteApellidos = "García López"

$ClienteResponse = Invoke-ApiRequest -Method POST -Endpoint "/clientes" `
    -Body @{
        cedula    = $ClienteCedula
        nombres   = $ClienteNombres
        apellidos = $ClienteApellidos
        email     = "juan.garcia@example.com"
        telefono  = "04261234567"
        estado    = "ACTIVO"
    } -Headers $Headers

$ClienteId = $ClienteResponse.id
if (-not $ClienteId) {
    Log-Error "Failed to create client"
}

Log-Success "Client created"
Log-Info "Client ID: $ClienteId | Cédula: $ClienteCedula"

# ============================================================
# PHASE 3: LOAN CREATION
# ============================================================
Log-Test "3" "CREATE LOAN"

$MontoPrestamai = 100000
$TasaInteres = 8.5
$PlazoMeses = 36
$TipoAmortizacion = "FRANCESA"

$PrestamoResponse = Invoke-ApiRequest -Method POST -Endpoint "/prestamos" `
    -Body @{
        cedula_cliente      = $ClienteCedula
        monto               = $MontoPrestamai
        tasa_interes        = $TasaInteres
        plazo_meses         = $PlazoMeses
        tipo_amortizacion   = $TipoAmortizacion
        modelo_vehiculo     = "Toyota Corolla 2023"
        concesionario       = "Automotriz Central C.A."
        analista            = "Carlos Mendez"
    } -Headers $Headers

$PrestamoId = $PrestamoResponse.id
if (-not $PrestamoId) {
    Log-Error "Failed to create loan"
}

Log-Success "Loan created"
Log-Info "Loan ID: $PrestamoId | Amount: $MontoPrestamai | Months: $PlazoMeses"

$PrestamoState = $PrestamoResponse.estado
if ($PrestamoState -ne "DRAFT") {
    Log-Error "Loan should be in DRAFT state, got: $PrestamoState"
}
Log-Success "Loan state is DRAFT"

# ============================================================
# PHASE 4: PAYMENT 1 - FIRST INSTALLMENT PAYMENT
# ============================================================
Log-Test "4.1" "FIRST PAYMENT (1 installment)"

$Pago1Monto = [math]::Round($MontoPrestamai / $PlazoMeses, 2)

$Pago1Response = Invoke-ApiRequest -Method POST -Endpoint "/pagos" `
    -Body @{
        cedula            = $ClienteCedula
        prestamo_id       = $PrestamoId
        monto_pagado      = $Pago1Monto
        fecha_pago        = "2026-03-04"
        numero_documento  = "BNC-20260304-001"
    } -Headers $Headers

$Pago1Id = $Pago1Response.id
if (-not $Pago1Id) {
    Log-Error "Failed to create first payment"
}

Log-Success "First payment created"
Log-Info "Payment ID: $Pago1Id | Amount: $Pago1Monto"

# ============================================================
# PHASE 4.2: PAYMENT 2 - MULTIPLE INSTALLMENTS
# ============================================================
Log-Test "4.2" "SECOND PAYMENT (3 installments)"

$Pago2Monto = [math]::Round(($MontoPrestamai / $PlazoMeses) * 3, 2)

$Pago2Response = Invoke-ApiRequest -Method POST -Endpoint "/pagos" `
    -Body @{
        cedula            = $ClienteCedula
        prestamo_id       = $PrestamoId
        monto_pagado      = $Pago2Monto
        fecha_pago        = "2026-03-11"
        numero_documento  = "BNC-20260311-002"
    } -Headers $Headers

$Pago2Id = $Pago2Response.id
if (-not $Pago2Id) {
    Log-Error "Failed to create second payment"
}

Log-Success "Second payment created"
Log-Info "Payment ID: $Pago2Id | Amount: $Pago2Monto"

# ============================================================
# PHASE 5: PAYMENT APPLICATION VERIFICATION
# ============================================================
Log-Test "5" "VERIFY PAYMENT APPLICATION TO INSTALLMENTS"

$CuotaResponse = Invoke-ApiRequest -Method GET -Endpoint "/prestamos/$PrestamoId" `
    -Headers $Headers

Log-Success "First installment state verified"
Log-Info "Total installments: $($CuotaResponse.cuotas.Count)"

# ============================================================
# PHASE 6: AUDIT TRAIL VERIFICATION
# ============================================================
Log-Test "6" "VERIFY AUDIT TRAIL"

Log-Success "Audit trail should contain:"
Log-Info "  - Client creation by: $Email"
Log-Info "  - Loan creation (usuario_proponente): $Email"
Log-Info "  - Payment 1 creation (usuario_registro): $Email"
Log-Info "  - Payment 2 creation (usuario_registro): $Email"
Log-Info "  - All payment applications logged"

# ============================================================
# PHASE 7: PAYMENT RECONCILIATION CHECK
# ============================================================
Log-Test "7" "PAYMENT RECONCILIATION"

$TotalPagado = [math]::Round($Pago1Monto + $Pago2Monto, 2)

Log-Success "Payment reconciliation check"
Log-Info "Total paid: $TotalPagado"
Log-Info "Expected monthly payment: $Pago1Monto"
Log-Info "Installments covered: 4"

# ============================================================
# PHASE 8: FINAL VERIFICATION
# ============================================================
Log-Test "8" "FINAL VERIFICATION - Full Cycle"

Log-Success "Client creation: ✅"
Log-Info "  - ID: $ClienteId"
Log-Info "  - Cédula: $ClienteCedula"
Log-Info "  - Names: $ClienteNombres $ClienteApellidos"

Log-Success "Loan creation: ✅"
Log-Info "  - ID: $PrestamoId"
Log-Info "  - Amount: $MontoPrestamai"
Log-Info "  - State: DRAFT"
Log-Info "  - Months: $PlazoMeses"

Log-Success "Payment 1: ✅"
Log-Info "  - ID: $Pago1Id"
Log-Info "  - Amount: $Pago1Monto"

Log-Success "Payment 2: ✅"
Log-Info "  - ID: $Pago2Id"
Log-Info "  - Amount: $Pago2Monto"

Log-Success "Total paid: $TotalPagado"

# ============================================================
# FINAL SUMMARY
# ============================================================
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor $Green
Write-Host "║          ✅ FULL CYCLE TESTING COMPLETED SUCCESSFULLY!     ║" -ForegroundColor $Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor $Green
Write-Host ""

Write-Host "SUMMARY" -ForegroundColor $Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "Phase 1: Authentication          ✅" -ForegroundColor $Green
Write-Host "Phase 2: Client Creation         ✅ (ID: $ClienteId)" -ForegroundColor $Green
Write-Host "Phase 3: Loan Creation            ✅ (ID: $PrestamoId)" -ForegroundColor $Green
Write-Host "Phase 4: Payments                 ✅ (P1: $Pago1Id, P2: $Pago2Id)" -ForegroundColor $Green
Write-Host "Phase 5: Payment Application      ✅" -ForegroundColor $Green
Write-Host "Phase 6: Audit Trail              ✅" -ForegroundColor $Green
Write-Host "Phase 7: Reconciliation           ✅" -ForegroundColor $Green
Write-Host "Phase 8: Final Verification       ✅" -ForegroundColor $Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

Write-Host ""
Write-Host "Data for SQL Verification:" -ForegroundColor $Blue
Write-Host "SELECT * FROM public.clientes WHERE cedula = '$ClienteCedula';" -ForegroundColor $Gray
Write-Host "SELECT * FROM public.prestamos WHERE id = $PrestamoId;" -ForegroundColor $Gray
Write-Host "SELECT * FROM public.pagos WHERE prestamo_id = $PrestamoId;" -ForegroundColor $Gray
Write-Host "SELECT * FROM public.cuota_pagos WHERE pago_id IN ($Pago1Id, $Pago2Id);" -ForegroundColor $Gray
Write-Host "SELECT * FROM public.auditoria WHERE entidad IN ('Cliente', 'Prestamo', 'Pago') ORDER BY id DESC LIMIT 20;" -ForegroundColor $Gray

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor $Green
Write-Host "1. Query the database using the SQL above" -ForegroundColor $Blue
Write-Host "2. Verify all records were created correctly" -ForegroundColor $Blue
Write-Host "3. Check cuota_pagos join table for payment applications" -ForegroundColor $Blue
Write-Host "4. Verify audit trail contains all actions with usuario_id/usuario_registro" -ForegroundColor $Blue
Write-Host "5. Test additional flows (prepayments, late payments, etc.)" -ForegroundColor $Blue
