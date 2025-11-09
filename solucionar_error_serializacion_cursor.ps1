# Script completo para solucionar error de serialización en Cursor
# Error: "Serialization error in aiserver.v1.StreamUnifiedChatRequestWithTools"

Write-Host "=== SOLUCION ERROR DE SERIALIZACION CURSOR ===" -ForegroundColor Cyan
Write-Host "Error: Serialization error in aiserver.v1.StreamUnifiedChatRequestWithTools" -ForegroundColor Yellow
Write-Host ""

# 1. Cerrar todos los procesos de Cursor
Write-Host "1. Cerrando procesos de Cursor..." -ForegroundColor Yellow
$cursorProcesses = Get-Process -Name "Cursor" -ErrorAction SilentlyContinue
if ($cursorProcesses) {
    Write-Host "   Encontrados $($cursorProcesses.Count) proceso(s) de Cursor" -ForegroundColor Cyan
    $cursorProcesses | Stop-Process -Force
    Start-Sleep -Seconds 3
    Write-Host "   OK: Todos los procesos de Cursor cerrados" -ForegroundColor Green
} else {
    Write-Host "   INFO: No hay procesos de Cursor ejecutándose" -ForegroundColor Gray
}

# 2. Limpiar cache de Cursor completamente
Write-Host ""
Write-Host "2. Limpiando cache de Cursor..." -ForegroundColor Yellow
$cachePaths = @(
    "$env:APPDATA\Cursor\Cache",
    "$env:APPDATA\Cursor\Code Cache",
    "$env:APPDATA\Cursor\GPUCache",
    "$env:APPDATA\Cursor\CachedData",
    "$env:LOCALAPPDATA\Cursor\Cache",
    "$env:LOCALAPPDATA\Cursor\Code Cache",
    "$env:LOCALAPPDATA\Cursor\GPUCache",
    "$env:LOCALAPPDATA\Cursor\CachedData",
    "$env:LOCALAPPDATA\Cursor\User\Cache",
    "$env:LOCALAPPDATA\Cursor\User\Code Cache",
    "$env:LOCALAPPDATA\Cursor\User\GPUCache",
    "$env:LOCALAPPDATA\Cursor\User\CachedData",
    "$env:LOCALAPPDATA\Cursor\logs\*.log"
)

