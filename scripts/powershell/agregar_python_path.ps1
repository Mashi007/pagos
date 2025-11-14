# Script para agregar Python al PATH del usuario
# Ejecutar con: powershell -ExecutionPolicy Bypass -File .\scripts\powershell\agregar_python_path.ps1

Write-Host "🔍 Verificando instalación de Python..." -ForegroundColor Cyan

# Obtener la ruta de Python usando py launcher
try {
    $pythonPath = & py -c "import sys; print(sys.executable)" 2>$null
    if ($pythonPath) {
        $pythonDir = Split-Path $pythonPath -Parent
        $pythonScriptsDir = Join-Path $pythonDir "Scripts"
        
        Write-Host "✅ Python encontrado en: $pythonDir" -ForegroundColor Green
        Write-Host "📁 Scripts en: $pythonScriptsDir" -ForegroundColor Green
        
        # Obtener PATH actual del usuario
        $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
        
        # Verificar si ya está en PATH
        if ($currentPath -like "*$pythonDir*") {
            Write-Host "⚠️  Python ya está en PATH del usuario" -ForegroundColor Yellow
            Write-Host "   Ruta actual: $pythonDir" -ForegroundColor Gray
        } else {
            Write-Host "📝 Agregando Python al PATH del usuario..." -ForegroundColor Cyan
            
            # Agregar directorio de Python y Scripts al PATH
            $newPath = $currentPath
            if ($newPath -and -not $newPath.EndsWith(";")) {
                $newPath += ";"
            }
            $newPath += "$pythonDir;"
            
            # Agregar Scripts si existe
            if (Test-Path $pythonScriptsDir) {
                $newPath += "$pythonScriptsDir;"
            }
            
            # Actualizar PATH del usuario
            [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
            
            Write-Host "✅ Python agregado al PATH del usuario" -ForegroundColor Green
            Write-Host "   Directorio: $pythonDir" -ForegroundColor Gray
            if (Test-Path $pythonScriptsDir) {
                Write-Host "   Scripts: $pythonScriptsDir" -ForegroundColor Gray
            }
            Write-Host ""
            Write-Host "⚠️  IMPORTANTE: Cierra y vuelve a abrir la terminal para que los cambios surtan efecto" -ForegroundColor Yellow
            Write-Host "   O ejecuta: refreshenv" -ForegroundColor Yellow
        }
        
        # Verificar versión
        Write-Host ""
        Write-Host "📋 Información de Python:" -ForegroundColor Cyan
        & py --version
        Write-Host "   Ejecutable: $pythonPath" -ForegroundColor Gray
        
    } else {
        Write-Host "❌ No se pudo encontrar Python" -ForegroundColor Red
        Write-Host "   Asegúrate de que Python esté instalado y 'py' esté disponible" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "❌ Error al obtener información de Python: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Proceso completado" -ForegroundColor Green

