# Script para organizar archivos .md existentes en Documentos por fecha
# Mueve archivos de Documentos/General, Documentos/Auditorias, etc. a subcarpetas por fecha

param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$rootPath = (Resolve-Path ($PSScriptRoot + "\..")).Path
Set-Location $rootPath

Write-Host ""
Write-Host "ORGANIZADOR DE DOCUMENTOS POR FECHA" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$documentosPath = Join-Path $rootPath "Documentos"
$subfolders = @("General", "Auditorias", "Analisis", "Desarrollo", "Testing", "Configuracion")

$moved = 0
$skipped = 0

foreach ($subfolder in $subfolders) {
    $folderPath = Join-Path $documentosPath $subfolder
    
    if (-not (Test-Path $folderPath)) {
        continue
    }
    
    # Obtener archivos .md directamente en la carpeta (no en subcarpetas)
    $mdFiles = Get-ChildItem -Path $folderPath -Filter "*.md" -File | Where-Object {
        $_.Name -ne "README.md" -and
        $_.DirectoryName -eq $folderPath
    }
    
    foreach ($file in $mdFiles) {
        # Obtener fecha de modificación del archivo
        $lastModified = $file.LastWriteTime
        $yearMonth = $lastModified.ToString("yyyy-MM")
        
        # Crear estructura por fecha
        $dateFolder = Join-Path $folderPath $yearMonth
        $destinationFile = Join-Path $dateFolder $file.Name
        
        # Verificar si ya está en la ubicación correcta
        if ($file.FullName -eq $destinationFile) {
            $skipped++
            continue
        }
        
        # Crear carpeta si no existe
        if (-not (Test-Path $dateFolder)) {
            if (-not $DryRun) {
                New-Item -ItemType Directory -Path $dateFolder -Force | Out-Null
            }
        }
        
        # Verificar si el archivo destino ya existe
        if (Test-Path $destinationFile) {
            Write-Host "  [WARN] $($file.Name) (ya existe en destino, omitiendo)" -ForegroundColor Yellow
            $skipped++
            continue
        }
        
        # Mover archivo
        if ($DryRun) {
            Write-Host "  [DRY RUN] Moveria: $($file.Name)" -ForegroundColor Magenta
            Write-Host "    De: $($file.FullName)" -ForegroundColor Gray
            Write-Host "    A:  $destinationFile" -ForegroundColor Gray
            $moved++
        }
        else {
            try {
                Move-Item -Path $file.FullName -Destination $destinationFile -Force
                Write-Host "  [OK] $($file.Name) -> $subfolder\$yearMonth" -ForegroundColor Green
                $moved++
            }
            catch {
                Write-Host "  [ERROR] Error moviendo $($file.Name): $_" -ForegroundColor Red
            }
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "RESUMEN" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "  Archivos a mover: $moved" -ForegroundColor Magenta
    Write-Host "  Archivos omitidos: $skipped" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  [MODO DRY RUN - No se movieron archivos]" -ForegroundColor Yellow
}
else {
    Write-Host "  Archivos movidos: $moved" -ForegroundColor Green
    Write-Host "  Archivos omitidos: $skipped" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  [OK] Proceso completado" -ForegroundColor Green
}

Write-Host ""

