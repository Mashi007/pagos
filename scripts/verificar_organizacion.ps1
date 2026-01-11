# Script para verificar que todos los documentos .md y .sql estén organizados
# Uso: .\scripts\verificar_organizacion.ps1

param(
    [string]$RootPath = "."
)

# Colores para output
$Info = "Cyan"
$Success = "Green"
$Warning = "Yellow"
$ErrorColor = "Red"

Write-Host "`nVERIFICACION DE ORGANIZACION DE DOCUMENTOS`n" -ForegroundColor $Info

# Carpetas permitidas para archivos .md
$allowedMdFolders = @(
    "Documentos",
    "scripts",
    "scripts_obsoletos",
    ".github",
    "backend",
    "frontend",
    "node_modules",
    ".git",
    ".venv"
)

# Carpetas permitidas para archivos .sql
$allowedSqlFolders = @(
    "scripts\sql",
    "migrations",
    "node_modules",
    ".git"
)

# Archivos .md que pueden estar en la raíz
$allowedRootMd = @(
    "README.md"
)

$issues = @()
$mdIssues = 0
$sqlIssues = 0

Write-Host "Verificando archivos .md..." -ForegroundColor $Info

# Verificar archivos .md
$mdFiles = Get-ChildItem -Path $RootPath -Filter "*.md" -Recurse -File | Where-Object {
    $fullPath = $_.FullName
    $relativePath = $fullPath.Replace((Resolve-Path $RootPath).Path + "\", "")
    
    # Verificar si está en carpeta permitida
    $isAllowed = $false
    
    foreach ($allowed in $allowedMdFolders) {
        if ($relativePath -like "$allowed\*" -or $relativePath.StartsWith($allowed)) {
            $isAllowed = $true
            break
        }
    }
    
    # Verificar si es README.md en la raíz
    if (-not $isAllowed -and $_.Name -eq "README.md" -and $relativePath -eq "README.md") {
        $isAllowed = $true
    }
    
    return -not $isAllowed
}

if ($mdFiles.Count -gt 0) {
    Write-Host "   Encontrados $($mdFiles.Count) archivos .md fuera de carpetas organizadas:" -ForegroundColor $Warning
    foreach ($file in $mdFiles) {
        $relativePath = $file.FullName.Replace((Resolve-Path $RootPath).Path + "\", "")
        Write-Host "   - $relativePath" -ForegroundColor $Warning
        $issues += "MD: $relativePath"
        $mdIssues++
    }
} else {
    Write-Host "   [OK] Todos los archivos .md estan organizados" -ForegroundColor $Success
}

Write-Host "`nVerificando archivos .sql..." -ForegroundColor $Info

# Verificar archivos .sql
$sqlFiles = Get-ChildItem -Path $RootPath -Filter "*.sql" -Recurse -File | Where-Object {
    $fullPath = $_.FullName
    $relativePath = $fullPath.Replace((Resolve-Path $RootPath).Path + "\", "")
    
    # Verificar si está en carpeta permitida
    $isAllowed = $false
    
    foreach ($allowed in $allowedSqlFolders) {
        if ($relativePath -like "*\$allowed\*" -or $relativePath.StartsWith($allowed)) {
            $isAllowed = $true
            break
        }
    }
    
    return -not $isAllowed
}

if ($sqlFiles.Count -gt 0) {
    Write-Host "   Encontrados $($sqlFiles.Count) archivos .sql fuera de scripts\sql:" -ForegroundColor $Warning
    foreach ($file in $sqlFiles) {
        $relativePath = $file.FullName.Replace((Resolve-Path $RootPath).Path + "\", "")
        Write-Host "   - $relativePath" -ForegroundColor $Warning
        $issues += "SQL: $relativePath"
        $sqlIssues++
    }
} else {
    Write-Host "   [OK] Todos los archivos .sql estan organizados" -ForegroundColor $Success
}

# Resumen
Write-Host "`n=======================================" -ForegroundColor $Info
Write-Host "RESUMEN DE VERIFICACION" -ForegroundColor $Info
Write-Host "=======================================" -ForegroundColor $Info

if ($issues.Count -eq 0) {
    Write-Host "   [OK] Todos los documentos estan organizados correctamente" -ForegroundColor $Success
} else {
    Write-Host "   Archivos .md desorganizados: $mdIssues" -ForegroundColor $(if ($mdIssues -gt 0) { $Warning } else { $Success })
    Write-Host "   Archivos .sql desorganizados: $sqlIssues" -ForegroundColor $(if ($sqlIssues -gt 0) { $Warning } else { $Success })
    
    if ($mdIssues -gt 0) {
        Write-Host "`n   Para organizar archivos .md, ejecuta:" -ForegroundColor $Info
        Write-Host "   .\scripts\organizar_documentos.ps1" -ForegroundColor $Info
    }
    
    if ($sqlIssues -gt 0) {
        Write-Host "`n   Para organizar archivos .sql, ejecuta:" -ForegroundColor $Info
        Write-Host "   .\scripts\organizar_sql.ps1" -ForegroundColor $Info
    }
}

Write-Host "`n[OK] Verificacion completada`n" -ForegroundColor $Success

if ($issues.Count -gt 0) {
    exit 1
} else {
    exit 0
}

