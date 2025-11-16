# Script para organizar todos los archivos .md en carpetas estructuradas
# Fecha: 2025-01-27

Write-Host "Organizando archivos .md del proyecto..." -ForegroundColor Cyan

# 1. Mover archivos de General/Auditorias a Documentos/Auditorias
Write-Host "`n1. Moviendo auditorias de General/Auditorias a Documentos/Auditorias..." -ForegroundColor Yellow
$generalAuditorias = Get-ChildItem -Path "Documentos\General\Auditorias" -Filter "*.md" -File -ErrorAction SilentlyContinue
if ($generalAuditorias) {
    foreach ($file in $generalAuditorias) {
        $destino = "Documentos\Auditorias\$($file.Name)"
        if (-not (Test-Path $destino)) {
            Move-Item -Path $file.FullName -Destination $destino -Force
            Write-Host "  Movido: $($file.Name)" -ForegroundColor Green
        } else {
            Write-Host "  Ya existe: $($file.Name)" -ForegroundColor Yellow
        }
    }
}

# 2. Mover archivos de General/Analisis a Documentos/Analisis
Write-Host "`n2. Moviendo analisis de General/Analisis a Documentos/Analisis..." -ForegroundColor Yellow
$generalAnalisis = Get-ChildItem -Path "Documentos\General\Analisis" -Filter "*.md" -File -ErrorAction SilentlyContinue
if ($generalAnalisis) {
    foreach ($file in $generalAnalisis) {
        $destino = "Documentos\Analisis\$($file.Name)"
        if (-not (Test-Path $destino)) {
            Move-Item -Path $file.FullName -Destination $destino -Force
            Write-Host "  Movido: $($file.Name)" -ForegroundColor Green
        } else {
            Write-Host "  Ya existe: $($file.Name)" -ForegroundColor Yellow
        }
    }
}

# 3. Organizar archivos sueltos en General segun su prefijo
Write-Host "`n3. Organizando archivos sueltos en General..." -ForegroundColor Yellow

$generalFiles = Get-ChildItem -Path "Documentos\General" -Filter "*.md" -File | Where-Object { $_.DirectoryName -eq (Resolve-Path "Documentos\General").Path }

