# Script para solucionar error de serialización en Cursor
Write-Host "=== SOLUCION ERROR DE SERIALIZACION CURSOR ===" -ForegroundColor Cyan
Write-Host ""

# 1. Cerrar todos los procesos de Cursor
Write-Host "1. Cerrando procesos de Cursor..." -ForegroundColor Yellow
$cursorProcesses = Get-Process -Name "Cursor" -ErrorAction SilentlyContinue
if ($cursorProcesses) {
    Write-Host "   Encontrados $($cursorProcesses.Count) proceso(s) de Cursor" -ForegroundColor Yellow
    $cursorProcesses | Stop-Process -Force
    Start-Sleep -Seconds 3
    Write-Host "   OK: Todos los procesos cerrados" -ForegroundColor Green
} else {
    Write-Host "   OK: No hay procesos de Cursor ejecutándose" -ForegroundColor Green
}

# 2. Limpiar cache de Cursor
Write-Host ""
Write-Host "2. Limpiando cache de Cursor..." -ForegroundColor Yellow
$cachePaths = @(
    "$env:APPDATA\Cursor\Cache",
    "$env:APPDATA\Cursor\Code Cache",
    "$env:APPDATA\Cursor\GPUCache",
    "$env:LOCALAPPDATA\Cursor\Cache",
    "$env:LOCALAPPDATA\Cursor\Code Cache",
    "$env:LOCALAPPDATA\Cursor\GPUCache",
    "$env:LOCALAPPDATA\Cursor\User\Cache",
    "$env:LOCALAPPDATA\Cursor\User\Code Cache",
    "$env:LOCALAPPDATA\Cursor\User\GPUCache",
    "$env:LOCALAPPDATA\Cursor\CachedData"
)

$cleanedCount = 0
foreach ($cachePath in $cachePaths) {
    if (Test-Path $cachePath) {
        try {
            Remove-Item -Path "$cachePath\*" -Recurse -Force -ErrorAction SilentlyContinue
            $cleanedCount++
            Write-Host "   Limpiado: $cachePath" -ForegroundColor Gray
        } catch {
            Write-Host "   Advertencia: No se pudo limpiar $cachePath" -ForegroundColor Yellow
        }
    }
}
Write-Host "   OK: $cleanedCount directorios de cache limpiados" -ForegroundColor Green

# 3. Limpiar configuración de workspace que puede causar problemas
Write-Host ""
Write-Host "3. Verificando configuración de workspace..." -ForegroundColor Yellow
$workspaceSettings = "$PWD\.vscode\settings.json"
if (Test-Path $workspaceSettings) {
    Write-Host "   INFO: Archivo de configuración encontrado: $workspaceSettings" -ForegroundColor Cyan
    Write-Host "   (No se modificará, solo se informa)" -ForegroundColor Gray
} else {
    Write-Host "   INFO: No hay archivo de configuración de workspace" -ForegroundColor Gray
}

# 4. Limpiar cache DNS
Write-Host ""
Write-Host "4. Limpiando cache DNS..." -ForegroundColor Yellow
ipconfig /flushdns | Out-Null
Write-Host "   OK: Cache DNS limpiado" -ForegroundColor Green

# 5. Verificar versión de Cursor
Write-Host ""
Write-Host "5. Verificando versión de Cursor..." -ForegroundColor Yellow
$cursorExe = "C:\Program Files\Cursor\Cursor.exe"
if (Test-Path $cursorExe) {
    $versionInfo = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($cursorExe)
    Write-Host "   Versión actual: $($versionInfo.FileVersion)" -ForegroundColor Green
    Write-Host "   IMPORTANTE: Verifica si hay actualizaciones disponibles" -ForegroundColor Yellow
} else {
    Write-Host "   ADVERTENCIA: No se encontró Cursor.exe" -ForegroundColor Yellow
}

# 6. Verificar archivos grandes en el proyecto que puedan causar problemas
Write-Host ""
Write-Host "6. Verificando archivos grandes (>10MB) que puedan causar problemas..." -ForegroundColor Yellow
$largeFiles = Get-ChildItem -Path $PWD -Recurse -File -ErrorAction SilentlyContinue | 
    Where-Object { $_.Length -gt 10MB -and $_.Extension -notin @('.git', '.node_modules') } | 
    Select-Object -First 5 FullName, @{Name="SizeMB";Expression={[math]::Round($_.Length/1MB, 2)}}

if ($largeFiles) {
    Write-Host "   ADVERTENCIA: Se encontraron archivos grandes:" -ForegroundColor Yellow
    $largeFiles | ForEach-Object {
        Write-Host "   - $($_.FullName): $($_.SizeMB) MB" -ForegroundColor Gray
    }
    Write-Host "   SUGERENCIA: Cierra estos archivos en Cursor si están abiertos" -ForegroundColor Yellow
} else {
    Write-Host "   OK: No se encontraron archivos problemáticamente grandes" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== SOLUCIONES APLICADAS ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ Procesos de Cursor cerrados" -ForegroundColor Green
Write-Host "✅ Cache limpiado" -ForegroundColor Green
Write-Host "✅ DNS cache limpiado" -ForegroundColor Green
Write-Host ""
Write-Host "=== SIGUIENTES PASOS ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. ESPERA 10 SEGUNDOS antes de abrir Cursor" -ForegroundColor Yellow
Write-Host ""
Write-Host "2. ABRE CURSOR NUEVAMENTE:" -ForegroundColor Yellow
Write-Host "   - Abre Cursor normalmente" -ForegroundColor White
Write-Host "   - Espera a que cargue completamente" -ForegroundColor White
Write-Host ""
Write-Host "3. VERIFICA ACTUALIZACIONES:" -ForegroundColor Yellow
Write-Host "   - Ve a: Help > Check for Updates" -ForegroundColor White
Write-Host "   - Si hay actualización, instálala" -ForegroundColor White
Write-Host ""
Write-Host "4. SI EL ERROR PERSISTE:" -ForegroundColor Yellow
Write-Host "   - Cierra archivos grandes que tengas abiertos" -ForegroundColor White
Write-Host "   - Reduce el número de pestañas abiertas" -ForegroundColor White
Write-Host "   - Intenta con un workspace más pequeño primero" -ForegroundColor White
Write-Host ""
Write-Host "5. SOLUCION ALTERNATIVA:" -ForegroundColor Yellow
Write-Host "   - Descarga la última versión desde: https://cursor.com/downloads" -ForegroundColor White
Write-Host "   - Reinstala Cursor completamente" -ForegroundColor White
Write-Host ""
Write-Host "=== PROCESO COMPLETADO ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Presiona cualquier tecla para continuar..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
