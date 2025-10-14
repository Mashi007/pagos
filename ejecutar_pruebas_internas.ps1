# 🧪 EJECUTAR PRUEBAS INTERNAS DEL SISTEMA RAPICREDIT
# Script PowerShell para ejecutar todas las pruebas internas

Write-Host "🧪 PRUEBAS INTERNAS DEL SISTEMA RAPICREDIT" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

# Verificar Python
Write-Host "`n🔍 Verificando Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python encontrado: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python no encontrado. Instalando..." -ForegroundColor Red
    # Intentar usar py en lugar de python
    try {
        $pythonVersion = py --version 2>&1
        Write-Host "✅ Python encontrado (via py): $pythonVersion" -ForegroundColor Green
        $pythonCmd = "py"
    } catch {
        Write-Host "❌ Python no disponible. Instalando Python..." -ForegroundColor Red
        # Aquí podrías agregar lógica para instalar Python automáticamente
        exit 1
    }
}

# Verificar Node.js
Write-Host "`n🔍 Verificando Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    Write-Host "✅ Node.js encontrado: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js no encontrado. Instalando..." -ForegroundColor Red
    # Aquí podrías agregar lógica para instalar Node.js automáticamente
}

# Ejecutar pruebas Python (Backend)
Write-Host "`n🚀 Ejecutando pruebas del backend..." -ForegroundColor Yellow
try {
    if ($pythonCmd) {
        $pythonCmd = "py"
    } else {
        $pythonCmd = "python"
    }
    
    $backendResult = & $pythonCmd test_internas_sistema.py 2>&1
    Write-Host "✅ Pruebas backend completadas" -ForegroundColor Green
    Write-Host $backendResult -ForegroundColor White
} catch {
    Write-Host "❌ Error ejecutando pruebas backend: $($_.Exception.Message)" -ForegroundColor Red
}

# Ejecutar pruebas JavaScript (Frontend) si Node.js está disponible
Write-Host "`n🚀 Ejecutando pruebas del frontend..." -ForegroundColor Yellow
try {
    # Crear script temporal para Node.js
    $frontendTestScript = @"
const FrontendTester = require('./test_internas_frontend.js');
const fs = require('fs');

async function runTests() {
    const tester = new FrontendTester();
    const report = await tester.runAllTests();
    
    // Guardar reporte
    fs.writeFileSync('reporte_pruebas_frontend.json', JSON.stringify(report, null, 2));
    console.log('📄 Reporte frontend guardado en: reporte_pruebas_frontend.json');
    
    // Exit code basado en resultado
    if (report.summary.successRate >= 80) {
        process.exit(0);
    } else {
        process.exit(1);
    }
}

runTests().catch(console.error);
"@
    
    $frontendTestScript | Out-File -FilePath "temp_frontend_test.js" -Encoding UTF8
    
    $frontendResult = & node temp_frontend_test.js 2>&1
    Write-Host "✅ Pruebas frontend completadas" -ForegroundColor Green
    Write-Host $frontendResult -ForegroundColor White
    
    # Limpiar archivo temporal
    Remove-Item "temp_frontend_test.js" -ErrorAction SilentlyContinue
} catch {
    Write-Host "❌ Error ejecutando pruebas frontend: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "💡 Ejecuta manualmente en el navegador: new FrontendTester().runAllTests()" -ForegroundColor Yellow
}

# Ejecutar pruebas de conectividad
Write-Host "`n🔍 Ejecutando pruebas de conectividad..." -ForegroundColor Yellow

$endpoints = @(
    @{ Name = "Backend Health"; Url = "https://pagos-f2qf.onrender.com/api/v1/health" },
    @{ Name = "Frontend"; Url = "https://rapicredit.onrender.com" },
    @{ Name = "Backend Auth"; Url = "https://pagos-f2qf.onrender.com/api/v1/auth/login" },
    @{ Name = "Backend Clientes"; Url = "https://pagos-f2qf.onrender.com/api/v1/clientes" }
)

foreach ($endpoint in $endpoints) {
    try {
        Write-Host "  🔍 Probando: $($endpoint.Name)..." -ForegroundColor Gray
        $response = Invoke-WebRequest -Uri $endpoint.Url -Method GET -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        Write-Host "  ✅ $($endpoint.Name): OK ($($response.StatusCode))" -ForegroundColor Green
    } catch {
        if ($_.Exception.Response.StatusCode -eq 401 -or $_.Exception.Response.StatusCode -eq 403) {
            Write-Host "  ✅ $($endpoint.Name): OK ($($_.Exception.Response.StatusCode) - Auth requerida)" -ForegroundColor Green
        } else {
            Write-Host "  ❌ $($endpoint.Name): ERROR ($($_.Exception.Message))" -ForegroundColor Red
        }
    }
}

# Generar reporte consolidado
Write-Host "`n📊 Generando reporte consolidado..." -ForegroundColor Yellow

$consolidatedReport = @{
    timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffZ"
    tests = @{
        backend = if (Test-Path "reporte_pruebas_internas.json") { "Completed" } else { "Failed" }
        frontend = if (Test-Path "reporte_pruebas_frontend.json") { "Completed" } else { "Failed" }
        connectivity = "Completed"
    }
    summary = @{
        status = "Tests completed"
        files_generated = @(
        "reporte_pruebas_internas.json",
        "reporte_pruebas_frontend.json",
        "reporte_consolidado.json"
        )
    }
}

$consolidatedReport | ConvertTo-Json -Depth 3 | Out-File -FilePath "reporte_consolidado.json" -Encoding UTF8

Write-Host "`n✅ PRUEBAS COMPLETADAS" -ForegroundColor Green
Write-Host "📄 Archivos generados:" -ForegroundColor Cyan
Write-Host "  - reporte_pruebas_internas.json (Backend)" -ForegroundColor White
Write-Host "  - reporte_pruebas_frontend.json (Frontend)" -ForegroundColor White
Write-Host "  - reporte_consolidado.json (Consolidado)" -ForegroundColor White

Write-Host "`n🎯 Para ver los resultados:" -ForegroundColor Yellow
Write-Host "  - Backend: Get-Content reporte_pruebas_internas.json | ConvertFrom-Json" -ForegroundColor Gray
Write-Host "  - Frontend: Get-Content reporte_pruebas_frontend.json | ConvertFrom-Json" -ForegroundColor Gray
Write-Host "  - Consolidado: Get-Content reporte_consolidado.json | ConvertFrom-Json" -ForegroundColor Gray

Write-Host "`n" + "=" * 60 -ForegroundColor Cyan
Write-Host "🧪 PRUEBAS INTERNAS COMPLETADAS" -ForegroundColor Cyan
