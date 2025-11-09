# Script para verificar y actualizar Cursor IDE
Write-Host "=== ACTUALIZACION DE CURSOR IDE ===" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar si Cursor está instalado
Write-Host "1. Verificando instalación de Cursor..." -ForegroundColor Yellow
$cursorPaths = @(
    "C:\Program Files\Cursor\Cursor.exe",
    "C:\Program Files (x86)\Cursor\Cursor.exe",
    "$env:LOCALAPPDATA\Programs\Cursor\Cursor.exe"
)

$cursorPath = $null
foreach ($path in $cursorPaths) {
    if (Test-Path $path) {
        $cursorPath = $path
        Write-Host "   OK: Cursor encontrado en: $path" -ForegroundColor Green
        break
    }
}

if (-not $cursorPath) {
    Write-Host "   ADVERTENCIA: No se encontró Cursor en las rutas estándar" -ForegroundColor Yellow
    Write-Host "   Puede estar instalado en otra ubicación" -ForegroundColor Yellow
}

# 2. Verificar versión actual si es posible
Write-Host ""
Write-Host "2. Verificando versión actual..." -ForegroundColor Yellow
if ($cursorPath) {
    try {
        $versionInfo = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($cursorPath)
        Write-Host "   Versión actual: $($versionInfo.FileVersion)" -ForegroundColor Green
        Write-Host "   Producto: $($versionInfo.ProductName)" -ForegroundColor Cyan
    } catch {
        Write-Host "   No se pudo obtener la versión del archivo" -ForegroundColor Yellow
    }
}

# 3. Verificar si Cursor está ejecutándose
Write-Host ""
Write-Host "3. Verificando procesos de Cursor..." -ForegroundColor Yellow
$cursorProcesses = Get-Process -Name "Cursor" -ErrorAction SilentlyContinue
if ($cursorProcesses) {
    Write-Host "   ADVERTENCIA: Cursor está ejecutándose" -ForegroundColor Yellow
    Write-Host "   Cierra Cursor antes de actualizar para evitar conflictos" -ForegroundColor Yellow
    $response = Read-Host "   ¿Deseas cerrar Cursor ahora? (S/N)"
    if ($response -eq "S" -or $response -eq "s") {
        Write-Host "   Cerrando procesos de Cursor..." -ForegroundColor Yellow
        $cursorProcesses | Stop-Process -Force
        Start-Sleep -Seconds 2
        Write-Host "   OK: Cursor cerrado" -ForegroundColor Green
    }
} else {
    Write-Host "   OK: Cursor no está ejecutándose" -ForegroundColor Green
}

# 4. Instrucciones para actualizar
Write-Host ""
Write-Host "=== OPCIONES PARA ACTUALIZAR CURSOR ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "OPCION 1: Actualizar desde Cursor (Recomendado)" -ForegroundColor Yellow
Write-Host "   1. Abre Cursor" -ForegroundColor White
Write-Host "   2. Presiona Ctrl+Shift+J para abrir la configuración" -ForegroundColor White
Write-Host "   3. O ve a: Help > Check for Updates" -ForegroundColor White
Write-Host "   4. Si hay actualizaciones disponibles, haz clic en 'Update'" -ForegroundColor White
Write-Host ""
Write-Host "OPCION 2: Descargar e instalar manualmente" -ForegroundColor Yellow
Write-Host "   1. Visita: https://cursor.com/downloads" -ForegroundColor White
Write-Host "   2. Descarga la última versión para Windows" -ForegroundColor White
Write-Host "   3. Ejecuta el instalador (sobrescribirá la versión actual)" -ForegroundColor White
Write-Host ""
Write-Host "OPCION 3: Usar winget (si está disponible)" -ForegroundColor Yellow
Write-Host "   winget upgrade Cursor.Cursor" -ForegroundColor White
Write-Host ""

# 5. Verificar si winget está disponible
Write-Host "5. Verificando si winget está disponible..." -ForegroundColor Yellow
try {
    $wingetVersion = winget --version 2>$null
    if ($wingetVersion) {
        Write-Host "   OK: winget está disponible" -ForegroundColor Green
        Write-Host ""
        $useWinget = Read-Host "   ¿Deseas intentar actualizar con winget ahora? (S/N)"
        if ($useWinget -eq "S" -or $useWinget -eq "s") {
            Write-Host "   Ejecutando: winget upgrade Cursor.Cursor" -ForegroundColor Yellow
            winget upgrade Cursor.Cursor
        }
    } else {
        Write-Host "   INFO: winget no está disponible en este sistema" -ForegroundColor Gray
    }
} catch {
    Write-Host "   INFO: winget no está disponible en este sistema" -ForegroundColor Gray
}

# 6. Limpiar cache antes de actualizar (opcional)
Write-Host ""
Write-Host "6. Limpieza de cache (opcional)..." -ForegroundColor Yellow
$cleanCache = Read-Host "   ¿Deseas limpiar el cache de Cursor antes de actualizar? (S/N)"
if ($cleanCache -eq "S" -or $cleanCache -eq "s") {
    Write-Host "   Limpiando cache..." -ForegroundColor Yellow
    $cachePaths = @(
        "$env:APPDATA\Cursor\Cache",
        "$env:LOCALAPPDATA\Cursor\Cache"
    )
    
    foreach ($cachePath in $cachePaths) {
        if (Test-Path $cachePath) {
            try {
                Remove-Item -Path "$cachePath\*" -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "   OK: Cache limpiado en $cachePath" -ForegroundColor Green
            } catch {
                Write-Host "   ADVERTENCIA: No se pudo limpiar $cachePath" -ForegroundColor Yellow
            }
        }
    }
    
    # Limpiar DNS cache
    ipconfig /flushdns | Out-Null
    Write-Host "   OK: Cache DNS limpiado" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== INSTRUCCIONES FINALES ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Después de actualizar Cursor:" -ForegroundColor Yellow
Write-Host "   1. Reinicia Cursor completamente" -ForegroundColor White
Write-Host "   2. Verifica la versión en Help > About" -ForegroundColor White
Write-Host "   3. Si el error persiste, revisa los logs en:" -ForegroundColor White
Write-Host "      %LOCALAPPDATA%\Cursor\logs" -ForegroundColor Gray
Write-Host ""
Write-Host "=== PROCESO COMPLETADO ===" -ForegroundColor Cyan




