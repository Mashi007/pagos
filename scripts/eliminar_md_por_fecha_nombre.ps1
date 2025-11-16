# Script para eliminar archivos .md con fecha en el nombre mayor a 2 meses
# Fecha: 2025-01-27

Write-Host "Eliminando archivos .md con fecha en el nombre mayor a 2 meses..." -ForegroundColor Cyan

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

$eliminados = 0
$total = 0

# Buscar todos los archivos .md
$archivosMD = Get-ChildItem -Path "Documentos" -Filter "*.md" -Recurse -File

foreach ($archivo in $archivosMD) {
    # Excluir archivos por nombre
    $excluir = $false
    foreach ($excluido in $archivosExcluidos) {
        if ($archivo.Name -eq $excluido) {
            $excluir = $true
            break
        }
    }
    
    if ($excluir) {
        continue
    }
    
    $total++
    
    # Buscar fecha en el nombre del archivo (formato YYYY-MM-DD o YYYY_MM_DD)
    if ($archivo.Name -match '(\d{4})[-_](\d{2})[-_](\d{2})') {
        try {
            $fechaEnNombre = [DateTime]::ParseExact("$($matches[1])-$($matches[2])-$($matches[3])", "yyyy-MM-dd", $null)
            
            if ($fechaEnNombre -lt $fechaLimite) {
                $diasAntiguedad = [math]::Round((Get-Date - $fechaEnNombre).TotalDays)
                Write-Host "Eliminando: $($archivo.Name)" -ForegroundColor Red
                Write-Host "  Fecha en nombre: $fechaEnNombre ($diasAntiguedad dias atras)" -ForegroundColor Gray
                Write-Host "  Ruta: $($archivo.FullName)" -ForegroundColor Gray
                
                try {
                    Remove-Item -Path $archivo.FullName -Force
                    $eliminados++
                } catch {
                    Write-Host "  ERROR: No se pudo eliminar - $($_.Exception.Message)" -ForegroundColor Yellow
                }
                Write-Host ""
            }
        } catch {
            # Si no se puede parsear la fecha, ignorar
        }
    }
}

Write-Host "Resumen:" -ForegroundColor Cyan
Write-Host "  Archivos revisados: $total" -ForegroundColor White
Write-Host "  Archivos eliminados: $eliminados" -ForegroundColor $(if ($eliminados -gt 0) { "Red" } else { "Green" })
Write-Host "  Archivos conservados: $($total - $eliminados)" -ForegroundColor Green

