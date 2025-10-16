# ============================================================
# CONFIGURACION DE VARIABLES DE ENTORNO PARA SCRIPTS
# ============================================================
# 
# Ejecuta este script ANTES de usar los otros scripts para configurar
# las variables de entorno necesarias.
#
# USO:
#   . .\config_variables.ps1
#   . .\paso_0_obtener_token.ps1
#
# ============================================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "CONFIGURACION DE VARIABLES DE ENTORNO" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# URL de la API
$env:API_BASE_URL = "https://pagos-f2qf.onrender.com"
Write-Host "✓ API_BASE_URL configurado: $env:API_BASE_URL" -ForegroundColor Green

# Email del administrador
$env:ADMIN_EMAIL = "itmaster@rapicreditca.com"
Write-Host "✓ ADMIN_EMAIL configurado: $env:ADMIN_EMAIL" -ForegroundColor Green

# Contraseña del administrador
Write-Host "Ingresa la contraseña del administrador:" -ForegroundColor Yellow
$securePassword = Read-Host "Contraseña" -AsSecureString
$env:ADMIN_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword))
Write-Host "✓ ADMIN_PASSWORD configurado (oculto por seguridad)" -ForegroundColor Green

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "VARIABLES CONFIGURADAS CORRECTAMENTE" -ForegroundColor Cyan
Write-Host "Ahora puedes ejecutar los scripts de carga de datos" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
