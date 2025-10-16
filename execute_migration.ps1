# Script PowerShell para ejecutar la migración de roles

$BaseUrl = "https://pagos-f2qf.onrender.com/api/v1"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "MIGRACION DE ROLES - Sistema de Prestamos" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Paso 1: Ejecutar migración
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host "PASO 1: EJECUTAR MIGRACION" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "Ejecutando migracion..." -ForegroundColor White

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/emergency/migrate-roles" -Method Post -ContentType "application/json" -TimeoutSec 60
    
    Write-Host ""
    Write-Host "MIGRACION EXITOSA!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Resultado:" -ForegroundColor Cyan
    $response | ConvertTo-Json -Depth 10 | Write-Host
    
    # Esperar un momento
    Write-Host ""
    Write-Host "Esperando 5 segundos para que la DB se estabilice..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    # Paso 2: Verificar resultado
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Yellow
    Write-Host "PASO 2: VERIFICAR RESULTADO" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Yellow
    Write-Host ""
    
    try {
        $checkResponse = Invoke-RestMethod -Uri "$BaseUrl/emergency/check-roles" -Method Get -TimeoutSec 30
        
        Write-Host "Estado final:" -ForegroundColor Cyan
        $checkResponse | ConvertTo-Json -Depth 10 | Write-Host
        
        if ($checkResponse.necesita_migracion -eq $false) {
            Write-Host ""
            Write-Host "SISTEMA CORRECTO!" -ForegroundColor Green
            
            # Paso 3: Probar login
            Write-Host ""
            Write-Host "============================================================" -ForegroundColor Yellow
            Write-Host "PASO 3: PROBAR LOGIN" -ForegroundColor Yellow
            Write-Host "============================================================" -ForegroundColor Yellow
            Write-Host ""
            
            try {
                $loginBody = @{
                    email = "itmaster@rapicreditca.com"
                    password = "admin123"
                } | ConvertTo-Json
                
                $loginResponse = Invoke-RestMethod -Uri "$BaseUrl/auth/login" -Method Post -Body $loginBody -ContentType "application/json" -TimeoutSec 30
                
                Write-Host "Login exitoso!" -ForegroundColor Green
                Write-Host ""
                
                # Resumen final
                Write-Host "============================================================" -ForegroundColor Green
                Write-Host "PROCESO COMPLETADO" -ForegroundColor Green
                Write-Host "============================================================" -ForegroundColor Green
                Write-Host ""
                Write-Host "Siguiente paso:" -ForegroundColor Cyan
                Write-Host "  1. Verificar que la app funciona en el navegador" -ForegroundColor White
                Write-Host "  2. Eliminar archivos temporales:" -ForegroundColor White
                Write-Host "     - backend/app/api/v1/endpoints/emergency_migrate_roles.py" -ForegroundColor Gray
                Write-Host "     - backend/scripts/run_migration_production.py" -ForegroundColor Gray
                Write-Host "     - execute_migration.ps1 (este archivo)" -ForegroundColor Gray
                Write-Host "  3. Actualizar main.py para remover el endpoint" -ForegroundColor White
                Write-Host "  4. Commit y push" -ForegroundColor White
                
            } catch {
                Write-Host "Login fallo: $($_.Exception.Message)" -ForegroundColor Yellow
                Write-Host "Esto puede ser normal, verifica manualmente" -ForegroundColor Yellow
            }
            
        } else {
            Write-Host ""
            Write-Host "Aun necesita migracion" -ForegroundColor Yellow
        }
        
    } catch {
        Write-Host "Error verificando resultado: $($_.Exception.Message)" -ForegroundColor Red
    }
    
} catch {
    Write-Host ""
    Write-Host "ERROR EJECUTANDO MIGRACION" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Posibles causas:" -ForegroundColor Yellow
    Write-Host "  1. La app aun esta iniciando (espera 1-2 minutos)" -ForegroundColor White
    Write-Host "  2. Error de conexion a DB" -ForegroundColor White
    Write-Host "  3. Permisos insuficientes en PostgreSQL" -ForegroundColor White
    Write-Host ""
    Write-Host "Intenta ejecutar este script nuevamente en 1 minuto" -ForegroundColor Yellow
}

