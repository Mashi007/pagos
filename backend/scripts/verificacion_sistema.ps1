Write-Host "=== SEGUNDO ENFOQUE DE VALIDACION Y RESOLUCION ===" -ForegroundColor Green
Write-Host ""

Write-Host "1. VERIFICACION CONECTIVIDAD BASICA:" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "https://pagos-f2qf.onrender.com/" -TimeoutSec 10
    Write-Host "   Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "   ✅ Servidor respondiendo" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "2. VERIFICACION ENDPOINT DE AUTH:" -ForegroundColor Yellow

$loginData = @{
    email = "itmaster@rapicreditca.com"
    password = "R@pi_2025**"
} | ConvertTo-Json

try {
    $response = Invoke-WebRequest -Uri "https://pagos-f2qf.onrender.com/api/v1/auth/login" -Method POST -Body $loginData -ContentType "application/json" -TimeoutSec 15
    Write-Host "   Status: $($response.StatusCode)" -ForegroundColor Green
    
    if ($response.StatusCode -eq 200) {
        Write-Host "   ✅ LOGIN EXITOSO!" -ForegroundColor Green
        $data = $response.Content | ConvertFrom-Json
        Write-Host "   Token: $($data.access_token.Substring(0,20))..." -ForegroundColor Green
        Write-Host "   Usuario: $($data.user.email)" -ForegroundColor Green
    } elseif ($response.StatusCode -eq 503) {
        Write-Host "   ❌ ERROR 503 PERSISTE" -ForegroundColor Red
        Write-Host "   Detalles: $($response.Content)" -ForegroundColor Red
    } elseif ($response.StatusCode -eq 401) {
        Write-Host "   ❌ ERROR 401: Credenciales incorrectas" -ForegroundColor Red
    } else {
        Write-Host "   ❌ Status inesperado: $($response.Content)" -ForegroundColor Red
    }
} catch {
    Write-Host "   ❌ Error en auth: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "3. VERIFICACION OTROS ENDPOINTS:" -ForegroundColor Yellow

$endpoints = @(
    @{url="/api/v1/clientes/ping"; name="Clientes"},
    @{url="/api/v1/validadores/ping"; name="Validadores"},
    @{url="/api/v1/usuarios/"; name="Usuarios"},
    @{url="/api/v1/clientes/count"; name="Conteo clientes"}
)

foreach ($endpoint in $endpoints) {
    try {
        $response = Invoke-WebRequest -Uri "https://pagos-f2qf.onrender.com$($endpoint.url)" -TimeoutSec 10
        Write-Host "   $($endpoint.name): $($response.StatusCode)" -ForegroundColor Green
        
        if ($response.StatusCode -eq 200) {
            Write-Host "      ✅ OK" -ForegroundColor Green
        } elseif ($response.StatusCode -eq 403) {
            Write-Host "      ⚠️ Requiere autenticacion (esperado)" -ForegroundColor Yellow
        } elseif ($response.StatusCode -eq 404) {
            Write-Host "      ❌ No existe" -ForegroundColor Red
        } elseif ($response.StatusCode -eq 503) {
            Write-Host "      ❌ Error de servidor" -ForegroundColor Red
        }
    } catch {
        Write-Host "   $($endpoint.name): ❌ ERROR - $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "4. VERIFICACION CONFIGURACION:" -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "https://pagos-f2qf.onrender.com/api/v1/clientes/opciones-configuracion" -TimeoutSec 10
    Write-Host "   Opciones configuracion: $($response.StatusCode)" -ForegroundColor Green
    
    if ($response.StatusCode -eq 200) {
        $data = $response.Content | ConvertFrom-Json
        Write-Host "      Modelos vehiculos: $($data.modelos_vehiculos.Count)" -ForegroundColor Green
        Write-Host "      Analistas: $($data.analistas.Count)" -ForegroundColor Green
        Write-Host "      Concesionarios: $($data.concesionarios.Count)" -ForegroundColor Green
    } else {
        Write-Host "      ❌ Error: $($response.Content)" -ForegroundColor Red
    }
} catch {
    Write-Host "   ❌ Error verificando configuracion: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== CONCLUSIONES DEL SEGUNDO ENFOQUE ===" -ForegroundColor Cyan
Write-Host "✅ Si el login es exitoso (200), el problema esta resuelto." -ForegroundColor Green
Write-Host "❌ Si el login da 503, el problema persiste." -ForegroundColor Red
Write-Host "⚠️ Si el login da 401, las credenciales son incorrectas." -ForegroundColor Yellow
Write-Host "✅ Si otros endpoints funcionan, el sistema esta operativo." -ForegroundColor Green
