# Script de validación PowerShell para tokens JWT
# Valida la causa raíz de errores 401 Unauthorized

Write-Host "🔍 VALIDACIÓN ALTERNATIVA DE TOKENS JWT" -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Cyan

$backendUrl = "https://pagos-f2qf.onrender.com"
$frontendUrl = "https://rapicredit.onrender.com"

# Función para hacer requests HTTP
function Test-Endpoint {
    param(
        [string]$Url,
        [hashtable]$Headers = @{},
        [string]$Method = "GET",
        [string]$Body = $null
    )
    
    try {
        $response = Invoke-RestMethod -Uri $Url -Method $Method -Headers $Headers -Body $Body -TimeoutSec 10
        return @{
            Success = $true
            StatusCode = 200
            Data = $response
        }
    }
    catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        return @{
            Success = $false
            StatusCode = $statusCode
            Error = $_.Exception.Message
        }
    }
}

# 1. Probar endpoint de login
Write-Host "`n🔐 PROBANDO LOGIN..." -ForegroundColor Yellow

$loginData = @{
    email = "itmaster@rapicreditca.com"
    password = "admin123"
} | ConvertTo-Json

$loginResult = Test-Endpoint -Url "$backendUrl/api/v1/auth/login" -Method "POST" -Body $loginData -Headers @{"Content-Type"="application/json"}

if ($loginResult.Success) {
    Write-Host "✅ Login exitoso!" -ForegroundColor Green
    $accessToken = $loginResult.Data.access_token
    Write-Host "📝 Token recibido: $($accessToken.Substring(0, 50))..." -ForegroundColor Gray
    
    # 2. Probar endpoints protegidos con token
    Write-Host "`n🔒 PROBANDO ENDPOINTS PROTEGIDOS..." -ForegroundColor Yellow
    
    $authHeaders = @{
        "Authorization" = "Bearer $accessToken"
        "Content-Type" = "application/json"
        "Origin" = $frontendUrl
    }
    
    $endpoints = @(
        "/api/v1/auth/me",
        "/api/v1/usuarios/?page=1&page_size=100",
        "/api/v1/clientes/?page=1&per_page=20"
    )
    
    $successCount = 0
    foreach ($endpoint in $endpoints) {
        Write-Host "`n🔍 Probando: $endpoint" -ForegroundColor Cyan
        
        $result = Test-Endpoint -Url "$backendUrl$endpoint" -Headers $authHeaders
        
        if ($result.Success) {
            Write-Host "✅ Endpoint accesible!" -ForegroundColor Green
            $successCount++
        } else {
            Write-Host "❌ Error $($result.StatusCode): $($result.Error)" -ForegroundColor Red
        }
    }
    
    # 3. Resumen
    Write-Host "`n📊 RESUMEN:" -ForegroundColor Magenta
    Write-Host "✅ Endpoints exitosos: $successCount/$($endpoints.Count)" -ForegroundColor $(if($successCount -eq $endpoints.Count) {"Green"} else {"Red"})
    
    if ($successCount -eq $endpoints.Count) {
        Write-Host "🎯 CONCLUSIÓN: Backend funcionando correctamente" -ForegroundColor Green
        Write-Host "   El problema está en el frontend (token storage, interceptors)" -ForegroundColor Yellow
    } elseif ($successCount -eq 0) {
        Write-Host "🎯 CONCLUSIÓN: Problema crítico en backend" -ForegroundColor Red
        Write-Host "   Los tokens no son válidos o hay problema en middleware de auth" -ForegroundColor Yellow
    } else {
        Write-Host "🎯 CONCLUSIÓN: Problema parcial" -ForegroundColor Yellow
        Write-Host "   Algunos endpoints funcionan, otros no" -ForegroundColor Yellow
    }
    
} else {
    Write-Host "❌ Login falló: $($loginResult.Error)" -ForegroundColor Red
    Write-Host "🎯 CONCLUSIÓN: Problema crítico en autenticación básica" -ForegroundColor Red
}

# 4. Probar CORS
Write-Host "`n🌐 PROBANDO CORS..." -ForegroundColor Yellow

try {
    $corsHeaders = @{
        "Access-Control-Request-Method" = "GET"
        "Access-Control-Request-Headers" = "Authorization, Content-Type"
        "Origin" = $frontendUrl
    }
    
    $corsResponse = Invoke-RestMethod -Uri "$backendUrl/api/v1/auth/me" -Method "OPTIONS" -Headers $corsHeaders -TimeoutSec 10
    Write-Host "✅ CORS funcionando correctamente" -ForegroundColor Green
}
catch {
    Write-Host "❌ Error en CORS: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n🎯 VALIDACIÓN COMPLETADA" -ForegroundColor Cyan
