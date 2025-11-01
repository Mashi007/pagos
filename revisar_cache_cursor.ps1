# Script para revisar el estado del cache de Cursor
Write-Host "=== REVISION DEL CACHE DE CURSOR ===" -ForegroundColor Cyan
Write-Host ""

$cachePaths = @(
    "$env:APPDATA\Cursor\Cache",
    "$env:APPDATA\Cursor\Code Cache",
    "$env:APPDATA\Cursor\GPUCache",
    "$env:LOCALAPPDATA\Cursor\Cache",
    "$env:LOCALAPPDATA\Cursor\Code Cache",
    "$env:LOCALAPPDATA\Cursor\GPUCache",
    "$env:LOCALAPPDATA\Cursor\User\Cache",
    "$env:LOCALAPPDATA\Cursor\User\Code Cache",
    "$env:LOCALAPPDATA\Cursor\User\GPUCache"
)

$totalSize = 0
$existsCount = 0

foreach ($path in $cachePaths) {
    if (Test-Path $path) {
        $existsCount++
        try {
            $size = (Get-ChildItem -Path $path -Recurse -Force -ErrorAction SilentlyContinue | 
                    Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
            if (-not $size) { $size = 0 }
            $sizeMB = [math]::Round($size / 1MB, 2)
            $totalSize += $size
            $itemCount = (Get-ChildItem -Path $path -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object).Count
            Write-Host "EXISTE: $path" -ForegroundColor Green
            Write-Host "  Tamaño: $sizeMB MB" -ForegroundColor Yellow
            Write-Host "  Archivos: $itemCount" -ForegroundColor Yellow
        } catch {
            Write-Host "EXISTE: $path (error al calcular tamaño)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "NO EXISTE: $path" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "=== RESUMEN ===" -ForegroundColor Cyan
Write-Host "Directorios de cache encontrados: $existsCount de $($cachePaths.Count)" -ForegroundColor Yellow
Write-Host "Tamaño total del cache: $([math]::Round($totalSize / 1MB, 2)) MB" -ForegroundColor Yellow

# Verificar cache DNS de Windows
Write-Host ""
Write-Host "=== CACHE DNS DE WINDOWS ===" -ForegroundColor Cyan
$dnsEntries = ipconfig /displaydns | Select-String -Pattern "cursor" -CaseSensitive:$false
if ($dnsEntries) {
    Write-Host "ENTRADAS DNS RELACIONADAS CON CURSOR:" -ForegroundColor Yellow
    $dnsEntries | Select-Object -First 10 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
} else {
    Write-Host "No hay entradas DNS relacionadas con Cursor" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== FIN DE REVISION ===" -ForegroundColor Cyan