$totalCleaned = 0
foreach ($cachePath in $cachePaths) {
    if (Test-Path $cachePath) {
        try {
            $items = Get-ChildItem -Path $cachePath -Recurse -Force -ErrorAction SilentlyContinue
            $count = $items.Count
            $size = ($items | Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
            Remove-Item -Path "$cachePath\*" -Recurse -Force -ErrorAction SilentlyContinue
            $totalCleaned += $count
            Write-Host "   OK: Limpiado $count archivos de $cachePath" -ForegroundColor Green
        } catch {
            Write-Host "   ADVERTENCIA: No se pudo limpiar $cachePath" -ForegroundColor Yellow
        }
    }
}

if ($totalCleaned -gt 0) {
    Write-Host "   RESUMEN: $totalCleaned archivos de cache eliminados" -ForegroundColor Cyan
} else {
    Write-Host "   INFO: No se encontraron archivos de cache para limpiar" -ForegroundColor Gray
}

# 3. Limpiar cache DNS de Windows
Write-Host ""
Write-Host "3. Limpiando cache DNS de Windows..." -ForegroundColor Yellow
ipconfig /flushdns | Out-Null
Write-Host "   OK: Cache DNS limpiado" -ForegroundColor Green

# 4. Verificar y limpiar configuración de Cursor problemática
Write-Host ""
Write-Host "4. Verificando configuración de Cursor..." -ForegroundColor Yellow
$configPath = "$env:APPDATA\Cursor\User\settings.json"
if (Test-Path $configPath) {
    try {
        $config = Get-Content $configPath -Raw | ConvertFrom-Json
        Write-Host "   OK: Configuración encontrada" -ForegroundColor Green
        
        # Verificar si hay configuraciones que puedan causar problemas
        $problematicSettings = @()
        if ($config.'ai.chat.maxTokens' -gt 100000) {
            $problematicSettings += "ai.chat.maxTokens demasiado alto"
        }
        
        if ($problematicSettings.Count -gt 0) {
            Write-Host "   ADVERTENCIA: Configuraciones potencialmente problemáticas:" -ForegroundColor Yellow
            $problematicSettings | ForEach-Object { Write-Host "     - $_" -ForegroundColor Yellow }
        } else {
            Write-Host "   OK: Configuración parece correcta" -ForegroundColor Green
        }
    } catch {
        Write-Host "   INFO: No se pudo leer la configuración (puede estar corrupta)" -ForegroundColor Yellow
    }
}

# 5. Verificar espacio en disco
Write-Host ""
Write-Host "5. Verificando espacio en disco..." -ForegroundColor Yellow
$drive = (Get-Location).Drive.Name
$disk = Get-PSDrive $drive
$freeSpaceGB = [math]::Round($disk.Free / 1GB, 2)
if ($freeSpaceGB -lt 1) {
    Write-Host "   ADVERTENCIA: Menos de 1 GB de espacio libre ($freeSpaceGB GB)" -ForegroundColor Red
    Write-Host "   Esto puede causar problemas de serialización" -ForegroundColor Red
} else {
    Write-Host "   OK: $freeSpaceGB GB de espacio libre disponible" -ForegroundColor Green
}

# 6. Verificar conectividad a servicios de Cursor
Write-Host ""
Write-Host "6. Verificando conectividad a servicios de Cursor..." -ForegroundColor Yellow
$testHosts = @("cursor.sh", "api.cursor.sh")
foreach ($host in $testHosts) {
    try {
        $dns = Resolve-DnsName -Name $host -ErrorAction Stop
        $testConnection = Test-NetConnection -ComputerName $host -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue
        if ($testConnection) {
            Write-Host "   OK: $host accesible" -ForegroundColor Green
        } else {
            Write-Host "   ERROR: $host no accesible en puerto 443" -ForegroundColor Red
        }
    } catch {
        Write-Host "   ERROR: No se puede resolver $host" -ForegroundColor Red
    }
}

# 7. Verificar archivos grandes en el workspace que puedan causar problemas
Write-Host ""
Write-Host "7. Verificando archivos grandes en el workspace..." -ForegroundColor Yellow
$largeFiles = Get-ChildItem -Path (Get-Location) -Recurse -File -ErrorAction SilentlyContinue | 
    Where-Object { $_.Length -gt 10MB } | 
    Sort-Object Length -Descending | 
    Select-Object -First 10

if ($largeFiles) {
    Write-Host "   ADVERTENCIA: Archivos grandes encontrados (>10MB):" -ForegroundColor Yellow
    $largeFiles | ForEach-Object {
        $sizeMB = [math]::Round($_.Length / 1MB, 2)
        Write-Host "     - $($_.Name): $sizeMB MB" -ForegroundColor Yellow
    }
    Write-Host "   NOTA: Archivos muy grandes pueden causar problemas de serialización" -ForegroundColor Yellow
} else {
    Write-Host "   OK: No se encontraron archivos excesivamente grandes" -ForegroundColor Green
}

# 8. Verificar versión de Cursor
Write-Host ""
Write-Host "8. Verificando versión de Cursor..." -ForegroundColor Yellow
$cursorExe = "C:\Program Files\Cursor\Cursor.exe"
if (Test-Path $cursorExe) {
    try {
        $versionInfo = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($cursorExe)
        Write-Host "   Versión actual: $($versionInfo.FileVersion)" -ForegroundColor Cyan
        Write-Host "   RECOMENDACIÓN: Verifica si hay actualizaciones disponibles" -ForegroundColor Yellow
        Write-Host '   Menú: Help > Check for Updates' -ForegroundColor White
    } catch {
        Write-Host "   No se pudo obtener la versión" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ADVERTENCIA: Cursor.exe no encontrado en ruta estándar" -ForegroundColor Yellow
}

# 9. Recomendaciones finales
Write-Host ""
Write-Host "=== RECOMENDACIONES ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. ACTUALIZAR CURSOR:" -ForegroundColor Yellow
Write-Host "   - Abre Cursor" -ForegroundColor White
Write-Host '   - Ve a: Help > Check for Updates' -ForegroundColor White
Write-Host "   - Instala cualquier actualización disponible" -ForegroundColor White
Write-Host ""
Write-Host "2. REINICIAR COMPUTADORA:" -ForegroundColor Yellow
Write-Host "   - Reinicia completamente tu computadora" -ForegroundColor White
Write-Host "   - Esto limpia procesos en segundo plano que pueden interferir" -ForegroundColor White
Write-Host ""
Write-Host "3. VERIFICAR EXTENSIONES:" -ForegroundColor Yellow
Write-Host "   - Desactiva extensiones recientemente instaladas" -ForegroundColor White
Write-Host "   - Algunas extensiones pueden causar problemas de serialización" -ForegroundColor White
Write-Host ""
Write-Host "4. REDUCIR CONTEXTO:" -ForegroundColor Yellow
Write-Host "   - Cierra pestañas de archivos grandes" -ForegroundColor White
Write-Host "   - Cierra ventanas de Cursor que no uses" -ForegroundColor White
Write-Host "   - Reduce el número de archivos abiertos" -ForegroundColor White
Write-Host ""
Write-Host "5. VERIFICAR LOGS:" -ForegroundColor Yellow
Write-Host "   - Revisa logs en: $env:LOCALAPPDATA\Cursor\logs" -ForegroundColor White
Write-Host "   - Busca errores relacionados con serialización" -ForegroundColor White
Write-Host ""
Write-Host "6. CONTACTAR SOPORTE:" -ForegroundColor Yellow
Write-Host "   - Si el problema persiste, contacta al soporte de Cursor" -ForegroundColor White
Write-Host "   - Incluye el Request ID: 2a9c2992-b86e-4944-96f8-4f92130b2cb1" -ForegroundColor White
Write-Host ""
Write-Host "=== PROCESO COMPLETADO ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "PRÓXIMOS PASOS:" -ForegroundColor Yellow
Write-Host "1. Espera 10 segundos" -ForegroundColor White
Write-Host "2. Abre Cursor nuevamente" -ForegroundColor White
Write-Host "3. Intenta la operación que causaba el error" -ForegroundColor White
Write-Host "4. Si el error persiste, reinicia tu computadora" -ForegroundColor White
Write-Host ""

