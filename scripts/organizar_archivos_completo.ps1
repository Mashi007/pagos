# Script para organizar archivos .md y .sql
# Organiza .md en Documentos por fecha
# Organiza .sql en scripts/sql

param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$rootPath = (Resolve-Path ($PSScriptRoot + "\..")).Path
Set-Location $rootPath

Write-Host ""
Write-Host "ORGANIZADOR DE ARCHIVOS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ============================================
# 1. ORGANIZAR ARCHIVOS .MD
# ============================================
Write-Host "Organizando archivos .md..." -ForegroundColor Yellow

$mdFilesInRoot = Get-ChildItem -Path $rootPath -Filter "*.md" -File | Where-Object { 
    $_.Name -ne "README.md" -and 
    (Resolve-Path $_.DirectoryName).Path -eq (Resolve-Path $rootPath).Path
}

$movedMD = 0
$skippedMD = 0

foreach ($file in $mdFilesInRoot) {
    $filename = $file.Name
    
    # Determinar carpeta destino basada en nombre
    $destinationFolder = "Documentos\General"
    
    if ($filename -match "AUDITORIA") {
        $destinationFolder = "Documentos\Auditorias"
    }
    elseif ($filename -match "ANALISIS") {
        $destinationFolder = "Documentos\Analisis"
    }
    
    # Obtener fecha de modificación del archivo
    $lastModified = $file.LastWriteTime
    $yearMonth = $lastModified.ToString("yyyy-MM")
    
    # Crear estructura por fecha: Documentos/General/2025-01/
    $dateFolder = Join-Path $destinationFolder $yearMonth
    
    $destinationPath = Join-Path $rootPath $dateFolder
    $destinationFile = Join-Path $destinationPath $filename
    
    # Verificar si ya está en la ubicación correcta
    if ($file.FullName -eq $destinationFile) {
        Write-Host "  [OK] $filename (ya esta en ubicacion correcta)" -ForegroundColor Green
        $skippedMD++
        continue
    }
    
    # Crear carpeta si no existe
    if (-not (Test-Path $destinationPath)) {
        if (-not $DryRun) {
            New-Item -ItemType Directory -Path $destinationPath -Force | Out-Null
            Write-Host "  [INFO] Carpeta creada: $dateFolder" -ForegroundColor Cyan
        }
    }
    
    # Verificar si el archivo destino ya existe
    if (Test-Path $destinationFile) {
        Write-Host "  [WARN] $filename (ya existe en destino, omitiendo)" -ForegroundColor Yellow
        $skippedMD++
        continue
    }
    
    # Mover archivo
    if ($DryRun) {
        Write-Host "  [DRY RUN] Moveria: $filename" -ForegroundColor Magenta
        Write-Host "    De: $($file.FullName)" -ForegroundColor Gray
        Write-Host "    A:  $destinationFile" -ForegroundColor Gray
        $movedMD++
    }
    else {
        try {
            Move-Item -Path $file.FullName -Destination $destinationFile -Force
            Write-Host "  [OK] $filename -> $dateFolder" -ForegroundColor Green
            $movedMD++
        }
        catch {
            Write-Host "  [ERROR] Error moviendo $filename : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "  Archivos .md movidos: $movedMD" -ForegroundColor Green
Write-Host "  Archivos .md omitidos: $skippedMD" -ForegroundColor Yellow

# ============================================
# 2. ORGANIZAR ARCHIVOS .SQL
# ============================================
Write-Host ""
Write-Host "Organizando archivos .sql..." -ForegroundColor Yellow

$sqlTargetFolder = Join-Path $rootPath "scripts\sql"

# Buscar archivos SQL fuera de scripts/sql
$sqlFiles = @()
$sqlFiles += Get-ChildItem -Path $rootPath -Filter "*.sql" -File -Recurse | Where-Object {
    $_.DirectoryName -notlike "*\node_modules\*" -and
    $_.DirectoryName -notlike "*\.git\*" -and
    $_.DirectoryName -notlike "*\migrations\*" -and
    $_.FullName -notlike "*\scripts\sql\*"
}

$movedSQL = 0
$skippedSQL = 0
$conflictsSQL = 0

foreach ($file in $sqlFiles) {
    $filename = $file.Name
    $destinationFile = Join-Path $sqlTargetFolder $filename
    
    # Verificar si ya está en scripts/sql
    if ($file.DirectoryName -eq $sqlTargetFolder) {
        Write-Host "  [OK] $filename (ya esta en scripts/sql)" -ForegroundColor Green
        $skippedSQL++
        continue
    }
    
    # Verificar si el archivo destino ya existe
    if (Test-Path $destinationFile) {
        # Si es el mismo archivo, omitir
        if ($file.FullName -eq $destinationFile) {
            $skippedSQL++
            continue
        }
        
        # Si hay conflicto, crear nombre único
        $baseName = [System.IO.Path]::GetFileNameWithoutExtension($filename)
        $extension = [System.IO.Path]::GetExtension($filename)
        $counter = 1
        $newFilename = "${baseName}_${counter}${extension}"
        $destinationFile = Join-Path $sqlTargetFolder $newFilename
        
        while (Test-Path $destinationFile) {
            $counter++
            $newFilename = "${baseName}_${counter}${extension}"
            $destinationFile = Join-Path $sqlTargetFolder $newFilename
        }
        
        Write-Host "  [WARN] $filename tiene conflicto, se renombrara a: $newFilename" -ForegroundColor Yellow
        $filename = $newFilename
        $conflictsSQL++
    }
    
    # Mover archivo
    if ($DryRun) {
        Write-Host "  [DRY RUN] Moveria: $($file.Name)" -ForegroundColor Magenta
        Write-Host "    De: $($file.FullName)" -ForegroundColor Gray
        Write-Host "    A:  scripts\sql\$filename" -ForegroundColor Gray
        $movedSQL++
    }
    else {
        try {
            if (-not (Test-Path $sqlTargetFolder)) {
                New-Item -ItemType Directory -Path $sqlTargetFolder -Force | Out-Null
            }
            Move-Item -Path $file.FullName -Destination $destinationFile -Force
            Write-Host "  [OK] $($file.Name) -> scripts\sql" -ForegroundColor Green
            $movedSQL++
        }
        catch {
            Write-Host "  [ERROR] Error moviendo $($file.Name): $_" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "  Archivos .sql movidos: $movedSQL" -ForegroundColor Green
Write-Host "  Archivos .sql omitidos: $skippedSQL" -ForegroundColor Yellow
if ($conflictsSQL -gt 0) {
    Write-Host "  Archivos .sql renombrados (conflictos): $conflictsSQL" -ForegroundColor Yellow
}

# ============================================
# RESUMEN FINAL
# ============================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "RESUMEN" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "  Archivos .md a mover: $movedMD" -ForegroundColor Magenta
    Write-Host "  Archivos .sql a mover: $movedSQL" -ForegroundColor Magenta
    Write-Host ""
    Write-Host "  [MODO DRY RUN - No se movieron archivos]" -ForegroundColor Yellow
}
else {
    Write-Host "  Archivos .md movidos: $movedMD" -ForegroundColor Green
    Write-Host "  Archivos .sql movidos: $movedSQL" -ForegroundColor Green
    Write-Host ""
    Write-Host "  [OK] Proceso completado" -ForegroundColor Green
}

Write-Host ""
