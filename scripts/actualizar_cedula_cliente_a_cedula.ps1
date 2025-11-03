# ============================================
# ACTUALIZAR COLUMNA: cedula_cliente → cedula
# ============================================
# Script PowerShell para Windows que actualiza todas las referencias
# de cedula_cliente a cedula en los archivos del proyecto
# ============================================

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "ACTUALIZAR COLUMNA: cedula_cliente → cedula" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Directorio base del proyecto
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

# Archivos a actualizar (solo archivos Python y TypeScript, excluyendo SQL por ahora)
$filesToUpdate = @(
    "$projectRoot\backend\app\models\pago.py",
    "$projectRoot\backend\app\schemas\pago.py",
    "$projectRoot\backend\app\api\v1\endpoints\pagos.py",
    "$projectRoot\backend\app\api\v1\endpoints\pagos_upload.py",
    "$projectRoot\frontend\src\services\pagoService.ts"
)

# Contador de cambios
$totalChanges = 0

Write-Host "Archivos a procesar:" -ForegroundColor Yellow
foreach ($file in $filesToUpdate) {
    if (Test-Path $file) {
        Write-Host "  ✅ $file" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️ $file (NO ENCONTRADO)" -ForegroundColor Red
    }
}
Write-Host ""

# Preguntar confirmación
$confirm = Read-Host "¿Continuar con la actualización? (S/N)"
if ($confirm -ne "S" -and $confirm -ne "s") {
    Write-Host "Operación cancelada." -ForegroundColor Yellow
    exit
}

Write-Host ""
Write-Host "Procesando archivos..." -ForegroundColor Cyan
Write-Host ""

# Procesar cada archivo
foreach ($filePath in $filesToUpdate) {
    if (-not (Test-Path $filePath)) {
        Write-Host "⚠️ Archivo no encontrado: $filePath" -ForegroundColor Red
        continue
    }

    Write-Host "Procesando: $filePath" -ForegroundColor Yellow
    
    # Leer contenido
    $content = Get-Content $filePath -Raw -Encoding UTF8
    $originalContent = $content
    
    # Reemplazos específicos para cada tipo de archivo
    if ($filePath -like "*.py") {
        # Python: Reemplazar referencias de la columna en modelos y queries
        # Pago.cedula_cliente → Pago.cedula
        $content = $content -replace 'Pago\.cedula_cliente', 'Pago.cedula'
        # pago.cedula_cliente → pago.cedula
        $content = $content -replace 'pago\.cedula_cliente', 'pago.cedula'
        # pago_data.cedula_cliente → pago_data.cedula
        $content = $content -replace 'pago_data\.cedula_cliente', 'pago_data.cedula'
        # self.cedula_cliente → self.cedula
        $content = $content -replace 'self\.cedula_cliente', 'self.cedula'
        # Definición de columna
        $content = $content -replace 'cedula_cliente\s*=\s*Column\(', 'cedula = Column('
        # En schemas
        $content = $content -replace 'cedula_cliente:\s*str\s*=', 'cedula: str ='
        # En parámetros de funciones
        $content = $content -replace 'cedula_cliente=', 'cedula='
    }
    
    if ($filePath -like "*.ts" -or $filePath -like "*.tsx") {
        # TypeScript: Reemplazar en interfaces y tipos
        $content = $content -replace 'cedula_cliente:\s*string', 'cedula: string'
    }
    
    # Verificar si hubo cambios
    if ($content -ne $originalContent) {
        # Crear backup
        $backupPath = "$filePath.backup"
        Copy-Item $filePath $backupPath -Force
        Write-Host "  💾 Backup creado: $backupPath" -ForegroundColor Gray
        
        # Guardar cambios
        $content | Set-Content $filePath -Encoding UTF8 -NoNewline
        $changes = ([regex]::Matches($originalContent, 'cedula_cliente')).Count
        $totalChanges += $changes
        Write-Host "  ✅ Actualizado ($changes cambios)" -ForegroundColor Green
    } else {
        Write-Host "  ⏭️ Sin cambios necesarios" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "RESUMEN" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Total de cambios realizados: $totalChanges" -ForegroundColor Yellow
Write-Host ""
Write-Host "⚠️ IMPORTANTE:" -ForegroundColor Yellow
Write-Host "1. Los archivos SQL NO se actualizaron automáticamente" -ForegroundColor White
Write-Host "2. Revisa manualmente los archivos modificados" -ForegroundColor White
Write-Host "3. Prueba la aplicación antes de hacer commit" -ForegroundColor White
Write-Host ""
Write-Host "✅ Archivos de backup creados con extensión .backup" -ForegroundColor Green
Write-Host ""