foreach ($file in $generalFiles) {
    $moved = $false
    $name = $file.Name
    
    # Guias
    if ($name -match "^GUIA_|^INSTRUCCIONES_|^COMO_|^PASOS_|^PROCEDIMIENTO_") {
        $dest = "Documentos\General\Guias\$name"
        if (-not (Test-Path $dest)) {
            New-Item -ItemType Directory -Path "Documentos\General\Guias" -Force | Out-Null
            Move-Item -Path $file.FullName -Destination $dest -Force
            Write-Host "  Guia: $name" -ForegroundColor Green
            $moved = $true
        }
    }
    
    # Verificaciones
    if (-not $moved -and ($name -match "^VERIFICACION_|^VERIFICAR_|^VALIDACION_|^CHECKLIST_")) {
        $dest = "Documentos\General\Verificaciones\$name"
        if (-not (Test-Path $dest)) {
            New-Item -ItemType Directory -Path "Documentos\General\Verificaciones" -Force | Out-Null
            Move-Item -Path $file.FullName -Destination $dest -Force
            Write-Host "  Verificacion: $name" -ForegroundColor Green
            $moved = $true
        }
    }
    
    # Confirmaciones
    if (-not $moved -and ($name -match "^CONFIRMACION_")) {
        $dest = "Documentos\General\Confirmaciones\$name"
        if (-not (Test-Path $dest)) {
            New-Item -ItemType Directory -Path "Documentos\General\Confirmaciones" -Force | Out-Null
            Move-Item -Path $file.FullName -Destination $dest -Force
            Write-Host "  Confirmacion: $name" -ForegroundColor Green
            $moved = $true
        }
    }
    
    # Correcciones
    if (-not $moved -and ($name -match "^CORRECCION_|^CORRECCIONES_|^FIX_")) {
        $dest = "Documentos\General\Correcciones\$name"
        if (-not (Test-Path $dest)) {
            New-Item -ItemType Directory -Path "Documentos\General\Correcciones" -Force | Out-Null
            Move-Item -Path $file.FullName -Destination $dest -Force
            Write-Host "  Correccion: $name" -ForegroundColor Green
            $moved = $true
        }
    }
    
    # Soluciones
    if (-not $moved -and ($name -match "^SOLUCION_|^SOLUCIONES_")) {
        $dest = "Documentos\General\Soluciones\$name"
        if (-not (Test-Path $dest)) {
            New-Item -ItemType Directory -Path "Documentos\General\Soluciones" -Force | Out-Null
            Move-Item -Path $file.FullName -Destination $dest -Force
            Write-Host "  Solucion: $name" -ForegroundColor Green
            $moved = $true
        }
    }
    
    # Reportes
    if (-not $moved -and ($name -match "^REPORTE_|^RESUMEN_")) {
        $dest = "Documentos\General\Reportes\$name"
        if (-not (Test-Path $dest)) {
            New-Item -ItemType Directory -Path "Documentos\General\Reportes" -Force | Out-Null
            Move-Item -Path $file.FullName -Destination $dest -Force
            Write-Host "  Reporte: $name" -ForegroundColor Green
            $moved = $true
        }
    }
    
    # Procesos
    if (-not $moved -and ($name -match "^PROCESO_|^LOGICA_|^REGLA_|^CRITERIOS_|^ESTRUCTURA_|^DETALLE_")) {
        $dest = "Documentos\General\Procesos\$name"
        if (-not (Test-Path $dest)) {
            New-Item -ItemType Directory -Path "Documentos\General\Procesos" -Force | Out-Null
            Move-Item -Path $file.FullName -Destination $dest -Force
            Write-Host "  Proceso: $name" -ForegroundColor Green
            $moved = $true
        }
    }
    
    # Mejoras
    if (-not $moved -and ($name -match "^MEJORAS_|^OPTIMIZACION|^INDICES_|^PERFORMANCE")) {
        $dest = "Documentos\General\Mejoras\$name"
        if (-not (Test-Path $dest)) {
            New-Item -ItemType Directory -Path "Documentos\General\Mejoras" -Force | Out-Null
            Move-Item -Path $file.FullName -Destination $dest -Force
            Write-Host "  Mejora: $name" -ForegroundColor Green
            $moved = $true
        }
    }
    
    # Documentacion/README
    if (-not $moved -and ($name -match "^README_|^LICENSE|^AUTHORS|^NORMAS_|^EXPLICACION_|^DIAGNOSTICO_|^ESTADO_|^ACLARACION_|^DIFERENCIA_|^DIFERENCIAS_")) {
        $dest = "Documentos\General\Documentacion\$name"
        if (-not (Test-Path $dest)) {
            New-Item -ItemType Directory -Path "Documentos\General\Documentacion" -Force | Out-Null
            Move-Item -Path $file.FullName -Destination $dest -Force
            Write-Host "  Documentacion: $name" -ForegroundColor Green
            $moved = $true
        }
    }
    
    # Configuracion
    if (-not $moved -and ($name -match "^CONFIGURACION_|^DEPLOY|^INSTALAR_|^RENDER_|^COMPLIANCE_|^ACTUALIZACION_")) {
        $dest = "Documentos\General\Configuracion\$name"
        if (-not (Test-Path $dest)) {
            New-Item -ItemType Directory -Path "Documentos\General\Configuracion" -Force | Out-Null
            Move-Item -Path $file.FullName -Destination $dest -Force
            Write-Host "  Configuracion: $name" -ForegroundColor Green
            $moved = $true
        }
    }
    
    # Comandos
    if (-not $moved -and ($name -match "^COMANDOS_|^EJECUTAR_")) {
        $dest = "Documentos\General\Comandos\$name"
        if (-not (Test-Path $dest)) {
            New-Item -ItemType Directory -Path "Documentos\General\Comandos" -Force | Out-Null
            Move-Item -Path $file.FullName -Destination $dest -Force
            Write-Host "  Comando: $name" -ForegroundColor Green
            $moved = $true
        }
    }
    
    if (-not $moved) {
        Write-Host "  Sin categoria: $name" -ForegroundColor Yellow
    }
}

# 4. Limpiar carpetas vacias
Write-Host "`n4. Limpiando carpetas vacias..." -ForegroundColor Yellow
if (Test-Path "Documentos\General\Auditorias") {
    $items = Get-ChildItem -Path "Documentos\General\Auditorias" -ErrorAction SilentlyContinue
    if ($null -eq $items -or $items.Count -eq 0) {
        Remove-Item -Path "Documentos\General\Auditorias" -Force -ErrorAction SilentlyContinue
        Write-Host "  Eliminada carpeta vacia: Auditorias" -ForegroundColor Green
    }
}

if (Test-Path "Documentos\General\Analisis") {
    $items = Get-ChildItem -Path "Documentos\General\Analisis" -ErrorAction SilentlyContinue
    if ($null -eq $items -or $items.Count -eq 0) {
        Remove-Item -Path "Documentos\General\Analisis" -Force -ErrorAction SilentlyContinue
        Write-Host "  Eliminada carpeta vacia: Analisis" -ForegroundColor Green
    }
}

Write-Host "`nOrganizacion completada!" -ForegroundColor Green
