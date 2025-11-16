# Script para eliminar archivos .md con mas de 2 meses de antiguedad
# Fecha: 2025-01-27

Write-Host "Eliminando archivos .md con mas de 2 meses de antiguedad..." -ForegroundColor Cyan

# Calcular fecha limite (2 meses atras)
$fechaLimite = (Get-Date).AddMonths(-2)
Write-Host "Fecha limite: $fechaLimite" -ForegroundColor Yellow
Write-Host ""

# Archivos a excluir (no eliminar)
$archivosExcluidos = @(
    "README.md",
    "LICENSE.md",
    "AUTHORS.md"
)

# Carpetas a excluir (no eliminar archivos de estas carpetas)
$carpetasExcluidas = @(
    "Documentos\README.md",
    "Documentos\Configuracion\README.md",
    "Documentos\Desarrollo\README.md",
    "Documentos\Testing\README.md",
    "Documentos\Analisis\README.md",
    "Documentos\Auditorias\README.md"
)

# Buscar todos los archivos .md
$archivosMD = Get-ChildItem -Path "." -Filter "*.md" -Recurse -File | Where-Object {
    $excluir = $false
    
    # Excluir archivos por nombre
    foreach ($excluido in $archivosExcluidos) {
        if ($_.Name -eq $excluido) {
            $excluir = $true
            break
        }
    }
    
    # Excluir READMEs en carpetas principales
    if (-not $excluir) {
        foreach ($carpeta in $carpetasExcluidas) {
            if ($_.FullName -like "*$carpeta*") {
                $excluir = $true
                break
            }
        }
    }
    
    -not $excluir
}

$eliminados = 0
$total = 0

foreach ($archivo in $archivosMD) {
    $total++
    $fechaModificacion = $archivo.LastWriteTime
    
    if ($fechaModificacion -lt $fechaLimite) {
        $diasAntiguedad = [math]::Round((Get-Date - $fechaModificacion).TotalDays)
        Write-Host "Eliminando: $($archivo.FullName)" -ForegroundColor Red
        Write-Host "  Ultima modificacion: $fechaModificacion ($diasAntiguedad dias atras)" -ForegroundColor Gray
        
        try {
            Remove-Item -Path $archivo.FullName -Force
            $eliminados++
        } catch {
            Write-Host "  ERROR: No se pudo eliminar - $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "Resumen:" -ForegroundColor Cyan
Write-Host "  Archivos revisados: $total" -ForegroundColor White
Write-Host "  Archivos eliminados: $eliminados" -ForegroundColor $(if ($eliminados -gt 0) { "Red" } else { "Green" })
Write-Host "  Archivos conservados: $($total - $eliminados)" -ForegroundColor Green

