# Script para organizar todos los archivos .sql en una carpeta centralizada
# Uso: .\scripts\organizar_sql.ps1

param(
    [switch]$DryRun = $false,           # Solo muestra lo que haría sin mover archivos
    [string]$RootPath = ".",            # Ruta raíz del proyecto
    [string]$TargetFolder = "scripts\sql"  # Carpeta destino para archivos SQL
)

# Colores para output
$Info = "Cyan"
$Success = "Green"
$Warning = "Yellow"
$Error = "Red"

Write-Host "`nORGANIZADOR DE ARCHIVOS SQL`n" -ForegroundColor $Info

# Carpetas que deben mantenerse en su ubicación actual (archivos SQL de sistema)
$excludedFolders = @(
    "node_modules",
    ".git",
    "migrations"  # Mantener migrations en su lugar ya que son parte del sistema de migración
)

# Archivos que no deben moverse (pueden ser migraciones automáticas)
$excludedPatterns = @(
    "*migration*.sql",
    "*migrations*.sql"
)

# Contadores
$moved = 0
$skipped = 0
$errors = 0
$conflicts = 0

# Buscar todos los archivos .sql
Write-Host "Buscando archivos .sql..." -ForegroundColor $Info

$sqlFiles = Get-ChildItem -Path $RootPath -Filter "*.sql" -Recurse -File | Where-Object {
    $fullPath = $_.FullName
    $shouldProcess = $true
    
    # Verificar si está en carpeta excluida
    foreach ($excluded in $excludedFolders) {
        if ($fullPath -like "*\$excluded\*") {
            $shouldProcess = $false
            break
        }
    }
    
    # Verificar patrones excluidos
    if ($shouldProcess) {
        foreach ($pattern in $excludedPatterns) {
            if ($_.Name -like $pattern) {
                $shouldProcess = $false
                break
            }
        }
    }
    
    return $shouldProcess
}

Write-Host "   Encontrados: $($sqlFiles.Count) archivos`n" -ForegroundColor $Info

if ($sqlFiles.Count -eq 0) {
    Write-Host "No se encontraron archivos SQL para organizar.`n" -ForegroundColor $Warning
    exit 0
}

# Crear carpeta destino
$destinationPath = Join-Path $RootPath $TargetFolder

if (-not (Test-Path $destinationPath)) {
    if (-not $DryRun) {
        New-Item -ItemType Directory -Path $destinationPath -Force | Out-Null
        Write-Host "[INFO] Carpeta creada: $TargetFolder" -ForegroundColor $Info
    } else {
        Write-Host "[DRY RUN] Crearia carpeta: $TargetFolder" -ForegroundColor $Warning
    }
}

# Procesar cada archivo
foreach ($file in $sqlFiles) {
    $fileName = $file.Name
    $filePath = $file.FullName
    $relativePath = $file.FullName.Replace((Resolve-Path $RootPath).Path + "\", "")
    
    $destinationFile = Join-Path $destinationPath $fileName
    
    # Verificar si ya está en la carpeta destino
    $currentFolder = $file.DirectoryName.Replace((Resolve-Path $RootPath).Path + "\", "")
    
    if ($currentFolder -eq $TargetFolder) {
        Write-Host "[OK] $fileName ya esta en: $TargetFolder" -ForegroundColor $Success
        $skipped++
        continue
    }
    
    # Verificar si el archivo destino ya existe
    if (Test-Path $destinationFile) {
        # Si es el mismo archivo (mismo path completo), no hacer nada
        if ((Resolve-Path $filePath).Path -eq (Resolve-Path $destinationFile).Path) {
            Write-Host "[OK] $fileName ya esta en destino" -ForegroundColor $Success
            $skipped++
            continue
        }
        
        # Si hay conflicto de nombres, crear nombre único
        $baseName = [System.IO.Path]::GetFileNameWithoutExtension($fileName)
        $extension = [System.IO.Path]::GetExtension($fileName)
        $counter = 1
        $newFileName = "${baseName}_$counter$extension"
        $destinationFile = Join-Path $destinationPath $newFileName
        
        while (Test-Path $destinationFile) {
            $counter++
            $newFileName = "${baseName}_$counter$extension"
            $destinationFile = Join-Path $destinationPath $newFileName
        }
        
        Write-Host "[WARN] $fileName tiene conflicto, se renombrara a: $newFileName" -ForegroundColor $Warning
        $fileName = $newFileName
        $conflicts++
    }
    
    # Mover archivo
    if ($DryRun) {
        Write-Host "[DRY RUN] Moveria:" -ForegroundColor $Warning
        Write-Host "   De: $relativePath" -ForegroundColor $Info
        Write-Host "   A:  $TargetFolder\$fileName" -ForegroundColor $Info
        $moved++
    } else {
        try {
            Move-Item -Path $filePath -Destination $destinationFile -Force
            Write-Host "[OK] $fileName" -ForegroundColor $Success
            Write-Host "   Movido: $relativePath -> $TargetFolder\$fileName" -ForegroundColor $Success
            $moved++
        } catch {
            Write-Host "Error moviendo $fileName : $_" -ForegroundColor $Error
            $errors++
        }
    }
}

# Resumen
Write-Host "`n=======================================" -ForegroundColor $Info
Write-Host "RESUMEN" -ForegroundColor $Info
Write-Host "=======================================" -ForegroundColor $Info

if ($DryRun) {
    Write-Host "   Archivos a mover: $moved" -ForegroundColor $Warning
} else {
    Write-Host "   Archivos movidos: $moved" -ForegroundColor $Success
}

if ($conflicts -gt 0) {
    Write-Host "   Archivos renombrados (conflictos): $conflicts" -ForegroundColor $Warning
}

Write-Host "   Archivos omitidos: $skipped" -ForegroundColor $Info

if ($errors -gt 0) {
    Write-Host "   Errores: $errors" -ForegroundColor $Error
}

Write-Host "`nCarpeta destino: $TargetFolder`n" -ForegroundColor $Info
Write-Host "[OK] Proceso completado`n" -ForegroundColor $Success

