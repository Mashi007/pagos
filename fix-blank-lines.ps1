# Script para eliminar espacios en blanco de líneas vacías
$files = @(
    "backend/app/api/v1/endpoints/analistas.py",
    "backend/app/api/v1/endpoints/auth.py",
    "backend/app/models/analista.py",
    "backend/app/models/concesionario.py",
    "backend/app/api/v1/endpoints/validadores.py",
    "backend/app/services/validators_service.py"
)

foreach ($file in $files) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        # Reemplazar líneas que solo contienen espacios en blanco con líneas vacías
        $content = $content -replace '(?m)^\s+$', ''
        Set-Content $file -Value $content -NoNewline
        Write-Host "✅ Corregido: $file"
    } else {
        Write-Host "❌ No encontrado: $file"
    }
}

Write-Host "`n✅ Todos los archivos corregidos"


