# Script para analizar y eliminar archivos SQL no utilizados
# Uso: .\scripts\analizar_sql_no_usados.ps1 [-DryRun] [-Eliminar]

param(
    [switch]$DryRun = $false,           # Por defecto no hace dry run
    [switch]$Eliminar = $false,         # Si está presente, elimina los archivos
    [string]$SqlFolder = "scripts\sql" # Carpeta de archivos SQL
)

# Colores para output
$Info = "Cyan"
$Success = "Green"
$Warning = "Yellow"
$Error = "Red"

Write-Host "`nANALIZADOR DE ARCHIVOS SQL NO UTILIZADOS`n" -ForegroundColor $Info

# Archivos SQL que NUNCA deben eliminarse (archivos críticos)
$archivosProtegidos = @(
    "README.md"
)

# Obtener todos los archivos SQL
$sqlPath = Join-Path (Get-Location) $SqlFolder
if (-not (Test-Path $sqlPath)) {
    Write-Host "Error: La carpeta $SqlFolder no existe" -ForegroundColor $Error
    exit 1
}

$sqlFiles = Get-ChildItem -Path $sqlPath -Filter "*.sql" -File

Write-Host "Encontrados $($sqlFiles.Count) archivos SQL para analizar`n" -ForegroundColor $Info

# Función para buscar referencias a un archivo
function Search-References {
    param(
        [string]$FileName,
        [string]$SearchPath = "."
    )
    
    $searchName = $FileName -replace '\.sql$', ''
    $searchNameLower = $searchName.ToLower()
    
    $references = @()
    
    # Buscar en archivos Python
    $pyFiles = Get-ChildItem -Path $SearchPath -Filter "*.py" -Recurse -File | Where-Object {
        $_.FullName -notlike "*\node_modules\*" -and
        $_.FullName -notlike "*\.git\*" -and
        $_.FullName -notlike "*\.venv\*" -and
        $_.FullName -notlike "*\__pycache__\*"
    }
    
    foreach ($file in $pyFiles) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        if ($content -and ($content -match [regex]::Escape($searchName) -or $content -match [regex]::Escape($searchNameLower))) {
            $references += $file.FullName.Replace((Get-Location).Path + "\", "")
        }
    }
    
    # Buscar en archivos PowerShell
    $psFiles = Get-ChildItem -Path $SearchPath -Filter "*.ps1" -Recurse -File | Where-Object {
        $_.FullName -notlike "*\node_modules\*" -and
        $_.FullName -notlike "*\.git\*"
    }
    
    foreach ($file in $psFiles) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        if ($content -and ($content -match [regex]::Escape($searchName) -or $content -match [regex]::Escape($searchNameLower))) {
            $references += $file.FullName.Replace((Get-Location).Path + "\", "")
        }
    }
    
    # Buscar en archivos Markdown (documentación)
    $mdFiles = Get-ChildItem -Path $SearchPath -Filter "*.md" -Recurse -File | Where-Object {
        $_.FullName -notlike "*\node_modules\*" -and
        $_.FullName -notlike "*\.git\*"
    }
    
    foreach ($file in $mdFiles) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        if ($content -and ($content -match [regex]::Escape($searchName) -or $content -match [regex]::Escape($searchNameLower))) {
            $references += $file.FullName.Replace((Get-Location).Path + "\", "")
        }
    }
    
    # Buscar en archivos de configuración y otros
    $configFiles = Get-ChildItem -Path $SearchPath -Filter "*.{txt,ini,yaml,yml,json}" -Recurse -File -ErrorAction SilentlyContinue | Where-Object {
        $_.FullName -notlike "*\node_modules\*" -and
        $_.FullName -notlike "*\.git\*"
    }
    
    foreach ($file in $configFiles) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        if ($content -and ($content -match [regex]::Escape($searchName) -or $content -match [regex]::Escape($searchNameLower))) {
            $references += $file.FullName.Replace((Get-Location).Path + "\", "")
        }
    }
    
    return $references
}

# Analizar cada archivo SQL
$archivosNoUsados = @()
$archivosUsados = @()
$archivosConReferencias = @{}

foreach ($file in $sqlFiles) {
    $fileName = $file.Name
    $filePath = $file.FullName
    
    # Verificar si está protegido
    if ($archivosProtegidos -contains $fileName) {
        Write-Host "[PROTEGIDO] $fileName" -ForegroundColor $Warning
        continue
    }
    
    Write-Host "Analizando: $fileName..." -NoNewline -ForegroundColor $Info
    
    $references = Search-References -FileName $fileName
    
    if ($references.Count -eq 0) {
        Write-Host " NO USADO" -ForegroundColor $Error
        $archivosNoUsados += $file
    } else {
        Write-Host " USADO ($($references.Count) referencias)" -ForegroundColor $Success
        $archivosUsados += $file
        $archivosConReferencias[$fileName] = $references
    }
}

# Resumen
Write-Host "`n=======================================" -ForegroundColor $Info
Write-Host "RESUMEN DEL ANALISIS" -ForegroundColor $Info
Write-Host "=======================================" -ForegroundColor $Info

Write-Host "`nArchivos SQL USADOS: $($archivosUsados.Count)" -ForegroundColor $Success
Write-Host "Archivos SQL NO USADOS: $($archivosNoUsados.Count)" -ForegroundColor $(if ($archivosNoUsados.Count -gt 0) { $Error } else { $Success })

if ($archivosNoUsados.Count -gt 0) {
    Write-Host "`nARCHIVOS NO USADOS (pueden eliminarse):" -ForegroundColor $Warning
    foreach ($file in $archivosNoUsados) {
        Write-Host "  - $($file.Name)" -ForegroundColor $Warning
    }
}

# Mostrar algunos ejemplos de archivos usados con sus referencias
if ($archivosConReferencias.Count -gt 0 -and $archivosConReferencias.Count -le 5) {
    Write-Host "`nEJEMPLOS DE ARCHIVOS USADOS:" -ForegroundColor $Info
    foreach ($fileName in $archivosConReferencias.Keys | Select-Object -First 3) {
        Write-Host "  $fileName" -ForegroundColor $Success
        $archivosConReferencias[$fileName] | ForEach-Object {
            Write-Host "    -> $_" -ForegroundColor $Info
        }
    }
}

# Eliminar archivos si se solicita
if ($archivosNoUsados.Count -gt 0) {
    if ($Eliminar) {
        Write-Host "`nELIMINANDO $($archivosNoUsados.Count) archivos no usados..." -ForegroundColor $Warning
        
        $eliminados = 0
        $errores = 0
        
        foreach ($file in $archivosNoUsados) {
            try {
                Remove-Item -Path $file.FullName -Force
                Write-Host "  [OK] Eliminado: $($file.Name)" -ForegroundColor $Success
                $eliminados++
            } catch {
                Write-Host "  [ERROR] No se pudo eliminar $($file.Name): $_" -ForegroundColor $Error
                $errores++
            }
        }
        
        Write-Host "`nEliminados: $eliminados | Errores: $errores" -ForegroundColor $(if ($errores -eq 0) { $Success } else { $Warning })
    } elseif ($DryRun) {
        Write-Host "`n[DRY RUN] Para eliminar estos archivos, ejecuta:" -ForegroundColor $Warning
        Write-Host "  .\scripts\analizar_sql_no_usados.ps1 -Eliminar" -ForegroundColor $Info
    }
}

Write-Host "`n[OK] Analisis completado`n" -ForegroundColor $Success

