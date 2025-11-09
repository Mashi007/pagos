# Script para solucionar error de serializacion en Cursor
Write-Host "=== SOLUCION ERROR DE SERIALIZACION CURSOR ===" -ForegroundColor Cyan
Write-Host ""

# 1. Cerrar procesos de Cursor
Write-Host "1. Cerrando procesos de Cursor..." -ForegroundColor Yellow
$cursorProcesses = Get-Process -Name "Cursor" -ErrorAction SilentlyContinue
if ($cursorProcesses) {
    Write-Host "   Encontrados $($cursorProcesses.Count) proceso(s)" -ForegroundColor Cyan
    $cursorProcesses | Stop-Process -Force
    Start-Sleep -Seconds 3
    Write-Host "   OK: Procesos cerrados" -ForegroundColor Green
} else {
    Write-Host "   INFO: No hay procesos ejecutandose" -ForegroundColor Gray
}

# 2. Limpiar cache
Write-Host ""
Write-Host "2. Limpiando cache de Cursor..." -ForegroundColor Yellow
$cachePaths = @(
    "$env:APPDATA\Cursor\Cache",
    "$env:APPDATA\Cursor\Code Cache",
    "$env:LOCALAPPDATA\Cursor\Cache",
    "$env:LOCALAPPDATA\Cursor\Code Cache"
)

$totalCleaned = 0
foreach ($cachePath in $cachePaths) {
    if (Test-Path $cachePath) {
        try {
            $items = Get-ChildItem -Path $cachePath -Recurse -Force -ErrorAction SilentlyContinue
            $count = $items.Count
            Remove-Item -Path "$cachePath\*" -Recurse -Force -ErrorAction SilentlyContinue
            $totalCleaned += $count
            Write-Host "   OK: Limpiado $count archivos" -ForegroundColor Green
        } catch {
            Write-Host "   ADVERTENCIA: No se pudo limpiar" -ForegroundColor Yellow
        }
    }
}

if ($totalCleaned -gt 0) {
    Write-Host "   RESUMEN: $totalCleaned archivos eliminados" -ForegroundColor Cyan
}

# 3. Limpiar DNS
Write-Host ""
Write-Host "3. Limpiando cache DNS..." -ForegroundColor Yellow
ipconfig /flushdns | Out-Null
Write-Host "   OK: DNS limpiado" -ForegroundColor Green

# 4. Verificar version
Write-Host ""
Write-Host "4. Verificando version de Cursor..." -ForegroundColor Yellow
$cursorExe = "C:\Program Files\Cursor\Cursor.exe"
if (Test-Path $cursorExe) {
    try {
        $versionInfo = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($cursorExe)
        Write-Host "   Version actual: $($versionInfo.FileVersion)" -ForegroundColor Cyan
    } catch {
        Write-Host "   No se pudo obtener la version" -ForegroundColor Yellow
    }
}

# 5. Recomendaciones
Write-Host ""
Write-Host "=== RECOMENDACIONES ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. ACTUALIZAR CURSOR:" -ForegroundColor Yellow
Write-Host "   - Abre Cursor" -ForegroundColor White
Write-Host "   - Menu: Help -> Check for Updates" -ForegroundColor White
Write-Host ""
Write-Host "2. REINICIAR COMPUTADORA:" -ForegroundColor Yellow
Write-Host "   - Reinicia completamente" -ForegroundColor White
Write-Host ""
Write-Host "3. REDUCIR CONTEXTO:" -ForegroundColor Yellow
Write-Host "   - Cierra pestañas de archivos grandes" -ForegroundColor White
Write-Host "   - Reduce archivos abiertos" -ForegroundColor White
Write-Host ""
Write-Host "=== PROCESO COMPLETADO ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Espera 10 segundos y abre Cursor nuevamente" -ForegroundColor Yellow

