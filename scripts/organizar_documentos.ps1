# Script para organizar automáticamente archivos .md en carpetas correspondientes
# Uso: .\scripts\organizar_documentos.ps1

param(
    [switch]$DryRun = $false,  # Solo muestra lo que haría sin mover archivos
    [string]$RootPath = "."     # Ruta raíz del proyecto
)

# Colores para output
$Info = "Cyan"
$Success = "Green"
$Warning = "Yellow"
$Error = "Red"

Write-Host "`nORGANIZADOR DE DOCUMENTOS MARKDOWN`n" -ForegroundColor $Info

# Definir reglas de clasificación
$rules = @{
    # Auditorías
    "AUDITORIA" = "Documentos\Auditorias"
    
    # Análisis
    "ANALISIS" = "Documentos\Analisis"
    
    # Testing
    "TEST_" = "Documentos\Testing"
    "CI-CD" = "Documentos\Testing"
    "ACCESIBILIDAD" = "Documentos\Testing"
    
    # Configuración e Instalación
    "INSTALAR" = "Documentos\Configuracion"
    "COMANDOS_INSTALACION" = "Documentos\Configuracion"
    "PASOS_INSTALACION" = "Documentos\Configuracion"
    "DEPLOYMENT" = "Documentos\Configuracion"
    "VERIFICAR_INSTALACION" = "Documentos\Configuracion"
    
    # Desarrollo
    "PROCEDIMIENTO" = "Documentos\Desarrollo"
    "AVANCE" = "Documentos\Desarrollo"
    "ESTADO_FINAL" = "Documentos\Desarrollo"
    "ESTADO_CLIENTES" = "Documentos\Desarrollo"
    "RESUMEN_CAMBIOS" = "Documentos\Desarrollo"
    "RESUMEN_ERRORES" = "Documentos\Desarrollo"
    "PROPUESTA" = "Documentos\Desarrollo"
    
    # General (verificaciones, confirmaciones, soluciones, etc.)
    "VERIFICACION" = "Documentos\General"
    "CONFIRMACION" = "Documentos\General"
    "CHECKLIST" = "Documentos\General"
    "SOLUCION" = "Documentos\General"
    "CORRECCION" = "Documentos\General"
    "CONEXIONES" = "Documentos\General"
    "EXPORTACION" = "Documentos\General"
    "SISTEMA_NOTIFICACIONES" = "Documentos\General"
    "RESUMEN_NOTIFICACIONES" = "Documentos\General"
    "GUIA" = "Documentos\General"
    "ESCALA" = "Documentos\General"
    "DETALLE" = "Documentos\General"
    "EXPLICACION" = "Documentos\General"
    "ACLARACION" = "Documentos\General"
    "CAMBIO_IMPORTANTE" = "Documentos\General"
}

# Carpetas que deben mantenerse en su ubicación actual
$excludedFolders = @(
    "Documentos",
    "backend",
    "frontend",
    "scripts",
    "node_modules",
    ".git"
)

# Archivos que no deben moverse
$excludedFiles = @(
    "README.md"
)

# Función para determinar la carpeta destino
function Get-DestinationFolder {
    param([string]$FileName)
    
    $fileNameUpper = $FileName.ToUpper().Replace(".MD", "")
    
    # Verificar cada regla
    foreach ($pattern in $rules.Keys) {
        if ($fileNameUpper -like "*$pattern*") {
            return $rules[$pattern]
        }
    }
    
    # Si no coincide con ninguna regla, mantener en General
    return "Documentos\General"
}

# Función para verificar si el archivo debe ser procesado
function Should-ProcessFile {
    param(
        [string]$FilePath,
        [string]$FileName
    )
    
    # Verificar si está en carpeta excluida
    foreach ($excluded in $excludedFolders) {
        if ($FilePath -like "*\$excluded\*" -or $FilePath -like "$excluded\*") {
            return $false
        }
    }
    
    # Verificar si el archivo está excluido
    if ($excludedFiles -contains $FileName) {
        return $false
    }
    
    # Solo procesar archivos .md
    if (-not ($FileName -match "\.md$")) {
        return $false
    }
    
    return $true
}

# Contadores
$moved = 0
$skipped = 0
$errors = 0

# Buscar todos los archivos .md en la raíz y subdirectorios (excepto Documentos y otras carpetas excluidas)
Write-Host "Buscando archivos .md..." -ForegroundColor $Info

$mdFiles = Get-ChildItem -Path $RootPath -Filter "*.md" -Recurse -File | Where-Object {
    $fullPath = $_.FullName
    $shouldProcess = $true
    
    foreach ($excluded in $excludedFolders) {
        if ($fullPath -like "*\$excluded\*") {
            $shouldProcess = $false
            break
        }
    }
    
    $shouldProcess -and ($excludedFiles -notcontains $_.Name)
}

Write-Host "   Encontrados: $($mdFiles.Count) archivos`n" -ForegroundColor $Info

# Procesar cada archivo
foreach ($file in $mdFiles) {
    $fileName = $file.Name
    $filePath = $file.FullName
    $relativePath = $file.FullName.Replace((Resolve-Path $RootPath).Path + "\", "")
    
    # Determinar carpeta destino
    $destinationFolder = Get-DestinationFolder -FileName $fileName
    $destinationPath = Join-Path $RootPath $destinationFolder
    $destinationFile = Join-Path $destinationPath $fileName
    
    # Verificar si ya está en la carpeta correcta
    $currentFolder = $file.DirectoryName.Replace((Resolve-Path $RootPath).Path + "\", "")
    
    if ($currentFolder -eq $destinationFolder) {
        Write-Host "[OK] $fileName ya esta en: $destinationFolder" -ForegroundColor $Success
        $skipped++
        continue
    }
    
    # Verificar si el archivo destino ya existe
    if (Test-Path $destinationFile) {
        Write-Host "[WARN] $fileName ya existe en destino: $destinationFolder" -ForegroundColor $Warning
        $skipped++
        continue
    }
    
    # Crear carpeta destino si no existe
    if (-not (Test-Path $destinationPath)) {
        if (-not $DryRun) {
            New-Item -ItemType Directory -Path $destinationPath -Force | Out-Null
            Write-Host "[INFO] Carpeta creada: $destinationFolder" -ForegroundColor $Info
        }
    }
    
    # Mover archivo
    if ($DryRun) {
        Write-Host "[DRY RUN] Moveria:" -ForegroundColor $Warning
        Write-Host "   De: $relativePath" -ForegroundColor $Info
        Write-Host "   A:  $destinationFolder\$fileName" -ForegroundColor $Info
        $moved++
    } else {
        try {
            Move-Item -Path $filePath -Destination $destinationFile -Force
            Write-Host "[OK] $fileName" -ForegroundColor $Success
            Write-Host "   Movido: $relativePath -> $destinationFolder\" -ForegroundColor $Success
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

Write-Host "   Archivos omitidos: $skipped" -ForegroundColor $Info
if ($errors -gt 0) {
    Write-Host "   Errores: $errors" -ForegroundColor $Error
}

Write-Host "`n[OK] Proceso completado`n" -ForegroundColor $Success

